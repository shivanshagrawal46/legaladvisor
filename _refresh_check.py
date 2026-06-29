"""Check current email_chunks_v2 state for the 2 re-OCR'd shas vs the text
now stored in attachments_v2, so we know how stale the chunks are."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper

PREFIXES = {"zip(33c8)": "33c8d9696d14", "tiana(f28af4)": "f28af47ed442"}


def main() -> int:
    s = Settings.load()
    mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    try:
        mongo.ping()
        v2 = mongo.db["attachments_v2"]
        ch = mongo.db["email_chunks_v2"]
        for label, pfx in PREFIXES.items():
            row = v2.find_one({"sha256": {"$regex": f"^{pfx}"}},
                              {"sha256": 1, "extracted_text": 1, "extraction.method": 1})
            if not row:
                print(f"{label}: NOT FOUND in attachments_v2"); continue
            sha = row["sha256"]
            txt_len = len(row.get("extracted_text") or "")
            method = (row.get("extraction") or {}).get("method")
            n_chunks = ch.count_documents({"sha256": sha, "source_type": "attachment"})
            # estimate chars currently represented in chunks
            agg = list(ch.aggregate([
                {"$match": {"sha256": sha, "source_type": "attachment"}},
                {"$group": {"_id": None, "chars": {"$sum": {"$strLenCP": {"$ifNull": ["$text", ""]}}}}},
            ]))
            chunk_chars = agg[0]["chars"] if agg else 0
            print(f"{label}: sha={sha[:16]} method={method} "
                  f"v2_text={txt_len:,} chars | chunks={n_chunks} (~{chunk_chars:,} chars)")
        return 0
    finally:
        mongo.close()


if __name__ == "__main__":
    raise SystemExit(main())
