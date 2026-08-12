"""Read-only reconciliation: Gmail label vs. what is actually vectorised.

Answers three questions precisely:
  1. What is the newest email that actually has vectors in email_chunks_v2?
  2. Between that date and today, how many Gmail messages exist on the label,
     and how many of those are genuinely not ingested yet?
  3. For those, how many attachments are new content vs. sha256 duplicates
     that only need a new occurrences[] entry?
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.ingest.gmail_client import GmailClient

LABEL = "__....Boris Lawsuit"

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
db = m.db
em, av2, ch = db["emails"], db["attachments_v2"], db["email_chunks_v2"]

base_q = {"source.origin": "gmail_api", "gmail_labels": LABEL}

# ---------------------------------------------------------------- 1. vectorised watermark
print("=" * 74)
print("1. WATERMARK — newest email that actually has VECTORS")
print("=" * 74)

vec_email_ids = set(ch.distinct("email_id", {"source_type": "email_body"}))
print(f"  distinct emails with a body vector (whole corpus): {len(vec_email_ids):,}")
print(f"  total vectors in email_chunks_v2                 : {ch.count_documents({}):,}")


def newest_vectorised(query, tag):
    newest = None
    for d in em.find(query, {"date": 1, "subject": 1, "from": 1}).sort("date", -1):
        if d["_id"] in vec_email_ids:
            newest = d
            break
    if newest:
        print(f"\n  [{tag}] newest VECTORISED email:")
        print(f"      date    : {newest.get('date')}")
        print(f"      from    : {(newest.get('from') or {}).get('email','')}")
        print(f"      subject : {(newest.get('subject') or '')[:60]}")
    return newest


boris_wm = newest_vectorised(base_q, "Boris Lawsuit")
newest_vectorised({}, "entire corpus")

# newest email merely STORED (may not be vectorised yet)
stored = list(em.find(base_q, {"date": 1, "subject": 1}).sort("date", -1).limit(1))
if stored:
    print(f"\n  [Boris Lawsuit] newest email merely STORED in Mongo:")
    print(f"      date    : {stored[0].get('date')}")
    print(f"      subject : {(stored[0].get('subject') or '')[:60]}")

wm_date = boris_wm.get("date") if boris_wm else None

# ---------------------------------------------------------------- 2. gap vs Gmail
print()
print("=" * 74)
print(f"2. GAP — Gmail label from the watermark to today ({datetime.now(timezone.utc):%Y-%m-%d})")
print("=" * 74)

after_day = wm_date.strftime("%Y-%m-%d") if wm_date else None
client = GmailClient().authenticate()
resolved = client.resolve_labels([LABEL])
label_ids = list(resolved.values())
gids = list(client.iter_message_ids(label_ids=label_ids,
                                    after=wm_date.replace(hour=0, minute=0, second=0)
                                    if wm_date else None))
print(f"  Gmail messages on label since {after_day}: {len(gids):,}")

# Which of those does Mongo already hold (any of the 3 dedup keys)?
held_ids = set()
for field in ("gmail_id", "also_seen_gmail_ids"):
    held_ids |= {v for v in em.distinct(field, {field: {"$in": gids}}) if v}
held_ids |= {p.split("gmail:", 1)[1]
             for p in em.distinct("pst_entry_id",
                                  {"pst_entry_id": {"$in": ["gmail:" + g for g in gids]}})}

not_ingested = [g for g in gids if g not in held_ids]
print(f"    already stored in Mongo                : {len(gids) - len(not_ingested):,}")
print(f"    NOT ingested yet (need pulling)        : {len(not_ingested):,}")

# Of the stored ones in this window, how many lack vectors?
win_q = {**base_q, "date": {"$gte": wm_date}} if wm_date else base_q
win = list(em.find(win_q, {"_id": 1, "date": 1, "subject": 1, "body_text": 1,
                           "attachment_ids": 1}))
no_vec = [d for d in win if d["_id"] not in vec_email_ids]
no_vec_real = [d for d in no_vec if len((d.get("body_text") or "").strip()) >= 20]
print(f"\n  stored in this window                    : {len(win):,}")
print(f"    lacking a body vector                  : {len(no_vec):,}"
      f"  (of which {len(no_vec_real):,} have real body text)")
for d in sorted(no_vec, key=lambda x: str(x.get("date"))):
    flag = "NEEDS VECTOR" if len((d.get("body_text") or "").strip()) >= 20 else "empty body"
    print(f"       {str(d.get('date'))[:19]}  att={len(d.get('attachment_ids') or []):>2}  "
          f"{flag:12s}  {(d.get('subject') or '')[:40]}")

# ---------------------------------------------------------------- 3. attachment sha256 dedup preview
print()
print("=" * 74)
print("3. ATTACHMENT DEDUP (sha256 / occurrences[]) for what is already stored")
print("=" * 74)

att_ids = [a for d in win for a in (d.get("attachment_ids") or [])]
rows = list(av2.find({"_id": {"$in": att_ids}}, {"sha256": 1}))
shas = {r["sha256"] for r in rows if r.get("sha256")}
already_chunked = set(ch.distinct("sha256", {"source_type": "attachment",
                                             "sha256": {"$in": list(shas)}}))
print(f"  attachment rows on these emails          : {len(att_ids):,}")
print(f"    with an OCR row in attachments_v2      : {len(rows):,}")
print(f"    unique sha256                          : {len(shas):,}")
print(f"    sha256 ALREADY vectorised (dedup hit)  : {len(already_chunked):,}"
      f"   -> only need an occurrences[] entry")
print(f"    sha256 NEW (need OCR + chunk + embed)  : {len(shas - already_chunked):,}")
print(f"  attachments with NO OCR row yet          : {len(att_ids) - len(rows):,}")

m.close()
