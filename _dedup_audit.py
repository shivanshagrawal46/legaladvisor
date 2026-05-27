"""Honest audit of de-duplication state across attachments_v2 and email_chunks_v2."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from config.settings import Settings
from pymongo import MongoClient

s = Settings.load()
db = MongoClient(s.mongo_uri)[s.mongo_db_name]

# ----- attachments_v2: how is it keyed? -----
av2 = db["attachments_v2"]
total_v2 = av2.count_documents({})
unique_sha_v2 = len(av2.distinct("sha256"))
unique_id_v2 = len(av2.distinct("_id"))
unique_email_ids_in_v2 = len(av2.distinct("email_id"))

print("=" * 64)
print("attachments_v2 schema audit")
print("=" * 64)
print(f"  total rows:             {total_v2}")
print(f"  unique _id:             {unique_id_v2}")
print(f"  unique sha256:          {unique_sha_v2}")
print(f"  unique email_id appearing in attachments_v2: {unique_email_ids_in_v2}")
print(f"  --> mean rows per sha256:  {total_v2/max(unique_sha_v2,1):.2f}")

# Compare with v1
av1 = db["attachments"]
total_v1 = av1.count_documents({})
unique_sha_v1 = len(av1.distinct("sha256"))
unique_id_v1 = len(av1.distinct("_id"))
print(f"\n  for reference, v1 attachments: total={total_v1}  unique_id={unique_id_v1}  unique_sha={unique_sha_v1}")

# ----- A sha256 with multiple rows --- show what its rows look like -----
pipe = [
    {"$group": {"_id": "$sha256", "n": {"$sum": 1},
                "filenames": {"$addToSet": "$filename"},
                "email_ids": {"$addToSet": "$email_id"}}},
    {"$match": {"n": {"$gt": 1}}},
    {"$sort": {"n": -1}},
    {"$limit": 3},
]
print("\nTop sha256s by row count in attachments_v2:")
for row in av2.aggregate(pipe):
    print(f"  sha256={(row['_id'] or '')[:16]}...  rows={row['n']:>3}  "
          f"filenames={list(row['filenames'])[:2]}  "
          f"distinct_email_ids={len(row['email_ids'])}")

# ----- email_chunks_v2: how is it keyed? -----
print("\n" + "=" * 64)
print("email_chunks_v2 chunk-level dedup state")
print("=" * 64)
ec2 = db["email_chunks_v2"]
total_chunks = ec2.count_documents({})
att_chunks = ec2.count_documents({"source_type": "attachment"})
unique_att_id_in_chunks = len(ec2.distinct("attachment_id"))
unique_sha_in_chunks = len(ec2.distinct("sha256", {"source_type": "attachment"}))
unique_emailatt_in_chunks = len(list(ec2.aggregate([
    {"$match": {"source_type": "attachment"}},
    {"$group": {"_id": {"e": "$email_id", "a": "$attachment_id"}}},
    {"$count": "n"}
])))
print(f"  total chunks:                              {total_chunks}")
print(f"  attachment chunks:                         {att_chunks}")
print(f"  unique attachment_id in chunks:            {unique_att_id_in_chunks}")
print(f"  unique sha256 in attachment chunks:        {unique_sha_in_chunks}")
print(f"  unique (email_id, attachment_id) pairs:    {unique_emailatt_in_chunks}")

# ----- Are sha256 duplicates getting re-embedded with identical text? -----
# Sample one sha256 that has many rows and show whether the chunk `body` is identical across rows.
print("\nLooking at one high-duplicate sha256...")
top = list(av2.aggregate(pipe[:-1] + [{"$limit": 1}]))
if top:
    sha = top[0]["_id"]
    rows_in_v2 = list(av2.find({"sha256": sha}, {"_id": 1, "email_id": 1, "filename": 1}).limit(3))
    print(f"  sha256={sha[:16]}...  has {top[0]['n']} rows in attachments_v2")
    print(f"  sample _ids → {[r['_id'] for r in rows_in_v2]}")
    chunks_for_sha = list(ec2.find({"sha256": sha, "source_type": "attachment"},
                                    {"attachment_id": 1, "email_id": 1, "chunk_index": 1, "body": 1}).limit(8))
    print(f"  chunks already written for this sha256:  {len(chunks_for_sha)}")
    if chunks_for_sha:
        bodies = set((c.get("body") or "")[:80] for c in chunks_for_sha)
        print(f"  distinct chunk-body[0:80] prefixes:      {len(bodies)}")
        for c in chunks_for_sha[:3]:
            print(f"    att_id={c['attachment_id']}  email_id={c['email_id']}  "
                  f"chunk_index={c['chunk_index']}  body[0:60]={(c.get('body') or '')[:60]!r}")
