"""Fast, honest audit of where the v2 build stopped — bulk-query version."""
import sys
sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
sys.path.insert(0, ".")

from config.settings import Settings
from pymongo import MongoClient

print("Connecting to Mongo...", flush=True)
s = Settings.load()
db = MongoClient(s.mongo_uri)[s.mongo_db_name]
emails = db["emails"]
av2 = db["attachments_v2"]
ec2 = db["email_chunks_v2"]

# ----- 1. High-level -----
print("\n" + "=" * 70, flush=True)
print("1. High-level counts", flush=True)
print("=" * 70, flush=True)
total_emails = emails.count_documents({})
total_atts_rows = av2.count_documents({})
total_chunks = ec2.count_documents({})
email_body_chunks = ec2.count_documents({"source_type": "email_body"})
att_chunks = ec2.count_documents({"source_type": "attachment"})
print(f"  emails in 'emails':                   {total_emails:>6}", flush=True)
print(f"  rows in 'attachments_v2':             {total_atts_rows:>6}", flush=True)
print(f"  chunks already written to v2:         {total_chunks:>6}", flush=True)
print(f"    email-body chunks:                  {email_body_chunks:>6}", flush=True)
print(f"    attachment chunks:                  {att_chunks:>6}", flush=True)

# ----- 2. Load everything in bulk so we don't do 1918 round-trips -----
print("\nLoading bulk data (one round-trip each)...", flush=True)

# All email metadata we need
emails_list = list(emails.find(
    {}, {"_id": 1, "date": 1, "body_text": 1, "attachment_ids": 1, "subject": 1}
).sort([("date", 1)]))
print(f"  loaded {len(emails_list):,} emails", flush=True)

# All attachment chunk relations: {(email_id, attachment_id)}
chunk_pairs = set()
for d in ec2.find({"source_type": "attachment"},
                  {"email_id": 1, "attachment_id": 1}):
    chunk_pairs.add((d["email_id"], d["attachment_id"]))
print(f"  loaded {len(chunk_pairs):,} (email,att) chunk relations", flush=True)

# Which emails have at least one body chunk?
emails_with_body_chunk = set(ec2.distinct("email_id", {"source_type": "email_body"}))
print(f"  loaded {len(emails_with_body_chunk):,} emails with a body chunk", flush=True)

# Which emails have at least one chunk of ANY kind?
emails_with_any_chunk = set(ec2.distinct("email_id"))
print(f"  loaded {len(emails_with_any_chunk):,} emails with at least one chunk", flush=True)

# ----- 3. Walk emails in date order and classify -----
print("\n" + "=" * 70, flush=True)
print("2. Per-email completeness", flush=True)
print("=" * 70, flush=True)

fully_done = 0
partial = 0
not_started = 0
last_touched_pos = -1
first_incomplete = None

for i, email in enumerate(emails_list):
    eid = email["_id"]
    body_text = (email.get("body_text") or "").strip()
    att_ids = email.get("attachment_ids") or []
    needs_body = bool(body_text)

    body_done = (eid in emails_with_body_chunk) if needs_body else True
    needed_atts = set(att_ids)
    atts_done = needed_atts.issubset({a for (e, a) in chunk_pairs if e == eid}) if needed_atts else True

    has_any_chunk = eid in emails_with_any_chunk
    if has_any_chunk:
        last_touched_pos = i

    if (not needs_body) and (not needed_atts):
        fully_done += 1                 # vacuously complete
    elif body_done and atts_done:
        fully_done += 1
    elif has_any_chunk:
        partial += 1
        if first_incomplete is None:
            first_incomplete = (i, email)
    else:
        not_started += 1
        if first_incomplete is None:
            first_incomplete = (i, email)

# Build per-email-id attachment-completed map by inverting chunk_pairs once
from collections import defaultdict
done_atts_by_email = defaultdict(set)
for (e, a) in chunk_pairs:
    done_atts_by_email[e].add(a)

# Re-classify with the inverted map (faster + correct)
fully_done = partial = not_started = 0
last_touched_pos = -1
first_incomplete = None
for i, email in enumerate(emails_list):
    eid = email["_id"]
    body_text = (email.get("body_text") or "").strip()
    att_ids = email.get("attachment_ids") or []
    needs_body = bool(body_text)
    body_done = (eid in emails_with_body_chunk) if needs_body else True
    needed_atts = set(att_ids)
    atts_done = needed_atts.issubset(done_atts_by_email[eid]) if needed_atts else True
    has_any_chunk = eid in emails_with_any_chunk
    if has_any_chunk:
        last_touched_pos = i
    if (not needs_body) and (not needed_atts):
        fully_done += 1
    elif body_done and atts_done:
        fully_done += 1
    elif has_any_chunk:
        partial += 1
        if first_incomplete is None:
            first_incomplete = (i, email)
    else:
        not_started += 1
        if first_incomplete is None:
            first_incomplete = (i, email)

print(f"  emails fully done:        {fully_done:>5}", flush=True)
print(f"  emails partially done:    {partial:>5}", flush=True)
print(f"  emails not started yet:   {not_started:>5}", flush=True)
print(f"  highest-position-touched: #{last_touched_pos+1} of {len(emails_list)}", flush=True)

