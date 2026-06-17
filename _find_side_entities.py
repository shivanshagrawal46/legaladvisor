"""Find entities matching the user's side-classification names so we can set
the canonical `side` field. Read-only inventory."""
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
ents = m.db["entities"]

needles = ["mango", "gmr", "directional", "washington", "brian", "ipa", "island"]
print("=== name/alias matches for side classification ===")
for n in needles:
    rx = {"$regex": n, "$options": "i"}
    rows = list(ents.find(
        {"$or": [{"canonical_name": rx}, {"aliases": rx}, {"name_norm": rx}, {"_id": rx}]},
        {"_id": 1, "kind": 1, "canonical_name": 1, "is_david": 1, "is_david_network": 1,
         "is_ours": 1, "side": 1, "david_role": 1}))
    print(f"\n[{n}] -> {len(rows)} hit(s)")
    for r in rows[:25]:
        print(f"   {r.get('_id'):40s} kind={r.get('kind'):9s} "
              f"david={r.get('is_david')} net={r.get('is_david_network')} "
              f"ours={r.get('is_ours')} side={r.get('side')} :: {r.get('canonical_name')}")

print("\n=== entity counts by kind ===")
import collections
c = collections.Counter(e.get("kind") for e in ents.find({}, {"kind": 1}))
for k, v in c.most_common():
    print(f"   {k}: {v}")
print("   total:", ents.count_documents({}))
print("   is_david=True:", ents.count_documents({"is_david": True}))
print("   needs_review=True:", ents.count_documents({"needs_review": True}))
m.close()
