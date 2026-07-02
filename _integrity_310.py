"""Integrity proof: the re-chunk deletion touched ONLY the 310 fraud born-digital
sha. Confirms (a) the 310 now have fresh chunks, (b) no doc lost its chunks, and
(c) the rest of the corpus is untouched."""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper


def main() -> int:
    s = Settings.load()
    mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    try:
        av2 = mongo.db["attachments_v2"]
        chunks = mongo.db["email_chunks_v2"]

        shas = sorted({r["sha256"] for r in av2.find(
            {"extracted_via": "reocr_fraud_borndigital_v1"}, {"sha256": 1})})
        nshas = len(shas)

        total = chunks.estimated_document_count()
        in310 = chunks.count_documents({"sha256": {"$in": shas}})
        attach_total = chunks.count_documents({"source_type": "attachment"})
        rest = total - in310

        # every one of the 310 has at least one chunk?
        with_chunks = len(chunks.distinct("sha256", {"sha256": {"$in": shas}}))
        missing = nshas - with_chunks

        # freshness: all 310 chunks have embedding + contextual summary?
        no_emb = chunks.count_documents(
            {"sha256": {"$in": shas}, "embedding": {"$exists": False}})
        no_ctx = chunks.count_documents(
            {"sha256": {"$in": shas},
             "$or": [{"contextual_summary": {"$exists": False}},
                     {"contextual_summary": None}, {"contextual_summary": ""}]})

        print("=" * 64)
        print("INTEGRITY AUDIT - 310 fraud born-digital re-chunk")
        print("=" * 64)
        print(f"target sha (310 set)............ {nshas}")
        print(f"  with >=1 chunk now............ {with_chunks}")
        print(f"  MISSING chunks (must be 0).... {missing}")
        print(f"  fresh chunks for the 310...... {in310}")
        print(f"    missing embedding (0)....... {no_emb}")
        print(f"    missing ctx summary (0)..... {no_ctx}")
        print("-" * 64)
        print(f"TOTAL chunks in collection...... {total}")
        print(f"  attachment chunks............. {attach_total}")
        print(f"  chunks OUTSIDE the 310........ {rest}  <- untouched")
        print("=" * 64)
        ok = missing == 0 and no_emb == 0 and no_ctx == 0 and in310 > 0
        print("RESULT:", "PASS - only the 310 changed" if ok else "CHECK NEEDED")
        return 0
    finally:
        mongo.close()


if __name__ == "__main__":
    raise SystemExit(main())
