"""Every message from Maida Srdanovic <srdanovic@compass.com>, mailbox-wide
(not label-scoped), matched against Mongo by gmail_id AND RFC822 Message-ID so
that anything already held under a PST/other origin is not double-counted.

Writes the un-ingested gmail ids to _maida_ids.csv.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.ingest.gmail_client import GmailClient

ADDR = "srdanovic@compass.com"

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
em = m.db["emails"]

client = GmailClient().authenticate()
gids = list(client.iter_message_ids(query=f"from:{ADDR}"))
print(f"Gmail messages from {ADDR} (whole mailbox): {len(gids)}\n")

held_gids = set(em.distinct("gmail_id"))
missing, held = [], 0
rows = []
for i, gid in enumerate(gids, 1):
    if gid in held_gids:
        held += 1
        continue
    h = client.get_full_summary(gid)
    mid = (h.get("message_id_header") or "").strip()
    doc = em.find_one({"$or": [{"gmail_id": gid},
                               {"pst_entry_id": "gmail:" + gid},
                               {"also_seen_gmail_ids": gid},
                               {"internet_message_id": mid},
                               {"internet_message_id": mid.strip("<>")}]},
                      {"_id": 1})
    if doc:
        held += 1
        continue
    real = [p for p in (h.get("parts") or [])
            if (p.get("disposition") or "").lower() != "inline"
            and (p.get("size") or 0) > 20000]
    missing.append(gid)
    rows.append((h.get("date"), h.get("subject"), len(real),
                 [(p.get("filename"), p.get("size")) for p in real]))
    if i % 25 == 0:
        print(f"    ...checked {i}/{len(gids)}")

print(f"  already held            : {held}")
print(f"  GENUINELY NOT INGESTED  : {len(missing)}\n")
for d, subj, natt, files in sorted(rows, key=lambda r: str(r[0])):
    print(f"  {str(d)[:31]:33s} att={natt}  {str(subj)[:46]}")
    for fn, sz in files:
        print(f"        - {str(fn)[:56]:58s}{sz:>10,}B")

if missing:
    # ingest_gmail reads this with csv.DictReader, so the header is required —
    # without it the first id is consumed as the column name and lost.
    Path("_maida_ids.csv").write_text(
        "gmail_id\n" + "\n".join(missing), encoding="utf-8")
    print(f"\n  wrote {len(missing)} ids -> _maida_ids.csv")

m.close()
