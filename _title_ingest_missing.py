r"""Ingest E:\missing title reports with ZERO missing versions.

Why a dedicated harness (not ingest_titles_full --folder):
  The standard pipeline pre-dedups on the *pre-OCR* born-digital text layer.
  Prowess two-column text layers are unreliable, so it falls back to a coarse
  (address-core, is_update) key that COLLAPSES distinct update searches
  (e.g. "Update Search" vs "Update Search 2026") onto one existing doc and
  skips OCR -> a genuinely newer version would be silently dropped.

This harness instead:
  * OCRs EVERY byte-new file (frontier vision only; Claude -> GPT-5) so the
    TRUE identity (order#/effective/search dates) comes from real content.
  * Dedups on that post-OCR identity via the deterministic doc_id. Same
    identity -> same doc_id -> merge provenance (no duplicate). Different
    identity (a real new/older/middle version) -> new doc (kept).
  * Byte-identical files (same sha256 already in DB) skip OCR but record the
    new E: path as provenance.
  * Links each report to its property entity by parcel OR folder/OCR address.
  * Enforces frontier-only OCR: any non-vision page is flagged.

Resumable + idempotent. Usage:
  python _title_ingest_missing.py --dry-run
  python _title_ingest_missing.py --live
"""
from __future__ import annotations
import argparse
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.utils.hashing import sha256_bytes, sha256_strings
from src.utils.logger import logger
from scripts.ingest_titles_full import (full_ocr, strip_watermarks, norm_address,
                                        addr_core, page_type)
from scripts.ingest_title_reports import (
    detect_vendor, parse_report, parse_prowess, normalize_parcel, _parse_date,
    resolve_owner_entity, resolve_property_entity, derive_fraud_flags,
    DOCS_COLLECTION, ENTITIES_COLLECTION,
)
from src.rag.evidence_schema import DEFAULT_MATTER_ID
from scripts.ingest_insurance import build_prop_index

ROOT = Path(r"E:\missing title reports")
FRONTIER = {"claude_vision", "openai_vision"}


def _acore(addr: str) -> str:
    return addr_core(norm_address(addr or ""))


def build_title_index(docs):
    """In-memory identity index of EVERY existing title_report doc, keyed by the
    user's dedup criteria with addr_core address normalization (60 central
    parkway == 60 central pkwy)."""
    idx = []
    for d in docs.find({"source_type": "title_report"},
                       {"vendor": 1, "order_number": 1, "completed_date": 1, "index_date": 1,
                        "order_type": 1, "search_date": 1, "old_effective_date": 1,
                        "new_effective_date": 1, "address_norm": 1, "property_ids": 1}):
        idx.append({
            "_id": d["_id"], "vendor": d.get("vendor"),
            "order_number": d.get("order_number"), "completed_date": d.get("completed_date"),
            "index_date": d.get("index_date"), "order_type": d.get("order_type"),
            "search_date": d.get("search_date"), "old_effective_date": d.get("old_effective_date"),
            "new_effective_date": d.get("new_effective_date"),
            "acore": addr_core(d.get("address_norm") or ""),
            "property_ids": d.get("property_ids") or [],
        })
    return idx


