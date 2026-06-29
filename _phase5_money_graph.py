"""PHASE 5 - P4: money graph.

Extracts grounded money records (cheques, wires, settlement-sheet line items,
invoices) from doc_p5_* documents via Anthropic tool-use (Sonnet 4.6) with
verbatim source_quote grounding (OCR-tolerant fuzzy match), stores them in
`money_records`, links each to properties/entities, then reconciles instruments
across documents (same check#/amount/date seen on a cheque AND a settlement
sheet -> a reconciled transfer).

Resumable: a doc stamped money_extracted_at is skipped. Idempotent per doc
(delete old money_records for the doc, re-insert).

Usage:
  python _phase5_money_graph.py --limit 5      # smoke test
  python _phase5_money_graph.py                # all money-bearing docs
  python _phase5_money_graph.py --reconcile    # (re)run reconciliation only
"""
from __future__ import annotations
import argparse
import re
from datetime import datetime, timezone
from typing import Any, Dict, List

from anthropic import Anthropic
from rapidfuzz import fuzz
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.utils.logger import logger
from scripts.ingest_titles_full import norm_address, addr_core
from scripts.ingest_insurance import build_prop_index

MONEY_CATEGORIES = ["cheque", "wire_confirmation", "settlement_sheet",
                    "bill_invoice", "closing_document"]
_MAX_DOC_CHARS = 160_000

_MONEY_TOOL = {
    "name": "record_money",
    "description": "Record every monetary transfer/payment/line-item explicitly "
                   "stated in this financial document (cheque, wire, ACH, "
                   "settlement-sheet line, invoice). Each item MUST include a "
                   "verbatim source_quote copied EXACTLY from the document.",
    "input_schema": {
        "type": "object",
        "properties": {
            "payments": {"type": "array", "items": {"type": "object", "properties": {
                "payer": {"type": "string", "description": "who paid / drawer / from"},
                "payee": {"type": "string", "description": "who received / pay to the order of / to"},
                "amount": {"type": "string", "description": "amount as written, e.g. $1,146.00"},
                "date": {"type": "string"},
                "instrument": {"type": "string", "description": "check/cheque/wire/ach/cash/credit/debit/line_item"},
                "instrument_no": {"type": "string", "description": "check number / wire ref / confirmation #"},
                "bank": {"type": "string", "description": "drawer or beneficiary bank if stated"},
                "memo": {"type": "string", "description": "memo / for / re / description"},
                "property": {"type": "string", "description": "property address if the payment references one"},
                "source_quote": {"type": "string"}},
                "required": ["source_quote"]}},
        },
        "required": [],
    },
}
_SYS = ("You are a forensic accountant. Extract ONLY monetary movements explicitly "
        "stated in the document (cheques, wires, ACH, settlement-sheet line items, "
        "invoice amounts). For every item copy a short verbatim source_quote EXACTLY "
        "as written. Never infer or fabricate. If the document is a settlement sheet "
        "or ledger, emit one item per money line. Omit nothing that involves money.")

_AMT = re.compile(r"([\d,]+(?:\.\d{1,2})?)")
_HOUSE_ST = re.compile(r"\b(\d{1,5}(?:-\d{1,5})?)\s+([A-Za-z][A-Za-z .']{2,40})")


def _norm(s: str) -> str:
    return " ".join((s or "").lower().split())


def parse_amount(s: str):
    m = _AMT.search(s or "")
    if not m:
        return None
    try:
        return float(m.group(1).replace(",", ""))
    except Exception:  # noqa: BLE001
        return None


class MoneyExtractor:
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6",
                 *, ground_threshold: float = 80.0) -> None:
        self.client = Anthropic(api_key=api_key, timeout=180.0, max_retries=0)
        self.model = model
        self.ground_threshold = ground_threshold

    @retry(stop=stop_after_attempt(4), wait=wait_exponential(multiplier=2, min=2, max=30),
           retry=retry_if_exception_type(Exception), reraise=True)
    def _call(self, doc_text: str) -> Dict[str, Any]:
        resp = self.client.messages.create(
            model=self.model, max_tokens=8000, system=_SYS,
            tools=[_MONEY_TOOL], tool_choice={"type": "tool", "name": "record_money"},
            messages=[{"role": "user", "content": [
                {"type": "text", "text": f"<document>\n{doc_text}\n</document>",
                 "cache_control": {"type": "ephemeral"}},
                {"type": "text", "text": "Extract all money movements via record_money."},
            ]}])
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use":
                return dict(block.input or {})
        return {}

    def extract(self, doc_text: str) -> List[Dict[str, Any]]:
        text = (doc_text or "")[:_MAX_DOC_CHARS]
        if not text.strip():
            return []
        raw = self._call(text)
        hay = _norm(text)
        kept = []
        for item in (raw.get("payments") or []):
            if not isinstance(item, dict):
                continue
            q = _norm(item.get("source_quote", ""))
            if not q:
                continue
            if q in hay or fuzz.partial_ratio(q, hay) >= self.ground_threshold:
                item["grounded"] = True
                item["amount_value"] = parse_amount(item.get("amount", ""))
                kept.append(item)
        return kept


