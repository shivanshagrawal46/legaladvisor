"""Give duplicate-send attachments their missing attachments_v2 row.

When the same file is emailed twice, the second `attachments` row can end up
with no `attachments_v2` counterpart (the extractor skips content whose sha256
was already processed). Phase A of build_email_chunks_v2 walks
email.attachment_ids -> attachments_v2, so those rows are invisible: the chunk
never learns that a later email also carried the document.

The content is already extracted under the same sha256, so no OCR is needed —
copy the text from the sibling row. Once the row exists, Phase A and
reconcile_occurrences agree, and the fix is stable across future runs.

Only touches attachments whose sha256 already has extracted text AND already
has chunks. Attachments with no extracted content anywhere are left alone;
those need real OCR and are a separate concern.

  python scripts/backfill_dedup_attachment_rows.py           # report only
  python scripts/backfill_dedup_attachment_rows.py --apply
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from loguru import logger
from pymongo import UpdateOne

from config.settings import Settings
from src.db.mongo import MongoClientWrapper


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    args = p.parse_args()

    s = Settings.load()
    mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    att = mongo.db["attachments"]
    av2 = mongo.db["attachments_v2"]
    chunks = mongo.db["email_chunks_v2"]

    v2_ids = set(av2.distinct("_id"))
    v2_blank = set(av2.distinct("_id", {"$or": [{"extracted_text": None},
                                                {"extracted_text": ""}]}))
    chunk_shas = set(chunks.distinct("sha256", {"source_type": "attachment"}))

    # One donor row per sha: the extracted content to clone.
    donor: dict[str, dict] = {}
    for a in av2.find({"extracted_text": {"$nin": [None, ""]}},
                      {"sha256": 1, "extracted_text": 1, "extraction": 1,
                       "extension": 1, "extracted_via": 1}):
        donor.setdefault(a["sha256"], a)
    logger.info(f"donor rows available for {len(donor):,} sha256")

    ops, skipped_no_donor = [], 0
    for r in att.find({}, {"_id": 1, "sha256": 1, "filename": 1, "email_id": 1,
                           "gridfs_id": 1, "size_bytes": 1, "extension": 1}):
        if r["_id"] in v2_ids and r["_id"] not in v2_blank:
            continue
        sha = r.get("sha256")
        d = donor.get(sha) if sha else None
        if not d or sha not in chunk_shas:
            skipped_no_donor += 1
            continue

        ext = (r.get("extension") or d.get("extension") or "").lstrip(".").lower()
        ops.append(UpdateOne(
            {"_id": r["_id"]},
            {"$set": {
                "email_id": r.get("email_id"),
                "filename": r.get("filename"),
                "extension": ext,
                "sha256": sha,
                "gridfs_id": r.get("gridfs_id"),
                "size_bytes": r.get("size_bytes"),
                "extracted_text": d["extracted_text"],
                "extraction": d.get("extraction"),
                "extracted_at": datetime.now(timezone.utc),
                "extracted_via": "dedup_sha_sibling_backfill",
                "dedup_source_attachment_id": d["_id"],
            }},
            upsert=True,
        ))

    logger.info(f"rows to backfill from a same-sha donor : {len(ops):,}")
    logger.info(f"rows left alone (no extracted content) : {skipped_no_donor:,}")

    if not ops:
        mongo.close()
        return
    if not args.apply:
        logger.info("report-only. re-run with --apply to write.")
        mongo.close()
        return

    res = av2.bulk_write(ops, ordered=False)
    logger.info(f"upserted={res.upserted_count}  modified={res.modified_count}")
    mongo.close()


if __name__ == "__main__":
    main()
