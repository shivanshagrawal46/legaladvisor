"""Locate messages on the Boris Lawsuit label from a given sender.

Reports, for each hit, whether we already hold it and what it carries, so we
can decide precisely what still needs ingesting.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.ingest.gmail_client import GmailClient

LABEL = "__....Boris Lawsuit"
NEEDLE = (sys.argv[1] if len(sys.argv) > 1 else "maida").lower()

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
em, ch = m.db["emails"], m.db["email_chunks_v2"]

client = GmailClient().authenticate()
label_ids = list(client.resolve_labels([LABEL]).values())

# Gmail-side search, scoped to the label.
gids = list(client.iter_message_ids(label_ids=label_ids, query=f"{NEEDLE}"))
print(f"Gmail hits for '{NEEDLE}' on the label: {len(gids)}")

vec_emails = set(ch.distinct("email_id", {"source_type": "email_body"}))

for gid in gids:
    h = client.get_full_summary(gid)
    frm = h.get("from", "")
    if NEEDLE not in frm.lower():
        continue  # matched on body text, not sender
    mid = (h.get("message_id_header") or "").strip()
    doc = em.find_one({"$or": [{"gmail_id": gid},
                               {"pst_entry_id": "gmail:" + gid},
                               {"also_seen_gmail_ids": gid},
                               {"internet_message_id": mid},
                               {"internet_message_id": mid.strip("<>")}]},
                      {"_id": 1, "source": 1, "date": 1, "attachment_ids": 1})
    real = [p for p in (h.get("parts") or [])
            if (p.get("disposition") or "").lower() != "inline" and (p.get("size") or 0) > 20000]
    print("\n" + "=" * 74)
    print(f"  gmail_id : {gid}")
    print(f"  date     : {h.get('date')}")
    print(f"  from     : {frm}")
    print(f"  subject  : {h.get('subject')}")
    print(f"  msg-id   : {mid}")
    if doc:
        origin = (doc.get("source") or {}).get("origin", "?")
        vec = "YES" if doc["_id"] in vec_emails else "NO"
        print(f"  STATUS   : HELD (origin={origin})  body-vector={vec}  "
              f"attachments_stored={len(doc.get('attachment_ids') or [])}")
    else:
        print(f"  STATUS   : *** NOT INGESTED ***")
    print(f"  attachment parts ({len(h.get('parts') or [])} total, "
          f"{len(real)} look like real docs):")
    for p in (h.get("parts") or []):
        print(f"     {(p.get('filename') or '')[:52]:52s} "
              f"{(p.get('size') or 0):>9,}B  {p.get('mime','')[:28]}")

m.close()