def find_existing_title(idx, *, vendor, rep, acore):
    """Return existing doc_id if this freshly-OCR'd report is a DUPLICATE of one
    already stored, per the exact criteria:
      ProTitle: order_number + completed_date + index_date (+ addr_core)
                (fallback to addr_core + completed_date + index_date if no order#)
      Prowess : order_type + search_date + old_effective_date + new_effective_date
                (+ addr_core)
    """
    if vendor == "protitle":
        on = rep.get("order_number")
        cd = _parse_date(rep.get("completed_date"))
        ix = _parse_date(rep.get("index_date"))
        for e in idx:
            if e["vendor"] != "protitle":
                continue
            if e["completed_date"] != cd or e["index_date"] != ix:
                continue
            if on and e["order_number"] == on:
                return e["_id"]
            if not on and acore and e["acore"] == acore:
                return e["_id"]
            if on and e["order_number"] == on and acore and e["acore"] == acore:
                return e["_id"]
    else:
        ot = rep.get("order_type") or "Full Search"
        sd = _parse_date(rep.get("search_date"))
        oe = _parse_date(rep.get("old_effective_date"))
        ne = _parse_date(rep.get("new_effective_date"))
        for e in idx:
            if e["vendor"] != "prowess":
                continue
            if (e["order_type"] or "Full Search") != ot:
                continue
            if e["search_date"] == sd and e["old_effective_date"] == oe \
                    and e["new_effective_date"] == ne and acore and e["acore"] == acore:
                return e["_id"]
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--live", dest="dry_run", action="store_false")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--budget", type=float, default=200.0)
    args = ap.parse_args()

    s = Settings.load()
    now = datetime.now(timezone.utc)
    inv = json.load(open("_tr_inventory.json", encoding="utf-8"))

    # flatten inventory -> per-file rows with folder + sha + byte-new flag
    rows = []
    for fld in inv:
        for f in fld.get("files", []):
            if "file" not in f:
                continue
            rows.append({"rel": f["file"], "folder": fld["folder"],
                         "folder_prop": fld.get("property_id"),
                         "new": bool(f.get("new"))})
    byte_new = [r for r in rows if r["new"]]
    byte_dup = [r for r in rows if not r["new"]]
    logger.info(f"missing-title files: total={len(rows)} byte-new={len(byte_new)} "
                f"byte-dup={len(byte_dup)}")

    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    m.ping()
    docs = m.db[DOCS_COLLECTION]
    ents = m.db[ENTITIES_COLLECTION]
    prop_idx = build_prop_index(ents)

    if args.dry_run:
        logger.info("DRY RUN — would OCR %d byte-new files; %d byte-dups get provenance only."
                    % (len(byte_new), len(byte_dup)))
        m.close()
        return 0

    from src.extractor.claude_ocr import init_spend_guard, get_spend_guard
    init_spend_guard(args.budget)

    # field-based identity index of every existing title report (addr_core-normalized)
    title_idx = build_title_index(docs)
    logger.info(f"existing title identity index: {len(title_idx)} reports")

    # ---- 1. byte-dup files: record provenance on the existing doc ----
    prov = 0
    for r in byte_dup:
        ap_ = ROOT / r["rel"]
        try:
            sha = sha256_bytes(ap_.read_bytes())
        except Exception:  # noqa: BLE001
            continue
        ex = docs.find_one({"custody.sha256": sha}, {"_id": 1})
        if ex:
            docs.update_one({"_id": ex["_id"]},
                            {"$addToSet": {"custody.source_files": "MISSING_TR/" + r["rel"]}})
            prov += 1
    logger.info(f"byte-dup provenance recorded on {prov} existing docs")

    # ---- 2. byte-new files: frontier OCR + identity dedup + linkage ----
    todo = byte_new[: args.limit] if args.limit else byte_new
    written = merged = resumed = flagged = 0
    nonfrontier_pages = 0
    affected_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    flag_docs = []

    for n, r in enumerate(todo, 1):
        p = ROOT / r["rel"]
        srcfile = "MISSING_TR/" + r["rel"]
        if docs.find_one({"custody.source_files": srcfile}, {"_id": 1}):
            resumed += 1
            continue
        try:
            res = full_ocr(p, s, force=True)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"  [{n}/{len(todo)}] OCR FAILED {r['rel']}: {str(exc)[:90]}")
            flag_docs.append({"file": r["rel"], "error": str(exc)[:120]})
            continue
        raw_pages = res.pages or []
        page_texts = [strip_watermarks(pg.text or "") for pg in raw_pages]
        methods = [pg.method for pg in raw_pages]
        full_text = "\n\n".join(t for t in page_texts if t).strip()
        nf = [mth for mth in methods if mth not in FRONTIER]
        if nf:
            nonfrontier_pages += len(nf)
            flag_docs.append({"file": r["rel"], "nonfrontier_methods": nf})

        vendor = detect_vendor(full_text) or "protitle"
        rep = parse_prowess(full_text) if vendor == "prowess" else parse_report(full_text)
        addr = rep.get("property_address")
        # address-core key (60 central parkway == 60 central pkwy); fall back to folder name
        acore = _acore(addr) or _acore(r["folder"])
        addr_key = norm_address(addr) or acore
        parcel = rep.get("parcel_id")
        is_update = (rep.get("is_update") if vendor == "protitle"
                     else rep.get("order_type") == "Update Search")
        eff = (_parse_date(rep.get("completed_date")) if vendor == "protitle"
               else (_parse_date(rep.get("new_effective_date")) or _parse_date(rep.get("search_date"))))

        # ---- FIELD-BASED dedup vs existing reports (the user's exact criteria) ----
        existing_id = find_existing_title(title_idx, vendor=vendor, rep=rep, acore=acore)

        owner_res = resolve_owner_entity(ents, rep.get("owner_name") or "", now)
        prop_id = resolve_property_entity(ents, rep, owner_res["is_david"], now)
        # linkage: parcel entity, then OCR/folder address via the property index
        pids = [prop_id] if prop_id else []
        for cand in (acore, _acore(r["folder"])):
            if cand and prop_idx.get(cand) and prop_idx[cand] not in pids:
                pids.append(prop_idx[cand])
        if not pids and r.get("folder_prop"):
            pids.append(r["folder_prop"])

        if existing_id:
            # DUPLICATE of an already-stored report: record provenance + backfill
            # property links if the stored doc was missing them. No new doc.
            upd = {"$addToSet": {"custody.source_files": srcfile}}
            if pids:
                upd.setdefault("$addToSet", {})
                upd["$addToSet"]["property_ids"] = {"$each": pids}
            docs.update_one({"_id": existing_id}, upd)
            merged += 1
            logger.info(f"  [{n}/{len(todo)}] DUP of {existing_id} (merge provenance)  {r['rel'][:48]}")
            continue

        # NEW report -> deterministic id from the addr-core-normalized identity
        if vendor == "protitle":
            doc_id = "doc_tr_" + (rep.get("order_number") or "na") + "_" + sha256_strings(
                [acore, rep.get("completed_date") or "", rep.get("index_date") or ""])[:8]
        else:
            doc_id = "doc_pw_" + sha256_strings([acore, rep.get("order_type") or "",
                     rep.get("search_date") or "", rep.get("old_effective_date") or "",
                     rep.get("new_effective_date") or ""])[:16]

        vgroup = ("parcel:" + normalize_parcel(parcel)) if parcel else ("addr:" + addr_key)
        page_meta = [{"page": i + 1, "type": page_type(page_texts[i]),
                      "method": methods[i] if i < len(methods) else "?"}
                     for i in range(len(page_texts))]
        method_counts: Dict[str, int] = defaultdict(int)
        for mth in methods:
            method_counts[mth] += 1

        existed = docs.find_one({"_id": doc_id}, {"_id": 1})
        doc = {
            "_id": doc_id, "source_type": "title_report", "vendor": vendor,
            "issuing_authority": "ProTitle USA" if vendor == "protitle" else "Prowess Title Abstracts",
            "matter_id": DEFAULT_MATTER_ID,
            "instrument_subtype": "update_search" if is_update else "full_search",
            "corpus": "property_records", "privilege_status": "public_record",
            "evidentiary_class": "third_party_business_record", "authority_score": 1.15,
            "order_number": rep.get("order_number"),
            "order_type": rep.get("order_type") or ("Update Search" if is_update else "Full Search"),
            "completed_date": _parse_date(rep.get("completed_date")),
            "index_date": _parse_date(rep.get("index_date")),
            "search_date": _parse_date(rep.get("search_date")),
            "old_effective_date": _parse_date(rep.get("old_effective_date")),
            "new_effective_date": _parse_date(rep.get("new_effective_date")),
            "effective_date": eff, "is_update": is_update,
            "property_address": addr, "address_norm": addr_key, "parcel_id": parcel,
            "county": rep.get("county"), "property_ids": pids,
            "owner_name_raw": rep.get("owner_name"), "owner_entity_id": owner_res["entity_id"],
            "owner_is_david": owner_res["is_david"],
            "version_group": vgroup, "fraud_flags": derive_fraud_flags(rep, full_text),
            "title_defect_category": rep.get("title_defect_category"),
            "page_count": len(page_texts), "pages": page_meta,
            "extraction_method": dict(method_counts), "ocr_confidence": res.avg_ocr_confidence,
            "frontier_only_ocr": (not nf),
            "extracted_text": full_text,
            # custody set via dotted paths so $addToSet on source_files does not conflict
            "custody.sha256": sha256_bytes(p.read_bytes()), "custody.origin": "missing_title_reports",
            "custody.ingested_at": now, "custody.folder_address": r["folder"],
            "quality": {"has_parcel": bool(parcel), "has_owner": bool(rep.get("owner_name")),
                        "needs_review": (not rep.get("owner_name")) or bool(nf) or (not pids)},
            "updated_at": now,
        }
        doc.pop("_id")
        docs.update_one({"_id": doc_id}, {"$set": doc,
                        "$addToSet": {"custody.source_files": srcfile},
                        "$setOnInsert": {"created_at": now}}, upsert=True)
        if not existed:
            written += 1
            # register in the live identity index so a later batch file that is
            # the SAME report collapses onto this doc (no duplicate).
            title_idx.append({
                "_id": doc_id, "vendor": vendor,
                "order_number": rep.get("order_number"),
                "completed_date": _parse_date(rep.get("completed_date")),
                "index_date": _parse_date(rep.get("index_date")),
                "order_type": rep.get("order_type") or ("Update Search" if is_update else "Full Search"),
                "search_date": _parse_date(rep.get("search_date")),
                "old_effective_date": _parse_date(rep.get("old_effective_date")),
                "new_effective_date": _parse_date(rep.get("new_effective_date")),
                "acore": acore, "property_ids": pids,
            })
        else:
            merged += 1
        affected_groups[vgroup].append({"doc_id": doc_id, "eff": eff, "is_update": is_update})
        g2 = get_spend_guard()
        spent = f"${g2.spent:.2f}" if g2 else "n/a"
        logger.info(f"  [{n}/{len(todo)}] {vendor} {'UPD' if is_update else 'ORIG'} "
                    f"pages={len(page_texts)} pids={len(pids)} {'NEW' if not existed else 'RESUME'} "
                    f"nf={len(nf)} spend={spent}  {r['rel'][:48]}")

    logger.info("================ MISSING-TITLE INGEST DONE ================")
    logger.info(f"new docs={written}  merged-into-existing={merged}  resumed={resumed}")
    logger.info(f"non-frontier pages flagged={nonfrontier_pages}  flagged docs={len(flag_docs)}")
    g2 = get_spend_guard()
    if g2:
        logger.info(f"vision spend: ${g2.spent:.2f} / ${g2.budget:.2f}")
    Path("_title_ingest_flags.json").write_text(json.dumps(flag_docs, indent=2), encoding="utf-8")
    logger.info(f"title_report docs now: {docs.count_documents({'source_type':'title_report'})}")
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
