"""Clear old chunks for WebCivil docs awaiting (re)chunking.

Repairing OCR rewrites extracted_text and resets chunked_at, but the chunks
written from the earlier text are still in the collection. If the repaired text
yields fewer chunks than before, the leftover high-index chunks would survive as
orphans, so they are deleted before the embed stage runs again.
"""
from __future__ import annotations

import argparse
import sys

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

CHUNKS = "email_chunks_v2"
Q = {"instrument_subtype": "nyscef_efiled"}

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    args = ap.parse_args()

    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    docs, chunks = m.db["documents"], m.db[CHUNKS]

    pending = list(docs.find({**Q, "chunked_at": None},
                             {"document_title": 1, "case_number": 1,
                              "page_count": 1, "ocr_failed_pages": 1}))
    print(f"docs awaiting chunking: {len(pending)}")
    total_old = 0
    for d in pending:
        live = chunks.count_documents({"document_id": d["_id"]})
        total_old += live
        print(f"  {d['_id']} {d.get('case_number')} pages={d.get('page_count')} "
              f"failed={d.get('ocr_failed_pages')} old_chunks={live} "
              f"{d.get('document_title')}")
    print(f"\nold chunks to remove: {total_old}")

    if not pending or not args.live:
        if pending:
            print("(dry run -- pass --live to delete)")
        m.close()
        return 0

    ids = [d["_id"] for d in pending]
    dele = chunks.delete_many({"document_id": {"$in": ids}}).deleted_count
    docs.update_many({"_id": {"$in": ids}}, {"$set": {"chunk_count": 0}})
    print(f"deleted {dele} stale chunk(s)")
    m.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
