"""Corpus-wide occurrences[] reconciliation for email_chunks_v2.

Phase D inside build_email_chunks_v2.py only syncs the sha256s that the
*current* run skipped via the idempotency filter. A file whose parent email
was ingested during a run that used --skip-occurrence-sync, or that was
interrupted before Phase D finished, keeps a stale occurrences[] array
forever. The retriever then cannot tell that the same document was also
circulated on later emails.

This walks every email in the corpus, rebuilds the ground-truth occurrence
map exactly the way Phase A does, and repairs any attachment chunk whose
fan-out disagrees. Write shape is identical to Phase D.

Read-only unless --apply is passed.

  python scripts/reconcile_occurrences.py           # report only
  python scripts/reconcile_occurrences.py --apply   # repair
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from bson import ObjectId
from loguru import logger

from config.settings import Settings
from scripts.build_email_chunks_v2 import (
    _build_occurrence,
    _date_sort_key,
    _latest_date,
)
from src.db.mongo import MongoClientWrapper

EMAIL_PROJ = {
    "_id": 1, "date": 1, "date_ym": 1, "from": 1, "to": 1,
    "subject": 1, "folder_path": 1, "attachment_ids": 1,
}


def gather_ground_truth(mongo: MongoClientWrapper) -> Dict[str, List[Dict[str, Any]]]:
    """sha256 -> occurrences[], earliest first. Mirrors Phase A."""
    attachments_v2 = mongo.db["attachments_v2"]

    att_cache: Dict[ObjectId, Dict[str, Any]] = {}
    for a in attachments_v2.find({}, {"_id": 1, "filename": 1, "sha256": 1,
                                      "extracted_text": 1}):
        # Store only what the occurrence needs; drop the text immediately so
        # the whole attachment table stays in memory cheaply.
        att_cache[a["_id"]] = {
            "_id": a["_id"],
            "filename": a.get("filename"),
            "sha256": a.get("sha256"),
            "has_text": bool((a.get("extracted_text") or "").strip()),
        }
    logger.info(f"loaded {len(att_cache):,} attachments_v2 rows")

    jobs: Dict[str, List[Dict[str, Any]]] = {}
    n_emails = 0
    for em in mongo.emails.find({}, EMAIL_PROJ):
        n_emails += 1
        for aid in em.get("attachment_ids") or []:
            att = att_cache.get(aid)
            if att is None or not att["sha256"] or not att["has_text"]:
                continue
            jobs.setdefault(att["sha256"], []).append(
                _build_occurrence(em, attachment_id=att["_id"],
                                  filename=att["filename"])
            )
    for occs in jobs.values():
        occs.sort(key=_date_sort_key)
    logger.info(f"walked {n_emails:,} emails -> {len(jobs):,} distinct attachment sha256")
    return jobs


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true",
                   help="Write the repairs (default is report-only)")
    p.add_argument("--limit-report", type=int, default=25)
    args = p.parse_args()

    s = Settings.load()
    mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    chunks = mongo.db["email_chunks_v2"]

    jobs = gather_ground_truth(mongo)

    stale: List[tuple] = []
    n_checked = n_ok = n_nochunks = 0

    for sha, occs in jobs.items():
        sample = chunks.find_one({"sha256": sha, "source_type": "attachment"},
                                 {"occurrences": 1})
        if sample is None:
            n_nochunks += 1
            continue
        n_checked += 1
        existing = sample.get("occurrences") or []
        have = {(o.get("email_id"), o.get("attachment_id")) for o in existing}
        want = {(o.get("email_id"), o.get("attachment_id")) for o in occs}
        if have == want:
            n_ok += 1
            continue
        stale.append((sha, len(have), len(want), occs))

    logger.info("=" * 70)
    logger.info(f"sha with chunks checked : {n_checked:,}")
    logger.info(f"  already correct       : {n_ok:,}")
    logger.info(f"  STALE                 : {len(stale):,}")
    logger.info(f"sha with no chunks yet  : {n_nochunks:,}")

    if stale:
        logger.info("-" * 70)
        for sha, nh, nw, occs in sorted(stale, key=lambda x: x[2] - x[1],
                                        reverse=True)[:args.limit_report]:
            fn = occs[0].get("filename") or "?"
            logger.info(f"  {nh:>3} -> {nw:<3} occ   {str(fn)[:58]}")
        if len(stale) > args.limit_report:
            logger.info(f"  ... and {len(stale) - args.limit_report:,} more")

    if not args.apply:
        logger.info("\nreport-only. re-run with --apply to repair.")
        mongo.close()
        return

    n_chunks_fixed = 0
    for sha, _nh, _nw, occs in stale:
        primary = occs[0]
        res = chunks.update_many(
            {"sha256": sha, "source_type": "attachment"},
            {"$set": {
                "occurrences": occs,
                "latest_date": _latest_date(occs),
                "email_id": primary["email_id"],
                "attachment_id": primary.get("attachment_id"),
                "filename": primary.get("filename"),
                "date": primary.get("date"),
                "date_ym": primary.get("date_ym"),
                "from_email": primary.get("from_email"),
                "to_emails": primary.get("to_emails") or [],
                "subject": primary.get("subject"),
                "folder_path": primary.get("folder_path"),
            }},
        )
        n_chunks_fixed += res.modified_count

    logger.info(f"\nrepaired {len(stale):,} sha256 across {n_chunks_fixed:,} chunks")
    mongo.close()


if __name__ == "__main__":
    main()
