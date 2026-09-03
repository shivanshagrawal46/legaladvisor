"""Stamp matter_id, draft flags, and version lineage on the new Boris batch.

Two documents now share the filename "Draft Brief -- IPA Sanctions.docx":
the 2 Sep draft (sha 341b728e..., 44,099 B) and the 3 Sep revision
(sha 100f032b..., 47,340 B). Without explicit lineage the retriever has no way
to prefer the current one, and an answer could quote the superseded text as
counsel's position. So:

  * 2 Sep  -> is_superseded=True, superseded_by=<3 Sep sha>, authority 0.70
  * 3 Sep  -> is_draft=True, is_current_draft=True, authority 0.85
  * BL pdf -> the blackline showing what changed between the two; flagged as
              a redline so it reads as a diff, not as the operative brief.
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper

APPLY = "--apply" in sys.argv
OLD_SHA = "341b728e0fb1549b4f7638e77f9a2358fb067e3df3ea20fd05e2c00512b8bed6"

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
em, att, ch = m.db["emails"], m.db["attachments"], m.db["email_chunks_v2"]
now = datetime.now(timezone.utc)

gids = [ln.strip() for ln in Path("_boris_backfill_ids.csv").read_text(
    encoding="utf-8").splitlines()[1:] if ln.strip()]
eids = []
for gid in gids:
    d = em.find_one({"$or": [{"gmail_id": gid}, {"pst_entry_id": "gmail:" + gid}]},
                    {"_id": 1})
    if d:
        eids.append(d["_id"])

# Resolve the two new attachment shas by filename.
new_docx = att.find_one({"email_id": {"$in": eids},
                         "filename": {"$regex": r"\.docx$", "$options": "i"}},
                        {"sha256": 1, "filename": 1})
new_pdf = att.find_one({"email_id": {"$in": eids},
                        "filename": {"$regex": r"\.pdf$", "$options": "i"}},
                       {"sha256": 1, "filename": 1})
NEW_SHA = new_docx["sha256"]
BL_SHA = new_pdf["sha256"]
print(f"revised docx : {new_docx['filename']}  {NEW_SHA[:16]}...  "
      f"chunks={ch.count_documents({'sha256': NEW_SHA})}")
print(f"blackline pdf: {new_pdf['filename']}  {BL_SHA[:16]}...  "
      f"chunks={ch.count_documents({'sha256': BL_SHA})}")
print(f"superseded   : 2 Sep draft {OLD_SHA[:16]}...  "
      f"chunks={ch.count_documents({'sha256': OLD_SHA})}")

scope_new = {"$or": [{"sha256": {"$in": [NEW_SHA, BL_SHA]}},
                     {"email_id": {"$in": eids}, "source_type": "email_body"}]}
print(f"\nnew chunks in batch: {ch.count_documents(scope_new)}")
print(f"  missing matter_id : {ch.count_documents({**scope_new, 'matter_id': {'$exists': False}})}")

if not APPLY:
    print("\nDRY — pass --apply to stamp.")
    m.close()
    raise SystemExit(0)

# 1) matter_id — the chunker does not propagate it from the parent email.
r = ch.update_many({**scope_new, "matter_id": {"$exists": False}},
                   {"$set": {"matter_id": "matter_001"}})
print(f"\nmatter_id stamped on {r.modified_count} chunks")

# 2) the revised brief — current operative draft
r = ch.update_many({"sha256": NEW_SHA}, {"$set": {
    "is_draft": True, "is_current_draft": True, "is_filed": False,
    "is_superseded": False, "supersedes": OLD_SHA,
    "draft_status": "revised_circulated_for_comment",
    "doc_authority_score": 0.85, "instrument_subtype": "draft_brief",
    "is_ours": True, "party_alignment": "our_counsel",
    "authored_by": "Westerman Ball (W. Heuer)",
    "document_version": "2026-09-03 revised (clean)",
    "matter_context": "IPA sanctions brief", "version_stamped_at": now}})
print(f"revised docx chunks stamped current: {r.modified_count}")

# 3) the blackline — a diff of old vs new, not the operative text
r = ch.update_many({"sha256": BL_SHA}, {"$set": {
    "is_draft": True, "is_redline": True, "is_filed": False,
    "is_current_draft": False,
    "draft_status": "blackline_showing_changes",
    "doc_authority_score": 0.70, "instrument_subtype": "blackline_draft_brief",
    "is_ours": True, "party_alignment": "our_counsel",
    "authored_by": "Westerman Ball (W. Heuer)",
    "document_version": "2026-09-03 blackline vs 2026-09-02",
    "compares": [OLD_SHA, NEW_SHA],
    "matter_context": "IPA sanctions brief", "version_stamped_at": now}})
print(f"blackline chunks stamped: {r.modified_count}")

# 4) the 2 Sep draft — now superseded
r = ch.update_many({"sha256": OLD_SHA}, {"$set": {
    "is_superseded": True, "superseded_by": NEW_SHA,
    "superseded_on": "2026-09-03", "is_current_draft": False,
    "doc_authority_score": 0.70,
    "document_version": "2026-09-02 draft (SUPERSEDED)",
    "version_stamped_at": now}})
print(f"2 Sep draft chunks marked superseded: {r.modified_count}")

# 5) the covering emails
r = ch.update_many({"email_id": {"$in": eids}, "source_type": "email_body"},
                   {"$set": {"is_ours": True, "party_alignment": "our_counsel",
                             "matter_context": "IPA sanctions brief"}})
print(f"body chunks flagged: {r.modified_count}")
em.update_many({"_id": {"$in": eids}},
               {"$set": {"is_ours": True, "party_alignment": "our_counsel"}})

print("\n=== after ===")
for sha, label in ((NEW_SHA, "3 Sep revised"), (BL_SHA, "3 Sep blackline"),
                   (OLD_SHA, "2 Sep superseded")):
    c = ch.find_one({"sha256": sha})
    print(f"  {label:18s} auth={c.get('doc_authority_score')} "
          f"current={c.get('is_current_draft')} superseded={c.get('is_superseded')} "
          f"version={c.get('document_version')}")
m.close()
