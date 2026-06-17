import re
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
ch = m.db["email_chunks_v2"]
ents = m.db["entities"]

# email_body link rate now
eb_total = ch.count_documents({"source_type": "email_body"})
eb_linked = ch.count_documents({"source_type": "email_body", "entity_ids.0": {"$exists": True}})
print(f"email_body linked: {eb_linked}/{eb_total} ({100*eb_linked/max(eb_total,1):.1f}%)")

# spot-check: chunks mentioning '147 Eagle' that are email/attachment, do they link the property?
prop = ents.find_one({"canonical_address": {"$regex": "147 EAGLE", "$options": "i"}}, {"_id": 1, "canonical_address": 1})
print("property:", prop)
pid = prop["_id"] if prop else None
n_mention = n_linked = 0
for d in ch.find({"$or": [{"body": {"$regex": "147 Eagle", "$options": "i"}},
                          {"text": {"$regex": "147 Eagle", "$options": "i"}}],
                  "source_type": {"$in": ["email_body", "attachment"]}},
                 {"entity_ids": 1, "source_type": 1}).limit(50):
    n_mention += 1
    if pid and pid in (d.get("entity_ids") or []):
        n_linked += 1
print(f"'147 Eagle' email/attachment chunks: {n_mention} mention, {n_linked} now linked to {pid}")
m.close()
