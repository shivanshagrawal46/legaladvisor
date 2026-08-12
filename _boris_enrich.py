"""Scoped enrichment for the chunks created by this run.

Mirrors steps 4a/4c of scripts/auto_ingest_folder.py: stamp the authority
score on anything missing it, then emit the sha/email key file that
backfill_chunk_entities consumes.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.graph.schema import authority_for, DEFAULT_AUTHORITY

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
ch = m.db["email_chunks_v2"]

# Anything not yet through the entity backfill is "new" for our purposes.
scope = {"entity_backfill_at": {"$exists": False}}
n = ch.count_documents(scope)
print(f"chunks awaiting enrichment: {n:,}")
if n == 0:
    print("nothing to do")
    m.close()
    raise SystemExit(0)

for f in ("corpus", "privilege_status", "doc_authority_score", "entity_ids"):
    print(f"   missing {f:22s}: {ch.count_documents({**scope, f: {'$exists': False}}):,}")

# 4a) authority score — same values the global stamper would write.
n_auth = 0
for st in ("attachment", "email_body"):
    r = ch.update_many(
        {**scope, "source_type": st, "doc_source_type": {"$exists": False},
         "doc_authority_score": {"$exists": False}},
        {"$set": {"doc_authority_score": authority_for(st)}})
    n_auth += r.modified_count
r = ch.update_many({**scope, "doc_authority_score": {"$exists": False}},
                   {"$set": {"doc_authority_score": DEFAULT_AUTHORITY}})
n_auth += r.modified_count
print(f"\nauthority stamped on {n_auth:,} chunks")

# 4c) build the key file for the entity backfill.
keys = set()
for d in ch.find(scope, {"source_type": 1, "sha256": 1, "email_id": 1}):
    if d.get("source_type") == "attachment" and d.get("sha256"):
        keys.add(d["sha256"])
    elif d.get("email_id"):
        keys.add(f"email:{d['email_id']}")
out = Path("_boris_enrich_keys.txt")
out.write_text("\n".join(sorted(keys)) + "\n", encoding="utf-8")
print(f"wrote {len(keys):,} scope keys -> {out}")

m.close()
