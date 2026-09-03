"""Progress report for the WebCivil/NYSCEF ingest: OCR -> chunk -> embed."""
from __future__ import annotations

import sys
from pathlib import Path

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

ROOT = Path(r"E:\WEBCIVIL")

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def main() -> int:
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    docs, chunks = m.db["documents"], m.db["email_chunks_v2"]
    q = {"instrument_subtype": "nyscef_efiled"}

    on_disk = len(list(ROOT.rglob("*.pdf")))
    ingested = docs.count_documents(q)
    chunked = docs.count_documents({**q, "chunked_at": {"$exists": True}})
    thin = docs.count_documents({**q, "quality.needs_review": True})

    print(f"PDFs on disk        : {on_disk}")
    print(f"OCR'd into documents: {ingested}  ({on_disk - ingested} remaining)")
    print(f"chunked + embedded  : {chunked}  ({ingested - chunked} remaining)")
    print(f"thin text (<200 ch) : {thin}")

    rows = list(docs.aggregate([
        {"$match": q},
        {"$group": {"_id": "$case_number", "n": {"$sum": 1},
                    "pages": {"$sum": "$page_count"},
                    "chunked": {"$sum": {"$cond": [
                        {"$ifNull": ["$chunked_at", False]}, 1, 0]}},
                    "nchunks": {"$sum": {"$ifNull": ["$chunk_count", 0]}}}},
        {"$sort": {"_id": 1}},
    ]))
    print("\nper case:")
    disk_by_case = {}
    for d in ROOT.iterdir():
        if d.is_dir() and d.name.startswith("IndexNo_"):
            key = f"{d.name[8:-4]}/{d.name[-4:]}"
            disk_by_case[key] = len(list(d.glob("*.pdf")))
    tp = tc = 0
    for r in rows:
        disk = disk_by_case.get(r["_id"], 0)
        flag = "" if r["n"] >= disk else f"   <- {disk - r['n']} left"
        print(f"  {r['_id']:<14} ocr={r['n']:>3}/{disk:<3} pages={r['pages']:>5} "
              f"chunked={r['chunked']:>3} chunks={r['nchunks']:>5}{flag}")
        tp += r["pages"]
        tc += r["nchunks"]
    print(f"  {'TOTAL':<14} pages={tp} chunks={tc}")

    emb = chunks.count_documents({"doc_source_type": "court_record",
                                  "embedding_model": "voyage-4-large"})
    print(f"\nchunks in email_chunks_v2 (court_record, voyage-4-large): {emb}")
    missing_ctx = chunks.count_documents({"doc_source_type": "court_record",
                                          "context": ""})
    print(f"chunks missing contextual summary: {missing_ctx}")
    m.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
