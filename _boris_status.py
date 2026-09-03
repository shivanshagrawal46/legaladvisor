"""Where does the Boris Lawsuit corpus currently end?"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

LABEL = "__....Boris Lawsuit"

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
em, ch = m.db["emails"], m.db["email_chunks_v2"]

q = {"$or": [{"gmail_labels": LABEL}, {"folder_path": LABEL}]}
n = em.count_documents(q)
print(f"Boris Lawsuit emails held: {n:,}")

print("\n=== latest 12 held ===")
for d in em.find(q, {"date": 1, "from": 1, "subject": 1, "attachment_count": 1,
                     "gmail_id": 1}).sort("date", -1).limit(12):
    print(f"  {str(d.get('date'))[:16]}  {(d.get('from') or {}).get('email','')[:30]:32s}"
          f"att={d.get('attachment_count', 0):<3} {str(d.get('subject'))[:42]}")

latest = em.find_one(q, {"date": 1}, sort=[("date", -1)])
print(f"\nwatermark (latest date held): {latest.get('date') if latest else None}")

ids = [d["_id"] for d in em.find(q, {"_id": 1})]
print(f"bodies chunked: {len(set(ch.distinct('email_id', {'email_id': {'$in': ids}, 'source_type': 'email_body'})))}"
      f" / {len(ids)}")
m.close()
