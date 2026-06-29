"""Verify Phase-5 chunk integrity after the concurrent-worker overlap.

Checks for staleness/corruption:
  - doc.chunk_count == actual #chunks in email_chunks_v2
  - chunk_index set == {0 .. total_chunks-1} (no dupes, no gaps)
  - total_chunks consistent within a doc
  - orphan chunks (document_id has no parent doc / not stamped)
Writes _stage2_redo_docs.json = docs needing redo (corrupt OR empty-context).
"""
import json
from collections import defaultdict
from pathlib import Path

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
docs = m.db["documents"]
ch = m.db["email_chunks_v2"]

# gather chunk facts per phase5 document
per = defaultdict(lambda: {"idx": [], "total": set(), "empty_ctx": 0})
for c in ch.find({"document_id": {"$regex": "^doc_p5_"}},
                 {"document_id": 1, "chunk_index": 1, "total_chunks": 1, "context": 1}):
    d = per[c["document_id"]]
    d["idx"].append(c.get("chunk_index"))
    d["total"].add(c.get("total_chunks"))
    if not (c.get("context") or ""):
        d["empty_ctx"] += 1

# doc-level stamps
stamp = {d["_id"]: d.get("chunk_count")
         for d in docs.find({"_id": {"$regex": "^doc_p5_"}},
                            {"chunk_count": 1, "chunked_at": 1})}
stamped_ids = {d["_id"] for d in docs.find(
    {"_id": {"$regex": "^doc_p5_"}, "chunked_at": {"$exists": True}}, {"_id": 1})}

count_mismatch, dup_idx, gap_idx, total_inconsistent, orphan = [], [], [], [], []
empty_ctx_docs = []
for doc_id, d in per.items():
    idx = d["idx"]
    n = len(idx)
    if doc_id not in stamp:
        orphan.append(doc_id)
        continue
    if stamp.get(doc_id) is not None and stamp[doc_id] != n:
        count_mismatch.append((doc_id, stamp[doc_id], n))
    if len(set(idx)) != len(idx):
        dup_idx.append(doc_id)
    if set(idx) != set(range(n)):
        gap_idx.append(doc_id)
    if len(d["total"]) > 1:
        total_inconsistent.append((doc_id, sorted(d["total"])))
    if d["empty_ctx"] > 0:
        empty_ctx_docs.append(doc_id)

print(f"phase5 docs with chunks      : {len(per)}")
print(f"stamped chunked docs         : {len(stamped_ids)}")
print(f"--- INTEGRITY ---")
print(f"count mismatch (stale/dupe)  : {len(count_mismatch)}  {count_mismatch[:5]}")
print(f"duplicate chunk indices      : {len(dup_idx)}  {dup_idx[:5]}")
print(f"index gaps (missing chunk)   : {len(gap_idx)}  {gap_idx[:5]}")
print(f"inconsistent total_chunks    : {len(total_inconsistent)}  {total_inconsistent[:5]}")
print(f"orphan chunks (no parent)    : {len(orphan)}  {orphan[:5]}")
print(f"--- SUMMARY QUALITY ---")
print(f"docs with empty-context chunk: {len(empty_ctx_docs)}")

# docs that exist but were never chunked
all_p5 = {d["_id"] for d in docs.find({"_id": {"$regex": "^doc_p5_"}}, {"_id": 1})}
pending = all_p5 - stamped_ids
print(f"pending (never chunked)      : {len(pending)}")

# redo set = corrupt + empty-context (clear & redo); pending handled automatically
corrupt = set([x[0] for x in count_mismatch]) | set(dup_idx) | set(gap_idx) | set([x[0] for x in total_inconsistent])
redo = sorted(corrupt | set(empty_ctx_docs))
Path("_stage2_redo_docs.json").write_text(json.dumps(redo), encoding="utf-8")
print(f"\nREDO list (corrupt + empty-ctx): {len(redo)} -> _stage2_redo_docs.json")
print(f"corrupt docs specifically      : {len(corrupt)}")
m.close()
