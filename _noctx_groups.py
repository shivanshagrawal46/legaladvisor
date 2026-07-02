import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
try:
    ch = mongo.db["email_chunks_v2"]
    q = {"$or": [{"context": {"$exists": False}}, {"context": None}, {"context": ""}]}
    eids = Counter()
    shas = Counter()
    for c in ch.find(q, {"email_id": 1, "sha256": 1, "source_type": 1}):
        if c.get("source_type") == "attachment":
            shas[c.get("sha256")] += 1
        else:
            eids[c.get("email_id")] += 1
    print("distinct email_ids (email_body):", len(eids))
    print("  chunk counts per email:", dict(eids))
    print("distinct attachment sha:", len(shas), dict(shas))
finally:
    mongo.close()
