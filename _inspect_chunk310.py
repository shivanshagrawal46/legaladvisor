import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
try:
    av2 = mongo.db["attachments_v2"]
    chunks = mongo.db["email_chunks_v2"]
    sha = av2.find_one({"extracted_via": "reocr_fraud_borndigital_v1"},
                       {"sha256": 1})["sha256"]
    c = chunks.find_one({"sha256": sha, "source_type": "attachment"})
    print("FIELDS:", sorted(c.keys()))
    for k in ("contextual_summary", "context", "summary", "context_summary",
              "contextualized_text", "text", "body", "embedding"):
        v = c.get(k)
        if isinstance(v, list):
            print(f"  {k}: <list len {len(v)}>")
        elif isinstance(v, str):
            print(f"  {k}: {v[:160]!r}")
        elif v is not None:
            print(f"  {k}: {type(v).__name__}")
finally:
    mongo.close()
