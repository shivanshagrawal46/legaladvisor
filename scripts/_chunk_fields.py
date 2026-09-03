"""Post-backfill linkage summary for the NYSCEF chunks."""
from __future__ import annotations

import sys

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
chunks = m.db["email_chunks_v2"]
q = {"origin": "webcivil_nyscef"}

n = chunks.count_documents(q)
print(f"NYSCEF chunks with origin marker : {n}")
for f in ("source_filename", "source_path", "case_number", "document_title",
          "nyscef_doc_no", "court", "entity_ids", "entity_sides"):
    print(f"  with {f:<18}: {chunks.count_documents({**q, f: {'$exists': True}})}")
print(f"  touches_david=True      : {chunks.count_documents({**q, 'touches_david': True})}")
print(f"  linked to >=1 property  : {chunks.count_documents({**q, 'entity_refs.properties.0': {'$exists': True}})}")
print(f"  linked to >=1 llc       : {chunks.count_documents({**q, 'entity_refs.llcs.0': {'$exists': True}})}")

print("\ntop LLC entities linked from NYSCEF chunks:")
for r in chunks.aggregate([{"$match": q}, {"$unwind": "$entity_refs.llcs"},
                           {"$group": {"_id": "$entity_refs.llcs", "n": {"$sum": 1}}},
                           {"$sort": {"n": -1}}, {"$limit": 12}]):
    print(f"  {r['_id']:<46} {r['n']}")

print("\nchunks per case (with filename provenance):")
for r in chunks.aggregate([{"$match": q},
                           {"$group": {"_id": "$case_number", "n": {"$sum": 1},
                                       "files": {"$addToSet": "$source_filename"}}},
                           {"$sort": {"_id": 1}}]):
    print(f"  {str(r['_id']):<14} chunks={r['n']:<5} distinct_files={len(r['files'])}")
m.close()
