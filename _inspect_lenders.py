from config.settings import Settings
from src.db.mongo import MongoClientWrapper
import collections

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
ents, docs = m.db["entities"], m.db["documents"]

# lenders on property entities
lenders = collections.Counter()
for e in ents.find({"kind": "property"}, {"lender": 1}):
    lv = e.get("lender")
    if lv:
        lenders[str(lv).strip()] += 1
print("=== property.lender values ===")
for k, v in lenders.most_common(40):
    print(f"  {v:3d}  {k}")

# equity rows lenders + mortgage fields
eq = docs.find_one({"source_type": "equity_schedule"}, {"equity_rows": 1})
if eq and eq.get("equity_rows"):
    r = eq["equity_rows"][0]
    print("\n=== equity_row keys ===", list(r.keys()))
    el = collections.Counter()
    for row in eq["equity_rows"]:
        if row.get("lender"):
            el[str(row["lender"]).strip()] += 1
    print("distinct equity lenders:", len(el))
    for k, v in el.most_common(15):
        print(f"  {v:3d}  {k}")
m.close()
