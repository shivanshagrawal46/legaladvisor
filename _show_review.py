from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
review = m.db["entity_review"]
print("=== entity merge review candidates ===")
for r in review.find({"status": "pending"}).sort("score", -1):
    print(f"  score={r['score']}  {r['a_name']!r}  <=>  {r['b_name']!r}")
    print(f"        ({r['a']} | {r['b']})")
print("total pending:", review.count_documents({"status": "pending"}))
m.close()
