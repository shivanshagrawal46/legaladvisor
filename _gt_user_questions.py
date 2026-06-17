"""Independently compute DB ground-truth answers to the user's 4 questions,
so we can grade the system's answers against them."""
import re
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.detect.dates import parse_date

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
ents, docs, events, doss = m.db["entities"], m.db["documents"], m.db["events"], m.db["property_dossier"]

IPA_RE = {"$regex": "IPA ASSET MANAGEMENT", "$options": "i"}
ipa_ids = [e["_id"] for e in ents.find({"canonical_name": IPA_RE}, {"_id": 1})]
print("IPA entity ids:", ipa_ids[:6], f"({len(ipa_ids)})")

def is_ipa(name):
    return bool(name and re.search(r"IPA\s*ASSET\s*MANAGEMENT", name, re.I))

# ── Q1: 8 Goose Hill Rd — purchase/sale by IPA ──
print("\n=== Q1: 8 Goose Hill Rd ===")
p = doss.find_one({"canonical_address": {"$regex": "GOOSE HILL", "$options": "i"}})
if not p:
    p = ents.find_one({"kind": "property", "canonical_address": {"$regex": "GOOSE HILL", "$options": "i"}})
if p:
    pid = p["_id"]
    print("property:", p.get("canonical_address"), pid)
    for ev in events.find({"property_id": pid, "event_type": {"$in": ["conveyance"]}}).sort("date", 1):
        print(f"   {ev.get('date')} {ev.get('detail')} amount={ev.get('amount')}")
else:
    print("   NOT FOUND in DB")

# ── Q2: properties where IPA is current owner (latest) ──
print("\n=== Q2: properties currently owned by IPA ===")
ipa_props = []
for d in doss.find({}, {"canonical_address": 1, "owners": 1}):
    owners = [o.get("name") for o in (d.get("owners") or [])]
    if any(is_ipa(n) for n in owners):
        ipa_props.append(d.get("canonical_address"))
print(f"   count={len(ipa_props)}")
for a in ipa_props[:40]:
    print("   -", a)

# ── Q3: 170 Hamlet Dr summary ──
print("\n=== Q3: 170 Hamlet Dr ===")
h = doss.find_one({"canonical_address": {"$regex": "HAMLET", "$options": "i"}})
if h:
    print("property:", h.get("canonical_address"))
    print("  owners:", [o.get("name") for o in (h.get("owners") or [])])
    print("  title:", h.get("title"), "insurance:", (h.get("insurance") or {}).get("in_force"),
          "equity:", (h.get("equity") or {}).get("equity"))
    print("  fact_counts:", h.get("fact_counts"))
else:
    print("   NOT FOUND")

# ── Q4: properties IPA sold since 2020 (grantor=IPA, date>=2020) ──
print("\n=== Q4: properties IPA sold since 2020 ===")
sold = {}
for ev in events.find({"event_type": "conveyance"}):
    d = ev.get("date")
    yr = d.year if hasattr(d, "year") else None
    if yr and yr >= 2020 and is_ipa(ev.get("detail", "").split("->")[0]):
        sold[ev.get("property_id")] = (ev.get("date"), ev.get("detail"))
print(f"   distinct properties IPA sold since 2020 (grantor side): {len(sold)}")
for pid, (dt, det) in list(sold.items())[:30]:
    print(f"   {dt} {det}")
m.close()
