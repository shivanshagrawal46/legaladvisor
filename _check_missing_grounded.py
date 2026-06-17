from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
docs = m.db["documents"]
title = docs.count_documents({"source_type": "title_report"})
with_facts = docs.count_documents({"source_type": "title_report", "grounded_facts": {"$exists": True}})
without = list(docs.find({"source_type": "title_report", "grounded_facts": {"$exists": False}},
                         {"_id": 1, "extracted_text": 1, "grounded_at": 1}))
print(f"title={title} with_facts={with_facts} without={len(without)}")
for d in without[:30]:
    t = d.get("extracted_text") or ""
    print(f"  {d['_id'][:36]} textlen={len(t)} grounded_at={'yes' if d.get('grounded_at') else 'no'}")
m.close()
