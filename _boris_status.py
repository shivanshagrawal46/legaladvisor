"""Read-only checkpoint report for the Boris Lawsuit label.

Answers: what is the newest email we hold for the label, how much of the
vector corpus belongs to it, and is every one of those chunks fully
enriched (context + embedding + entity linkage)?
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper

LABEL = "__....Boris Lawsuit"

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
m.ping()
db = m.db
em = db["emails"]
av2 = db["attachments_v2"]
ch = db["email_chunks_v2"]

print("=" * 72)
print("GLOBAL CORPUS")
print("=" * 72)
total_chunks = ch.count_documents({})
print(f"  emails (all sources)............ {em.count_documents({}):,}")
print(f"  attachments_v2 (OCR'd).......... {av2.count_documents({}):,}")
print(f"  email_chunks_v2 (vectors)....... {total_chunks:,}")
print(f"    with embedding................ {ch.count_documents({'embedding.0': {'$exists': True}}):,}")
print(f"    with contextual summary....... {ch.count_documents({'context': {'$nin': [None, '']}}):,}")
print(f"    entity-linked................. {ch.count_documents({'entity_ids.0': {'$exists': True}}):,}")

print()
print("=" * 72)
print(f"LABEL: {LABEL}")
print("=" * 72)

base_q = {"source.origin": "gmail_api", "gmail_labels": LABEL}
n_label = em.count_documents(base_q)
print(f"  emails pulled via Gmail API..... {n_label:,}")

# Wider net: same label seen on emails that arrived via PST/.eml too.
wide_q = {"$or": [
    {"gmail_labels": LABEL},
    {"also_seen_gmail_labels": LABEL},
    {"folder_path": {"$regex": "boris", "$options": "i"}},
]}
print(f"  emails w/ label (any origin).... {em.count_documents(wide_q):,}")

last = list(em.find(base_q, {"date": 1, "subject": 1, "from": 1, "ingested_at": 1})
            .sort("date", -1).limit(1))
if not last:
    print("  !! no emails found for this label")
    m.close()
    raise SystemExit(1)

ckpt = last[0]
print()
print("  --- CHECKPOINT (newest email held) ---")
print(f"  date........... {ckpt.get('date')}")
print(f"  ingested_at.... {ckpt.get('ingested_at')}")
print(f"  from........... {(ckpt.get('from') or {}).get('email', '')}")
print(f"  subject........ {(ckpt.get('subject') or '')[:70]}")

print()
print("  --- NEWEST 10 HELD ---")
for d in em.find(base_q, {"date": 1, "subject": 1, "from": 1}).sort("date", -1).limit(10):
    fr = (d.get("from") or {}).get("email", "")
    print(f"   {str(d.get('date'))[:19]}  {fr[:34]:34s}  {(d.get('subject') or '')[:44]}")

# Vector coverage for this label's emails.
eids = [e["_id"] for e in em.find(base_q, {"_id": 1, "attachment_ids": 1})]
att_ids = [a for e in em.find(base_q, {"attachment_ids": 1})
           for a in (e.get("attachment_ids") or [])]
shas = sorted({a["sha256"] for a in av2.find({"_id": {"$in": att_ids}}, {"sha256": 1})
               if a.get("sha256")})

scope = {"$or": [
    {"source_type": "attachment", "sha256": {"$in": shas}},
    {"source_type": "email_body", "email_id": {"$in": eids}},
]}
n_scope = ch.count_documents(scope)

print()
print("  --- VECTOR COVERAGE FOR THIS LABEL ---")
print(f"  attachments referenced.......... {len(att_ids):,} ({len(shas):,} unique sha256)")
print(f"  chunks in email_chunks_v2....... {n_scope:,}")
print(f"    email_body chunks............. {ch.count_documents({**scope, 'source_type': 'email_body'}):,}")
print(f"    attachment chunks............. {ch.count_documents({**scope, 'source_type': 'attachment'}):,}")
print(f"    with embedding................ {ch.count_documents({**scope, 'embedding.0': {'$exists': True}}):,}")
print(f"    with contextual summary....... {ch.count_documents({**scope, 'context': {'$nin': [None, '']}}):,}")
print(f"    entity-linked................. {ch.count_documents({**scope, 'entity_ids.0': {'$exists': True}}):,}")

# Emails held but never chunked -> the real backlog inside the DB.
embodied = set(ch.distinct("email_id", {"source_type": "email_body"}))
missing = [e for e in eids if e not in embodied]
print(f"  emails with NO body chunk....... {len(missing):,}")

if missing:
    # An empty/near-empty body is legitimately unchunkable; separate those
    # from genuine gaps that build_email_chunks_v2 still owes us.
    empty, real = [], []
    for d in em.find({"_id": {"$in": missing}},
                     {"date": 1, "subject": 1, "body_text": 1, "attachment_ids": 1}):
        if len((d.get("body_text") or "").strip()) < 20:
            empty.append(d)
        else:
            real.append(d)
    print(f"    empty/near-empty body (OK).... {len(empty):,}")
    print(f"    genuine gaps to rebuild....... {len(real):,}")
    for d in sorted(real, key=lambda x: str(x.get("date")), reverse=True)[:15]:
        subj = (d.get("subject") or "")[:52]
        nb = len((d.get("body_text") or "").strip())
        print(f"     {str(d.get('date'))[:19]}  {nb:>6,}ch  {subj}")

# Global backlog, not just this label.
all_ids = set(em.distinct("_id"))
print()
print("  --- GLOBAL BACKLOG ---")
print(f"  emails in DB with no body chunk. {len(all_ids - embodied):,}")
print(f"  attachments_v2 rows not chunked. "
      f"{len(set(av2.distinct('sha256')) - set(ch.distinct('sha256', {'source_type': 'attachment'}))):,}")

m.close()
