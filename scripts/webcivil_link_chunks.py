"""Stamp document provenance onto already-embedded chunks, and emit the sha
list needed for the entity backfill.

Chunks were written carrying only `document_id` + `sha256`, which means a
retrieved hit could not name its own source file, index number or docket entry
without a second query. This copies that metadata down onto each chunk. It
touches metadata only - the embedding, text, body and context are never
rewritten, so nothing needs re-embedding and no vector changes.

  python -m scripts.webcivil_link_chunks --dry-run
  python -m scripts.webcivil_link_chunks --live
  python -m scripts.webcivil_link_chunks --live --all-court-records   # + PACER
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from pymongo import UpdateMany

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.utils.logger import logger

CHUNKS = "email_chunks_v2"
SHA_FILE = Path(r"E:\WEBCIVIL_shas.txt")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", default=True)
    ap.add_argument("--live", dest="dry_run", action="store_false")
    ap.add_argument("--all-court-records", action="store_true",
                    help="also stamp the pre-existing PACER chunks, which have "
                         "the same missing-provenance gap")
    args = ap.parse_args()

    s = Settings.load()
    now = datetime.now(timezone.utc)
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    docs, chunks = m.db["documents"], m.db[CHUNKS]

    q: Dict[str, Any] = ({"source_type": "court_record"} if args.all_court_records
                         else {"instrument_subtype": "nyscef_efiled"})
    doc_list = list(docs.find(q, {
        "custody": 1, "instrument_subtype": 1, "case_number": 1, "case_title": 1,
        "court": 1, "county_clerk": 1, "document_title": 1, "docket_no": 1,
        "nyscef_doc_no": 1, "document_date": 1, "target_parties": 1,
        "page_count": 1, "ocr_method": 1}))
    logger.info(f"{len(doc_list)} document(s) in scope")

    ops: List[UpdateMany] = []
    shas: List[str] = []
    n_chunks = 0
    for d in doc_list:
        cust = d.get("custody") or {}
        srcs = cust.get("source_files") or []
        sha = cust.get("sha256")
        if sha:
            shas.append(sha)
        fields = {
            "source_filename": (srcs[0] if srcs else None),
            "source_path": cust.get("source_path"),
            "origin": cust.get("origin"),
            "retrieved_from": cust.get("retrieved_from"),
            "instrument_subtype": d.get("instrument_subtype"),
            "case_number": d.get("case_number"),
            "case_title": d.get("case_title"),
            "court": d.get("court"),
            "county_clerk": d.get("county_clerk"),
            "document_title": d.get("document_title"),
            "docket_no": d.get("docket_no"),
            "nyscef_doc_no": d.get("nyscef_doc_no"),
            "doc_page_count": d.get("page_count"),
            "doc_ocr_method": d.get("ocr_method"),
            "target_parties": d.get("target_parties") or [],
            "provenance_stamped_at": now,
        }
        fields = {k: v for k, v in fields.items() if v is not None}
        cnt = chunks.count_documents({"document_id": d["_id"]})
        n_chunks += cnt
        if cnt:
            # UpdateMany: one document maps to many chunks.
            ops.append(UpdateMany({"document_id": d["_id"]}, {"$set": fields}))

    logger.info(f"would stamp {n_chunks} chunk(s) across {len(ops)} document(s)")
    if args.dry_run:
        sample = doc_list[0] if doc_list else None
        if sample:
            cust = sample.get("custody") or {}
            logger.info(f"sample filename -> "
                        f"{(cust.get('source_files') or ['?'])[0]}")
        logger.info("DRY RUN - re-run with --live to apply.")
        m.close()
        return 0

    written = 0
    for i in range(0, len(ops), 200):
        res = chunks.bulk_write(ops[i:i + 200], ordered=False)
        written += res.modified_count
        logger.info(f"  ...{min(i + 200, len(ops))}/{len(ops)} docs, "
                    f"{written} chunks modified")

    SHA_FILE.write_text("\n".join(sorted(set(shas))), encoding="utf-8")
    logger.info(f"wrote {len(set(shas))} sha256 -> {SHA_FILE}")
    logger.info("================ PROVENANCE STAMP DONE ================")
    logger.info(f"chunks modified={written}")
    m.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
