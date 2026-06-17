from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
doss = m.db["property_dossier"]
fnd = m.db["findings"]

# diverse picks: rich David, with-findings, with-insurance, co-victim/third-party
def total_facts(d):
    return sum((d.get("fact_counts") or {}).values())

david = sorted([d for d in doss.find({"is_david": True})], key=total_facts, reverse=True)
print("=== top David by fact richness ===")
for d in david[:8]:
    nf = fnd.count_documents({"property_id": d["_id"]})
    print(f"  {d['_id']:34s} facts={total_facts(d):3d} findings={nf} ins={d.get('insurance',{}).get('in_force')} "
          f":: {str(d.get('canonical_address'))[:40]}")

print("\n=== properties WITH findings ===")
pids = fnd.distinct("property_id")
for pid in [p for p in pids if p][:8]:
    d = doss.find_one({"_id": pid})
    if d:
        print(f"  {pid:34s} :: {str(d.get('canonical_address'))[:40]}")

print("\n=== non-David sample ===")
for d in doss.find({"is_david": {"$ne": True}}).limit(4):
    print(f"  {d['_id']:34s} side={d.get('side')} :: {str(d.get('canonical_address'))[:40]}")
m.close()
