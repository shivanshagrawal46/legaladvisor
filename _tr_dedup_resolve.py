"""
Resolve content-duplicate title reports surfaced after reparse.

A title report's logical identity (user's criteria):
  ProTitle: (addr_core, order_number, completed_date, index_date)
  Prowess : (addr_core, order_type, search_date, old_effective_date, new_effective_date)

Byte-different files can carry the SAME logical report (re-saved/re-scanned PDF).
SHA dedup keeps them as separate files; identity dedup must collapse them to ONE
canonical document, recording every physical file occurrence (custody) and NEVER
storing the content twice (no duplicate chunks).

Canonical pick rule: keep the document that is already integrated (chunked /
linked / in version chains) when its OCR is frontier; otherwise keep the
frontier-OCR'd copy. The retired copy's physical file(s) are recorded on the
survivor's custody.source_files, then the retired doc is deleted (its chunks too).

Usage:
  python _tr_dedup_resolve.py            # dry-run report
  python _tr_dedup_resolve.py --live     # apply
"""
from __future__ import annotations

import argparse
from collections import defaultdict

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.utils.logger import logger
from scripts.ingest_titles_full import addr_core

FRONTIER = ("claude_vision", "openai_vision")


def _acore(d):
    return addr_core(d.get("address_norm") or "")


def identity(d):
    v = d.get("vendor")
    ac = _acore(d)
    cd = str(d.get("completed_date")); ix = str(d.get("index_date"))
    if v == "protitle":
        return ("PT", ac, d.get("order_number"), cd, ix)
    return ("PW", ac, d.get("order_type"), str(d.get("search_date")),
            str(d.get("old_effective_date")), str(d.get("new_effective_date")))


def _methods(d):
    """Normalize extraction_method (str or dict) -> {method: pages}."""
    em = d.get("extraction_method")
    if isinstance(em, dict):
        return em
    if isinstance(em, str) and em:
        return {em: int(d.get("page_count") or d.get("num_pages") or 1)}
    return {}


def is_frontier(d):
    em = _methods(d)
    return bool(em) and all(k in FRONTIER for k in em)


def npages(d):
    em = _methods(d)
    return sum(em.values()) if em else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    m.ping()
    docs, chunks = m.db["documents"], m.db["email_chunks_v2"]

    proj = {"vendor": 1, "address_norm": 1, "order_number": 1, "completed_date": 1,
            "index_date": 1, "order_type": 1, "search_date": 1, "old_effective_date": 1,
            "new_effective_date": 1, "extraction_method": 1, "page_count": 1,
            "num_pages": 1, "chunked_at": 1, "property_ids": 1, "custody": 1}
    groups = defaultdict(list)
    for d in docs.find({"source_type": "title_report"}, proj):
        groups[identity(d)].append(d)

    dup_groups = {k: v for k, v in groups.items() if len(v) > 1}
    logger.info(f"title docs total={sum(len(v) for v in groups.values())} | "
                f"identity groups={len(groups)} | DUPLICATE groups={len(dup_groups)}")

    retire = []           # (survivor_id, retired_doc)
    weak = []             # groups we won't auto-resolve (identity too thin)
    for k, v in dup_groups.items():
        # guard: never collapse on an empty/thin identity (e.g. no order#, no dates)
        ac, key_tail = k[1], [x for x in k[2:] if x not in ("", "None", None)]
        if not ac or not key_tail:
            weak.append((k, v))
            continue
        # canonical preference: integrated(chunked) & frontier > frontier > chunked > other
        def score(d):
            return (is_frontier(d) and bool(d.get("chunked_at")),
                    is_frontier(d), bool(d.get("chunked_at")),
                    bool(d.get("property_ids")), npages(d))
        v_sorted = sorted(v, key=score, reverse=True)
        survivor = v_sorted[0]
        for r in v_sorted[1:]:
            retire.append((survivor["_id"], r, is_frontier(survivor), is_frontier(r)))

    logger.info(f"resolvable duplicate docs to retire: {len(retire)} | "
                f"weak/thin-identity groups skipped: {len(weak)}")
    # show OCR posture of survivors vs retired
    surv_nonfront = sum(1 for s_id, r, sf, rf in retire if not sf)
    upgrade_needed = [(s_id, r) for s_id, r, sf, rf in retire if not sf and rf]
    logger.info(f"  survivors NOT frontier: {surv_nonfront} | of those, frontier copy available to upgrade: {len(upgrade_needed)}")
    for s_id, r, sf, rf in retire[:12]:
        logger.info(f"  RETIRE {r['_id']} -> survivor {s_id} | surv_frontier={sf} retired_frontier={rf} "
                    f"retired_chunked={bool(r.get('chunked_at'))}")
    for k, v in weak[:8]:
        logger.warning(f"  WEAK identity {k}: {[d['_id'] for d in v]}")

    if not args.live:
        logger.info("DRY-RUN — no changes. Re-run with --live to apply.")
        m.close()
        return 0

    applied = chunks_deleted = upgraded = prov = 0
    for s_id, r, sf, rf in retire:
        surv = docs.find_one({"_id": s_id})
        # 1) upgrade survivor text to frontier copy if survivor is not frontier but retired is
        if (not sf) and rf:
            docs.update_one({"_id": s_id}, {"$set": {
                "extracted_text": r.get("extracted_text"),
                "extraction_method": r.get("extraction_method"),
                "ocr_upgraded_from": r["_id"], "ocr_upgraded_at": __import__("datetime").datetime.utcnow(),
                "chunked_at": None,  # force re-chunk of the upgraded text
            }})
            docs.update_one({"_id": s_id}, {"$unset": {"chunked_at": ""}})
            chunks.delete_many({"document_id": s_id})
            upgraded += 1
        # 2) record every physical file occurrence of the retired doc on survivor
        rc = (r.get("custody") or {})
        files = rc.get("source_files") or ([rc] if rc.get("sha256") else [])
        if files:
            docs.update_one({"_id": s_id}, {"$addToSet": {"custody.source_files": {"$each": files}}})
            prov += 1
        docs.update_one({"_id": s_id}, {"$addToSet": {
            "duplicate_of_files": {"doc_id": r["_id"],
                                   "sha256": rc.get("sha256"),
                                   "path": rc.get("source_path") or rc.get("path")}}})
        # 3) delete the duplicate doc + any chunks + its dangling relationship edges
        n = chunks.delete_many({"document_id": r["_id"]}).deleted_count
        chunks_deleted += n
        m.db["relationships"].delete_many({"$or": [{"src": r["_id"]}, {"dst": r["_id"]},
                                                   {"source_doc_id": r["_id"]}]})
        docs.delete_one({"_id": r["_id"]})
        applied += 1

    logger.info(f"APPLIED: retired={applied} dup-chunks-deleted={chunks_deleted} "
                f"survivors-upgraded-to-frontier={upgraded} provenance-merged={prov}")
    logger.info(f"title docs now: {docs.count_documents({'source_type':'title_report'})}")
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