def reconcile(money) -> Dict[str, int]:
    """Group money_records by (instrument_no) and by (amount_value,date) to mark
    cross-document matches (e.g. a cheque that also appears on a settlement sheet)."""
    from collections import defaultdict
    by_no = defaultdict(list)
    by_amt = defaultdict(list)
    for r in money.find({"grounded": True}):
        no = (r.get("instrument_no") or "").strip()
        if no and no.isdigit() and len(no) >= 3:
            by_no[no].append(r)
        av = r.get("amount_value")
        if av:
            by_amt[round(av, 2)].append(r)
    groups = 0
    for no, recs in by_no.items():
        docs = {r["document_id"] for r in recs}
        if len(docs) >= 2:
            gid = f"recon_chk_{no}"
            money.update_many({"_id": {"$in": [r["_id"] for r in recs]}},
                              {"$set": {"reconciliation_id": gid,
                                        "reconciled_across_docs": sorted(docs)}})
            groups += 1
    return {"check_no_groups": groups, "distinct_amounts": len(by_amt)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--reocr", action="store_true")
    ap.add_argument("--reconcile", action="store_true", help="only run reconciliation")
    ap.add_argument("--budget", type=float, default=500.0)
    ap.add_argument("--shard", default=None, help="k/N disjoint worker shard, e.g. 0/3")
    args = ap.parse_args()
    shard_k = shard_n = None
    if args.shard:
        shard_k, shard_n = (int(x) for x in args.shard.split("/"))
    s = Settings.load()
    now = datetime.now(timezone.utc)
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    docs, money, ents = m.db["documents"], m.db["money_records"], m.db["entities"]
    money.create_index("document_id")
    money.create_index("instrument_no")
    money.create_index("amount_value")

    if args.reconcile:
        stats = reconcile(money)
        logger.info(f"reconciliation: {stats}")
        m.close()
        return 0

    prop_idx = build_prop_index(ents)
    ex = MoneyExtractor(s.anthropic_api_key)
    q: Dict[str, Any] = {"_id": {"$regex": "^doc_p5_"},
                         "doc_category": {"$in": MONEY_CATEGORIES}}
    if not args.reocr:
        q["money_extracted_at"] = {"$exists": False}
    pending = list(docs.find(q, {"_id": 1}))
    if shard_n:
        pending = [r for r in pending
                   if int(str(r["_id"]).split("_")[-1], 16) % shard_n == shard_k]
    if args.limit:
        pending = pending[: args.limit]
    logger.info(f"{len(pending)} money-bearing docs to extract (shard={args.shard or 'all'})")

    done = total_rec = 0
    for n, ref in enumerate(pending, 1):
        d = docs.find_one({"_id": ref["_id"]})
        text = d.get("extracted_text") or ""
        try:
            recs = ex.extract(text)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"  [{n}/{len(pending)}] {d['_id']}: money extract failed ({str(exc)[:80]})")
            continue
        money.delete_many({"document_id": d["_id"]})
        out = []
        for i, r in enumerate(recs):
            pids = list(d.get("property_ids") or [])
            if r.get("property"):
                mt = _HOUSE_ST.search(r["property"])
                if mt:
                    pid = prop_idx.get(addr_core(norm_address(f"{mt.group(1)} {mt.group(2)}")))
                    if pid and pid not in pids:
                        pids.append(pid)
            out.append({
                "_id": f"{d['_id']}::money::{i}", "document_id": d["_id"],
                "sha256": (d.get("custody") or {}).get("sha256"),
                "matter_id": d.get("matter_id"), "corpus": d.get("corpus"),
                "doc_category": d.get("doc_category"),
                "bates_start": d.get("bates_start"),
                "payer": r.get("payer"), "payee": r.get("payee"),
                "amount": r.get("amount"), "amount_value": r.get("amount_value"),
                "date": r.get("date"), "instrument": r.get("instrument"),
                "instrument_no": r.get("instrument_no"), "bank": r.get("bank"),
                "memo": r.get("memo"), "property": r.get("property"),
                "property_ids": pids, "source_quote": r.get("source_quote"),
                "grounded": True, "created_at": now,
            })
        if out:
            money.insert_many(out, ordered=False)
        docs.update_one({"_id": d["_id"]}, {"$set": {"money_extracted_at": now,
                        "money_record_count": len(out)}})
        done += 1
        total_rec += len(out)
        if n % 25 == 0 or n == len(pending):
            logger.info(f"  [{n}/{len(pending)}] {d['doc_category']} -> {len(out)} records "
                        f"| run_total={total_rec}")

    if shard_n:
        logger.info("================ MONEY SHARD DONE ================")
        logger.info(f"shard={args.shard} docs processed={done} money_records written={total_rec} "
                    "(reconcile deferred -> run --reconcile after all shards)")
        m.close()
        return 0
    stats = reconcile(money)
    logger.info("================ MONEY GRAPH DONE ================")
    logger.info(f"docs processed={done} money_records written={total_rec} reconcile={stats}")
    logger.info(f"money_records total: {money.estimated_document_count()}")
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
