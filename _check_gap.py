from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
ents, docs, fnd = m.db["entities"], m.db["documents"], m.db["findings"]

# is 183MA LLC a David entity?
for e in ents.find({"canonical_name": {"$regex": "183MA", "$options": "i"}}):
    print("entity:", e["_id"], "name:", e.get("canonical_name"), "is_david:", e.get("is_david"),
          "side:", e.get("side"), "active:", e.get("is_active"))

pid = "ent_prop_0200468000500010000"
print("\nfindings for 183 Mark Tree:", fnd.count_documents({"property_id": pid}))

# what does the grounded chain_of_title say for the title doc(s) of this property?
prop = ents.find_one({"_id": pid})
for did in (prop.get("title_doc_ids") or []):
    d = docs.find_one({"_id": did}, {"grounded_facts": 1})
    for it in (d.get("grounded_facts") or {}).get("chain_of_title", []):
        print(f"  COT grantee={it.get('grantee')!r} dated={it.get('dated')!r} amt={it.get('amount')!r}")
m.close()
