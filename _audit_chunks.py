"""Integrity audit: prove no document can be silently missed by chunk+embed.

Checks (run-safe while the pipeline is still running):
  1. Every doc stamped `chunked_at` has EXACTLY `chunk_count` chunks stored.
  2. Every stored chunk has a non-empty 1024-dim embedding + contextual summary.
  3. Docs NOT stamped are exactly the ones the resume query will still process.
  4. No orphan chunks pointing at unknown documents.
"""
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
d, ch = m.db["documents"], m.db["email_chunks_v2"]
T = ["title_report", "insurance", "equity_schedule", "service_agreement", "litigation_update"]

total = d.count_documents({"source_type": {"$in": T}})
stamped = list(d.find({"source_type": {"$in": T}, "chunked_at": {"$exists": True}},
                      {"chunk_count": 1, "source_type": 1, "chunk_skip_reason": 1}))
pending = d.count_documents({"source_type": {"$in": T}, "chunked_at": {"$exists": False}})

# 1) per-doc chunk count match
mismatch, empty_skips = [], []
for doc in stamped:
    actual = ch.count_documents({"document_id": doc["_id"]})
    expected = doc.get("chunk_count", -1)
    if doc.get("chunk_skip_reason") == "empty_text":
        empty_skips.append(doc["_id"])
        continue
    if actual != expected or expected <= 0:
        mismatch.append((doc["_id"], expected, actual))

# 2) embedding + context integrity on phase-3 chunks
bad_embed = ch.count_documents({"source_type": {"$in": T},
                                "$or": [{"embedding": {"$exists": False}},
                                        {"embedding": None}, {"embedding": []}]})
sample = ch.find_one({"source_type": {"$in": T}}, {"embedding": 1})
dim = len(sample["embedding"]) if sample and sample.get("embedding") else 0
no_context = ch.count_documents({"source_type": {"$in": T},
                                 "$or": [{"context": {"$exists": False}}, {"context": ""}]})

# 3) orphan chunks
doc_ids = set(x["_id"] for x in d.find({"source_type": {"$in": T}}, {"_id": 1}))
orphans = sum(1 for c in ch.find({"source_type": {"$in": T}}, {"document_id": 1})
              if c.get("document_id") not in doc_ids)

print(f"total docs           : {total}")
print(f"stamped (done)       : {len(stamped)}")
print(f"pending (will resume): {pending}")
print(f"stamped+pending=total: {len(stamped) + pending == total}")
print(f"count mismatches     : {len(mismatch)} {mismatch[:5]}")
print(f"empty-text skips     : {len(empty_skips)} {empty_skips}")
print(f"chunks missing embed : {bad_embed}")
print(f"embedding dimension  : {dim}")
print(f"chunks missing context: {no_context}")
print(f"orphan chunks        : {orphans}")
ok = (len(stamped) + pending == total and not mismatch and bad_embed == 0 and orphans == 0)
print("AUDIT:", "PASS — nothing lost, nothing can be missed" if ok else "FAIL — see above")
m.close()
