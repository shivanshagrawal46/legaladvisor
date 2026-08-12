"""Final parity verification for the Boris Lawsuit ingest run.

Mirrors step 5 of scripts/auto_ingest_folder.py: every chunk created by this
run must carry the full enrichment field set, a contextual summary and a
1024-d embedding.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

LABEL = "__....Boris Lawsuit"
keys = [ln.strip() for ln in Path("_boris_enrich_keys.txt").read_text(
    encoding="utf-8").splitlines() if ln.strip()]
shas = [k for k in keys if not k.startswith("email:")]
eids = [k.split("email:", 1)[1] for k in keys if k.startswith("email:")]

from bson import ObjectId
eids = [ObjectId(e) for e in eids]

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
db = m.db
em, ch = db["emails"], db["email_chunks_v2"]

scope = {"$or": [
    {"source_type": "attachment", "sha256": {"$in": shas}},
    {"source_type": "email_body", "email_id": {"$in": eids}},
]}
total = ch.count_documents(scope)

print("=" * 70)
print("PARITY CHECK — chunks created by this run")
print("=" * 70)
print(f"  chunks in scope: {total:,}")

req = ["corpus", "privilege_status", "evidentiary_class", "doc_authority_score",
       "entity_ids", "entity_refs", "touches_david", "occurrences",
       "entity_backfill_at", "embedding_model", "n_tokens"]
gaps = []
for f in req:
    n = ch.count_documents({**scope, f: {"$exists": True}})
    mark = "OK " if n == total else "GAP"
    if n != total:
        gaps.append(f)
    print(f"   [{mark}] {f:22s} {n:>5,}/{total:,}")

n_ctx = ch.count_documents({**scope, "context": {"$nin": [None, ""]}})
n_emb = ch.count_documents({**scope, "embedding.0": {"$exists": True}})
for label, n in (("context", n_ctx), ("embedding", n_emb)):
    mark = "OK " if n == total else "GAP"
    if n != total:
        gaps.append(label)
    print(f"   [{mark}] {label:22s} {n:>5,}/{total:,}")

linked = ch.count_documents({**scope, "entity_ids.0": {"$exists": True}})
print(f"\n  entity-linked: {linked:,}/{total:,} ({linked/total*100:.1f}%)")

# embedding dimension spot-check
one = ch.find_one({**scope, "embedding.0": {"$exists": True}},
                  {"embedding": 1, "embedding_model": 1, "n_tokens": 1})
if one:
    print(f"  embedding dim: {len(one['embedding'])}  model: {one.get('embedding_model')}")

print("\n" + "=" * 70)
print("CORPUS TOTALS")
print("=" * 70)
print(f"  emails (all)                : {em.count_documents({}):,}")
print(f"  email_chunks_v2 (vectors)   : {ch.count_documents({}):,}")
print(f"    with embedding            : {ch.count_documents({'embedding.0': {'$exists': True}}):,}")
print(f"    with contextual summary   : {ch.count_documents({'context': {'$nin': [None, '']}}):,}")
print(f"    entity-linked             : {ch.count_documents({'entity_ids.0': {'$exists': True}}):,}")

base_q = {"source.origin": "gmail_api", "gmail_labels": LABEL}
vec_emails = set(ch.distinct("email_id", {"source_type": "email_body"}))
newest = None
for d in em.find(base_q, {"date": 1, "subject": 1, "from": 1}).sort("date", -1):
    if d["_id"] in vec_emails:
        newest = d
        break
print(f"\n  Boris emails held           : {em.count_documents(base_q):,}")
print(f"  NEW watermark (vectorised)  : {newest.get('date') if newest else None}")
print(f"     subject: {(newest.get('subject') or '')[:60] if newest else ''}")

print("\n" + ("ALL CHECKS PASSED" if not gaps else f"GAPS: {gaps}"))
m.close()
