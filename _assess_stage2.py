"""Assess Stage-2 state after the Anthropic credit outage."""
import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
docs = m.db["documents"]
ch = m.db["email_chunks_v2"]

total = docs.count_documents({"_id": {"$regex": "^doc_p5_"}})
chunked = docs.count_documents({"_id": {"$regex": "^doc_p5_"}, "chunked_at": {"$exists": True}})
pending = total - chunked
print(f"phase5 documents total      : {total}")
print(f"  chunked (stamped)         : {chunked}")
print(f"  still pending (no chunks)  : {pending}")

# chunks with vs without contextual summary
q = {"document_id": {"$regex": "^doc_p5_"}}
n_chunks = ch.count_documents(q)
empty_ctx = ch.count_documents({**q, "context": {"$in": [None, ""]}})
good_ctx = n_chunks - empty_ctx
print(f"\nphase5 chunks written       : {n_chunks}")
print(f"  WITH contextual summary   : {good_ctx}")
print(f"  WITHOUT (outage-affected) : {empty_ctx}")

# affected documents (any empty-context chunk) -> need re-chunk
affected = ch.distinct("document_id", {**q, "context": {"$in": [None, ""]}})
print(f"\ndocuments needing re-summary: {len(affected)}")
import json
from pathlib import Path
Path("_stage2_affected_docs.json").write_text(json.dumps(affected), encoding="utf-8")
print("affected doc ids -> _stage2_affected_docs.json")
m.close()
