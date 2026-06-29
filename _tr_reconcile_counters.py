"""Title OCR is already 100% frontier per the authoritative pages[] array (a prior
repair_ocr_pages run spliced GPT-5 text into extracted_text and set pages[].method
= openai_vision). Only the doc-level extraction_method COUNTER is stale.

This script:
  1) reports repair-quality stats (ocr_repaired_pages, unlocated splices, lingering
     RapidOCR-era 'CORRECTED OCR' append blocks),
  2) reconciles each title doc's extraction_method counter to match pages[] (free),
  3) re-verifies 0 non-frontier pages remain.

Usage:
  python _tr_reconcile_counters.py            # dry-run
  python _tr_reconcile_counters.py --live
"""
import argparse
from collections import Counter
from datetime import datetime, timezone

import config.settings  # noqa
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.utils.logger import logger

FRONTIER = {"claude_vision", "openai_vision"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()
    s = Settings.load()
    now = datetime.now(timezone.utc)
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    m.ping()
    docs = m.db["documents"]
    proj = {"pages": 1, "extraction_method": 1, "quality": 1, "ocr_repaired_at": 1}

    total = repaired_docs = reconciled = nonfrontier = unlocated = 0
    repaired_pages = 0
    new_counter = Counter()
    lingering = []  # docs that still contain an appended CORRECTED-OCR block

    for d in docs.find({"source_type": "title_report"}, proj):
        total += 1
        pages = d.get("pages") or []
        per = Counter((p.get("method") or "unknown") for p in pages if isinstance(p, dict))
        new_counter.update(per)
        if any(k not in FRONTIER for k in per):
            nonfrontier += 1

        q = d.get("quality") or {}
        if d.get("ocr_repaired_at"):
            repaired_docs += 1
            repaired_pages += int(q.get("ocr_repaired_pages") or 0)
            u = int(q.get("repair_splice_unlocated") or 0)
            if u:
                unlocated += u
                lingering.append((d["_id"], u))

        old = d.get("extraction_method")
        target = dict(per)
        if old != target:
            reconciled += 1
            if args.live:
                docs.update_one({"_id": d["_id"]}, {"$set": {
                    "extraction_method": target,
                    "extraction_method_reconciled_at": now,
                }})

    logger.info(f"title docs: {total}")
    logger.info(f"docs with ocr_repaired_at (GPT-5 repair ran): {repaired_docs}  "
                f"pages repaired: {repaired_pages}  unlocated-splice pages: {unlocated}")
    logger.info(f"TRUE per-page methods (pages[]): {dict(new_counter)}")
    logger.info(f"docs with non-frontier pages: {nonfrontier}")
    logger.info(f"docs whose counter != pages[] (need reconcile): {reconciled}")
    if lingering:
        logger.warning(f"docs with appended CORRECTED-OCR blocks (old text may linger): {len(lingering)}")
        for _id, u in lingering[:20]:
            logger.warning(f"   {_id}  unlocated={u}")
    if not args.live:
        logger.info("DRY-RUN — re-run with --live to reconcile counters.")
    else:
        logger.info(f"RECONCILED {reconciled} counters to match pages[].")
    m.close()


if __name__ == "__main__":
    main()
