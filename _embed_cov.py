import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
ch = m.db["email_chunks_v2"]

total = ch.count_documents({"document_id": {"$regex": "^doc_p5_"}})
sample = ch.find_one({"document_id": {"$regex": "^doc_p5_"}, "embedding": {"$exists": True}},
                     {"embedding": 1})
dim = len(sample["embedding"]) if sample and sample.get("embedding") else 0
no_embed = ch.count_documents({"document_id": {"$regex": "^doc_p5_"},
                               "embedding": {"$exists": False}})
empty_embed = ch.count_documents({"document_id": {"$regex": "^doc_p5_"}, "embedding": []})
print(f"phase5 chunks total   : {total}")
print(f"embedding dim         : {dim}")
print(f"missing embedding     : {no_embed}")
print(f"empty embedding       : {empty_embed}")
m.close()
