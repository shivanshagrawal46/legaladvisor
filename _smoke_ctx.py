import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
docs = m.db["documents"]
ch = m.db["email_chunks_v2"]

done = docs.count_documents({"_id": {"$regex": "^doc_p5_"}, "chunked_at": {"$exists": True}})
pend = docs.count_documents({"_id": {"$regex": "^doc_p5_"}, "chunked_at": {"$exists": False}})
print("phase5 chunked :", done)
print("phase5 pending :", pend)

# sample latest chunked doc, show context is non-empty (proves summary API works)
latest = list(docs.find({"_id": {"$regex": "^doc_p5_"}, "chunked_at": {"$exists": True}})
              .sort("chunked_at", -1).limit(3))
for d in latest:
    c = ch.find_one({"document_id": d["_id"]}, {"context": 1})
    ctx = (c or {}).get("context", "") if c else ""
    print(f"  {d['_id']} chunks={d.get('chunk_count')} ctx_len={len(ctx)} ctx='{ctx[:80]}'")
m.close()
