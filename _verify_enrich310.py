"""Final enrichment verification for the 310 re-OCR'd fraud born-digital docs."""
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
try:
    av2 = mongo.db["attachments_v2"]
    chunks = mongo.db["email_chunks_v2"]
    shas = sorted({r["sha256"] for r in av2.find(
        {"extracted_via": "reocr_fraud_borndigital_v1"}, {"sha256": 1})})
    q = {"sha256": {"$in": shas}}
    n = chunks.count_documents(q)

    def miss(extra):
        return chunks.count_documents({**q, **extra})

    print("=" * 60)
    print(f"ENRICHMENT VERIFICATION  ({len(shas)} sha / {n} chunks)")
    print("=" * 60)
    checks = {
        "embedding (1024-d)": {"embedding": {"$exists": False}},
        "context summary":    {"$or": [{"context": {"$exists": False}}, {"context": None}, {"context": ""}]},
        "corpus":             {"$or": [{"corpus": {"$exists": False}}, {"corpus": None}]},
        "privilege_status":   {"$or": [{"privilege_status": {"$exists": False}}, {"privilege_status": None}]},
        "evidentiary_class":  {"$or": [{"evidentiary_class": {"$exists": False}}, {"evidentiary_class": None}]},
        "doc_authority_score":{"$or": [{"doc_authority_score": {"$exists": False}}, {"doc_authority_score": None}]},
    }
    allok = True
    for label, cond in checks.items():
        m = miss(cond)
        ok = m == 0
        allok = allok and ok
        print(f"  {'OK ' if ok else 'BAD'} {label:24s} missing={m}")

    linked = chunks.count_documents({**q, "entity_ids.0": {"$exists": True}})
    david = chunks.count_documents({**q, "touches_david": True})
    print(f"  -   entity-linked chunks       {linked}/{n}")
    print(f"  -   touches_david=True         {david}/{n}")
    print("-" * 60)
    print("  corpus dist :", dict(Counter(c.get("corpus") for c in chunks.find(q, {"corpus": 1}))))
    print("  priv  dist  :", dict(Counter(c.get("privilege_status") for c in chunks.find(q, {"privilege_status": 1}))))
    print("=" * 60)
    print("RESULT:", "PASS - all 310 fully enriched" if allok else "GAP FOUND")
finally:
    mongo.close()
