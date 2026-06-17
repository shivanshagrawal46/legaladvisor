from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
doss = m.db["property_dossier"]

print("=== David properties: equity rep vs grounded record ===")
n = 0
for d in doss.find({"is_david": True}):
    eq = d.get("equity") or {}
    fc = d.get("fact_counts") or {}
    lis_g = fc.get("lis_pendens", 0)
    jud_g = fc.get("judgments", 0)
    lien_g = fc.get("liens", 0)
    print(f"  {str(d.get('canonical_address'))[:38]:40s} "
          f"eq_lis={eq.get('lis_pendens')!r:8} foreclosure={eq.get('active_foreclosure')!r:6} "
          f"mort={eq.get('mortgage_amount')!r:>12} | grounded lis={lis_g} jud={jud_g} lien={lien_g}")
    n += 1
    if n >= 22:
        break
m.close()
