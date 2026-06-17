from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
ents, docs, rels = m.db["entities"], m.db["documents"], m.db["relationships"]

split = list(ents.find({"needs_split": True}, {"_id": 1, "kind": 1, "canonical_name": 1,
                                               "is_david": 1, "side": 1}))
print(f"=== {len(split)} needs_split entities ===")
for e in split:
    n_owner = docs.count_documents({"owner_entity_id": e["_id"]})
    n_owns = rels.count_documents({"type": "OWNS", "src": e["_id"]})
    print(f"  {e['_id']}")
    print(f"     name: {e.get('canonical_name')}")
    print(f"     david={e.get('is_david')} side={e.get('side')} | docs.owner={n_owner} OWNS_edges={n_owns}")

# how do docs reference owners generally?
print("\n=== owner linkage fields on documents ===")
sample = docs.find_one({"owner_entity_id": {"$exists": True}}, {"owner_entity_id": 1, "owner_name_raw": 1, "source_type": 1})
print("  sample:", sample)
print("  docs with owner_entity_id:", docs.count_documents({"owner_entity_id": {"$exists": True, "$ne": None}}))
m.close()
