from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.timeline.builder import timeline_for, evidence_packet

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
ents = m.db["entities"]
# a David property with lots of events
p = ents.find_one({"kind": "property", "is_david": True, "canonical_address": {"$regex": "59 BEECHER", "$options": "i"}})
pid = p["_id"]
print("property:", p.get("canonical_address"), pid)

tl = timeline_for(m, property_id=pid, limit=20)
print(f"\n=== timeline ({len(tl)} events, first 14) ===")
for e in tl[:14]:
    print(f"  {e['date']}  {e['event_type']:16s} {str(e['detail'])[:55]}")

pk = evidence_packet(m, property_id=pid)
print(f"\n=== evidence packet ===")
print(f"  address: {pk['address']} | david={pk['is_david']}")
print(f"  documents: {len(pk['documents'])}  timeline events: {len(pk['timeline'])}  findings: {len(pk['findings'])}")
print(f"  doc sample: {pk['documents'][0] if pk['documents'] else None}")
print(f"  findings: {[(f['severity'], f['title'][:50]) for f in pk['findings']]}")
m.close()