# ----- 4. Resume boundary -----
print("\n" + "=" * 70, flush=True)
print("3. Resume boundary — first incomplete email", flush=True)
print("=" * 70, flush=True)
if first_incomplete is None:
    print("  None! Every email is fully done.", flush=True)
else:
    i, email = first_incomplete
    eid = email["_id"]
    body_text = (email.get("body_text") or "").strip()
    att_ids = email.get("attachment_ids") or []
    needs_body = bool(body_text)
    body_done = (eid in emails_with_body_chunk) if needs_body else True
    needed_atts = set(att_ids)
    done_atts = done_atts_by_email[eid]
    missing_atts = needed_atts - done_atts

    print(f"  Position #{i+1} of {len(emails_list)} (date-sorted)", flush=True)
    print(f"  email_id:   {eid}", flush=True)
    print(f"  date:       {email.get('date')}", flush=True)
    print(f"  subject:    {(email.get('subject') or '')[:80]}", flush=True)
    print(f"  body_needed={needs_body}  body_chunk_written={body_done}", flush=True)
    print(f"  needed_atts={len(needed_atts)}  done_atts={len(needed_atts & done_atts)}  missing={len(missing_atts)}", flush=True)
    if missing_atts:
        sample = list(missing_atts)[:5]
        miss_docs = list(av2.find({"_id": {"$in": sample}},
                                  {"filename": 1, "sha256": 1, "extraction.method": 1}))
        for m in miss_docs:
            print(f"      missing att → filename={m.get('filename')!r}  "
                  f"sha256={(m.get('sha256') or '')[:12]}...  "
                  f"method={(m.get('extraction') or {}).get('method')}", flush=True)

# ----- 5. Integrity -----
print("\n" + "=" * 70, flush=True)
print("4. Integrity check (no half-written chunk-groups)", flush=True)
print("=" * 70, flush=True)
pipe = [
    {"$group": {
        "_id": {"e": "$email_id", "a": "$attachment_id", "s": "$source_type"},
        "hashes": {"$addToSet": "$source_hash"},
        "n": {"$sum": 1},
    }},
    {"$match": {"$expr": {"$gt": [{"$size": "$hashes"}, 1]}}},
    {"$limit": 5},
]
bad = list(ec2.aggregate(pipe))
no_embedding = ec2.count_documents({"embedding": {"$exists": False}})
empty_embedding = ec2.count_documents({"embedding": {"$size": 0}})
print(f"  chunk-groups with split source_hash:   {len(bad)}", flush=True)
print(f"  chunks missing 'embedding' field:      {no_embedding}", flush=True)
print(f"  chunks with empty embedding array:     {empty_embedding}", flush=True)
if not bad and not no_embedding and not empty_embedding:
    print("  → no half-written / broken state.", flush=True)
else:
    print("  → cleanup needed (see entries above).", flush=True)

# ----- 6. Dedup sanity (sha256 vs attachment_id) -----
print("\n" + "=" * 70, flush=True)
print("5. Dedup sanity (the topic of your question)", flush=True)
print("=" * 70, flush=True)
unique_sha_in_v2 = len(av2.distinct("sha256"))
unique_sha_chunked = len(ec2.distinct("sha256", {"source_type": "attachment"}))
unique_att_id_chunked = len(ec2.distinct("attachment_id"))
print(f"  unique sha256 in attachments_v2:                {unique_sha_in_v2}", flush=True)
print(f"  unique sha256 currently represented in chunks:  {unique_sha_chunked}", flush=True)
print(f"  unique attachment_id currently in chunks:       {unique_att_id_chunked}", flush=True)
print(f"  → if these last two were equal you'd have NO duplicates", flush=True)
print(f"  → currently {unique_att_id_chunked - unique_sha_chunked} attachment_ids share content with another", flush=True)

# Are the duplicate rows in attachments_v2 carrying identical extracted_text?
# Test: do 2 different attachment_ids with the same sha256 have identical extracted_text?
sample_dup = next(av2.aggregate([
    {"$group": {"_id": "$sha256", "ids": {"$push": "$_id"}, "n": {"$sum": 1}}},
    {"$match": {"n": {"$gte": 2}}},
    {"$limit": 1},
]), None)
if sample_dup:
    a, b = sample_dup["ids"][:2]
    da = av2.find_one({"_id": a}, {"extracted_text": 1, "filename": 1})
    dbb = av2.find_one({"_id": b}, {"extracted_text": 1, "filename": 1})
    same_text = (da.get("extracted_text") or "") == (dbb.get("extracted_text") or "")
    print(f"\n  Verification — same sha256, two different _ids:", flush=True)
    print(f"    sha256={sample_dup['_id'][:16]}...  has {sample_dup['n']} duplicate rows", flush=True)
    print(f"    extracted_text identical across rows? {same_text}", flush=True)
    print(f"    filenames: {da.get('filename')!r}  vs  {dbb.get('filename')!r}", flush=True)

print("\nDone.", flush=True)
