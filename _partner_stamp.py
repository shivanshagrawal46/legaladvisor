"""Inspect then stamp partner classification onto the two partner chunks.

build_email_chunks_v2 copies only a fixed set of spine fields onto chunks, so
the partner-specific flags (is_ours, party_alignment, content_kind, ...) and
any privilege OVERRIDE must be re-applied here — the same gap that required
_stamp_brian.py for the Schuman batch.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.graph.schema import authority_for

APPLY = "--apply" in sys.argv

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
em, ch = m.db["emails"], m.db["email_chunks_v2"]

pids = list(em.find({"pst_entry_id": {"$regex": "^partners:"}},
                    {"_id": 1, "from": 1, "subject": 1}))
ids = [d["_id"] for d in pids]
print(f"partner emails: {len(ids)}")

print("\n=== chunk state BEFORE ===")
for c in ch.find({"email_id": {"$in": ids}, "source_type": "email_body"}):
    print(f"  chunk {str(c['_id'])[-8:]}  from={c.get('from_email')}  idx={c.get('chunk_index')}")
    for k in ("corpus", "privilege_status", "evidentiary_class", "doc_authority_score",
              "is_ours", "party_alignment", "sender_role", "content_kind",
              "quotes_draft_letter", "adverse_source", "contains_allegations",
              "matter_id", "n_tokens"):
        print(f"       {k:22s} = {c.get(k, '<MISSING>')}")
    print(f"       context len          = {len(c.get('context') or '')}")
    print(f"       text starts [Context]= {(c.get('text') or '').startswith('[Context]')}")
    print(f"       embedding dim        = {len(c.get('embedding') or [])}")

STAMP = {
    "matter_id": "matter_001",
    "corpus": "legal_correspondence",
    "privilege_status": "not_privileged",
    "privilege_basis": "investor_partner_not_counsel_not_client",
    "evidentiary_class": "correspondence",
    "doc_authority_score": authority_for("email_body"),
    "is_ours": True,
    "party_alignment": "mangotree_partner",
    "sender_role": "investor_partner",
    "adverse_source": False,
    "contains_allegations": False,
    "content_kind": "editorial_feedback",
    "quotes_draft_letter": True,
    "instrument_subtype": "partner_correspondence",
}

if APPLY:
    r = ch.update_many({"email_id": {"$in": ids}, "source_type": "email_body"},
                       {"$set": STAMP})
    print(f"\nstamped {r.modified_count} chunks")
    print("\n=== chunk state AFTER ===")
    for c in ch.find({"email_id": {"$in": ids}, "source_type": "email_body"}):
        print(f"  {c.get('from_email'):34s} priv={c.get('privilege_status'):16s} "
              f"is_ours={c.get('is_ours')}  align={c.get('party_alignment')}  "
              f"auth={c.get('doc_authority_score')}  kind={c.get('content_kind')}")
else:
    print("\nDRY — pass --apply to stamp.")
m.close()
