from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
ents, docs, rels = m.db["entities"], m.db["documents"], m.db["relationships"]

retired = {e["_id"] for e in ents.find({"is_active": False}, {"_id": 1})}
print("retired (split) entities:", len(retired))
print("still needs_split:", ents.count_documents({"needs_split": True}))
print("needs_review (split_status=needs_human):", ents.count_documents({"split_status": "needs_human"}))

# no document owner should point at a retired combined entity
bad = [d["_id"] for d in docs.find({"owner_entity_id": {"$in": list(retired)}}, {"_id": 1})] if retired else []
print("docs.owner_entity_id pointing at retired entity:", len(bad), bad[:5])

# no OWNS edge should originate from a retired entity
bad_edges = rels.count_documents({"type": "OWNS", "src": {"$in": list(retired)}}) if retired else 0
print("OWNS edges from retired entity:", bad_edges)

# owner_entity_ids (multi-owner) populated?
print("docs with owner_entity_ids[] (co-owners):", docs.count_documents({"owner_entity_ids": {"$exists": True}}))

# every active doc owner resolves to an existing active entity
missing = 0
for d in docs.find({"owner_entity_id": {"$exists": True, "$ne": None}}, {"owner_entity_id": 1}):
    e = ents.find_one({"_id": d["owner_entity_id"]}, {"is_active": 1})
    if not e or e.get("is_active") is False:
        missing += 1
print("docs whose owner resolves to missing/retired entity:", missing)

import collections
c = collections.Counter(e.get("side") for e in ents.find({}, {"side": 1}))
print("side distribution:", dict(c))
print("total entities:", ents.count_documents({}), "| active:", ents.count_documents({"is_active": {"$ne": False}}))
m.close()
