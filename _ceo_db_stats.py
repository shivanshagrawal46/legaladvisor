"""Deep DB stats for CEO report."""
import sys
from collections import Counter
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
db = m.db


def c(name, q=None):
    try:
        return db[name].count_documents(q or {})
    except Exception:
        return 0


print("=" * 60)
print("ALL COLLECTIONS")
print("=" * 60)
for name in sorted(db.list_collection_names()):
    try:
        n = db[name].count_documents({})
    except Exception:
        n = -1
    print(f"  {name:28s} {n:>10,}")

ch = db["email_chunks_v2"]
print("\n" + "=" * 60)
print("CHUNK / VECTOR INDEX")
print("=" * 60)
total = ch.count_documents({})
print(f"  total chunks (vectors).......... {total:,}")
print(f"  with 1024-d embedding........... {ch.count_documents({'embedding.0': {'$exists': True}}):,}")
print(f"  with contextual summary......... {ch.count_documents({'context': {'$nin': [None, '']}}):,}")
print(f"  entity-linked................... {ch.count_documents({'entity_ids.0': {'$exists': True}}):,}")
print(f"  touches_david................... {ch.count_documents({'touches_david': True}):,}")
print("  by source_type:")
for k, v in Counter(x.get("source_type") for x in ch.find({}, {"source_type": 1})).most_common():
    print(f"     {str(k):20s} {v:>8,}")
print("  by corpus:")
for k, v in Counter(x.get("corpus") for x in ch.find({}, {"corpus": 1})).most_common():
    print(f"     {str(k):24s} {v:>8,}")
print("  by privilege_status:")
for k, v in Counter(x.get("privilege_status") for x in ch.find({}, {"privilege_status": 1})).most_common():
    print(f"     {str(k):20s} {v:>8,}")

print("\n" + "=" * 60)
print("DOCUMENTS / EVIDENCE")
print("=" * 60)
docs = db["documents"]
print(f"  documents (title/legal/etc)..... {docs.count_documents({}):,}")
print("  by source_type:")
for k, v in Counter(x.get("source_type") for x in docs.find({}, {"source_type": 1})).most_common(20):
    print(f"     {str(k):22s} {v:>6,}")
tot_pages = sum((d.get("page_count") or 0) for d in docs.find({}, {"page_count": 1}))
print(f"  total document pages............ {tot_pages:,}")

print("\n" + "=" * 60)
print("EMAIL / ATTACHMENT")
print("=" * 60)
print(f"  emails.......................... {c('emails'):,}")
print(f"  attachments_v2.................. {c('attachments_v2'):,}")
print(f"  attachment files (GridFS)....... {c('attachment_files.files'):,}")

print("\n" + "=" * 60)
print("KNOWLEDGE GRAPH")
print("=" * 60)
print(f"  entities........................ {c('entities'):,}")
print(f"  relationships................... {c('relationships'):,}")
print(f"  money_records................... {c('money_records'):,}")
print(f"  events.......................... {c('events'):,}")
print(f"  property_dossier................ {c('property_dossier'):,}")
print(f"  findings........................ {c('findings'):,}")
# money sum — use amount_value (the numeric field); `amount` is a display string.
try:
    amt = 0.0
    for r in db["money_records"].find({}, {"amount_value": 1}):
        a = r.get("amount_value")
        if isinstance(a, (int, float)):
            amt += a
    print(f"  money_records total amount...... ${amt:,.2f}")
except Exception as e:
    print("  money sum error:", e)
m.close()
