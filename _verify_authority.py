from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
ch = m.db["email_chunks_v2"]
print("title w/authority 1.15:", ch.count_documents({"doc_source_type": "title_report", "doc_authority_score": 1.15}))
print("title total:", ch.count_documents({"doc_source_type": "title_report"}))
print("chunks missing authority:", ch.count_documents({"doc_authority_score": {"$exists": False}}))
import collections
c = collections.Counter()
for d in ch.find({}, {"doc_authority_score": 1}):
    c[d.get("doc_authority_score")] += 1
print("authority distribution:", dict(c))
m.close()
