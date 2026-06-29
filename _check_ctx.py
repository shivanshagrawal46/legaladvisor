import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
ch = m.db["email_chunks_v2"]
q = {"document_id": {"$regex": "^doc_p5_"}}
n = ch.count_documents(q)
withctx = ch.count_documents({**q, "context": {"$nin": [None, ""]}})
print("phase5 chunks so far      :", n)
print("  with contextual summary :", withctx)
for d in ch.find({**q, "context": {"$nin": [None, ""]}},
                 {"context": 1, "embedding_model": 1, "doc_category": 1}).limit(3):
    print(f"  [{d.get('doc_category')}] model={d.get('embedding_model')}")
    print("    context:", (d.get("context") or "")[:200])
m.close()
