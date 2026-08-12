"""Find label messages we don't hold, matching on RFC822 Message-ID.

Watermark pulls filter on the message DATE, so an older email that gets
filed into the label today is invisible to them. This sweeps a bounded
recent window and identifies each message by Message-ID (the identity the
three-way dedup actually uses), so PST-origin docs are correctly counted
as held.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.ingest.gmail_client import GmailClient

LABEL = "__....Boris Lawsuit"
DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 120

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
em = m.db["emails"]

client = GmailClient().authenticate()
label_ids = list(client.resolve_labels([LABEL]).values())
after = datetime.now(timezone.utc) - timedelta(days=DAYS)
gids = list(client.iter_message_ids(label_ids=label_ids, after=after))
print(f"Gmail messages on label in last {DAYS} days: {len(gids):,}")

# Cheap pass first: anything already matched by gmail id needs no header fetch.
held_by_gid = set()
for field in ("gmail_id", "also_seen_gmail_ids"):
    held_by_gid |= {v for v in em.distinct(field, {field: {"$in": gids}}) if v}
held_by_gid |= {p.split("gmail:", 1)[1] for p in em.distinct(
    "pst_entry_id", {"pst_entry_id": {"$in": ["gmail:" + g for g in gids]}})}
todo = [g for g in gids if g not in held_by_gid]
print(f"  matched by gmail id      : {len(gids) - len(todo):,}")
print(f"  need Message-ID check    : {len(todo):,}")

missing = []
for i, gid in enumerate(todo, 1):
    if i % 25 == 0:
        print(f"    ...{i}/{len(todo)}")
    try:
        h = client.get_headers(gid)
    except Exception as exc:
        print(f"    {gid}: header error {exc}")
        continue
    mid = (h.get("message_id_header") or "").strip()
    doc = None
    if mid:
        doc = em.find_one({"internet_message_id": {"$in": [mid, mid.strip("<>")]}},
                          {"_id": 1})
    if not doc:
        missing.append((h.get("date", ""), h.get("from", ""), h.get("subject", ""),
                        h.get("n_attachments", 0), gid))

print(f"\n  GENUINELY NOT INGESTED: {len(missing)}")
for dt, frm, subj, na, gid in missing:
    print(f"    {dt[:31]:31s} {frm[:32]:32s} att={na:<3} {subj[:44]}")

if missing:
    out = Path("_boris_backfill_ids.csv")
    out.write_text("gmail_id\n" + "\n".join(x[4] for x in missing) + "\n",
                   encoding="utf-8")
    print(f"\n  wrote {len(missing)} ids -> {out}  (feed to ingest_gmail --ids-csv)")

m.close()
