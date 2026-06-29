import json

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
ids = json.load(open("_stage2_redo_docs.json"))
r = m.db["documents"].update_many({"_id": {"$in": ids}},
                                  {"$unset": {"chunked_at": "", "chunk_count": ""}})
print("reset chunked_at on", r.modified_count, "docs")
pend = m.db["documents"].count_documents(
    {"_id": {"$regex": "^doc_p5_"}, "chunked_at": {"$exists": False}})
print("now pending (to chunk):", pend)
m.close()
