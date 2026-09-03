"""Mark the IPA Sanctions brief chunks as an UNFILED DRAFT.

Heuer's covering email is explicit: "a draft brief is attached for your
review ... we will circulate a revised draft later today. The brief is due
tomorrow." Without these flags the corpus would present a superseded draft
as counsel's filed position.

authority 0.85 is the existing AUTHORITY_SCORES value for "draft" (vs 1.00
default for an attachment), so the reranker down-weights it against the
filed version once that arrives.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.graph.schema import AUTHORITY_SCORES

APPLY = "--apply" in sys.argv
SHA = "341b728e0fb1549b4f7638e77f9a2358fb067e3df3ea20fd05e2c00512b8bed6"
GID = "1a0627c5abe5377d"

s = Settings.load()
m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
em, ch = m.db["emails"], m.db["email_chunks_v2"]

mail = em.find_one({"$or": [{"gmail_id": GID}, {"pst_entry_id": "gmail:" + GID}]},
                   {"_id": 1})

STAMP = {
    "is_draft": True,
    "draft_status": "circulating_for_review",
    "superseded_expected": True,
    "is_filed": False,
    "doc_authority_score": AUTHORITY_SCORES["draft"],
    "instrument_subtype": "draft_brief",
    "is_ours": True,
    "party_alignment": "our_counsel",
    "authored_by": "Westerman Ball Ederer Miller Zucker & Sharfstein LLP (W. Heuer)",
    "brief_due_date": "2026-09-03",
    "matter_context": "IPA sanctions brief",
}

print(f"attachment chunks for sha: {ch.count_documents({'sha256': SHA})}")
print(f"authority now: "
      f"{sorted({c.get('doc_authority_score') for c in ch.find({'sha256': SHA}, {'doc_authority_score': 1})})}")

if APPLY:
    r = ch.update_many({"sha256": SHA}, {"$set": STAMP})
    print(f"stamped {r.modified_count} attachment chunks as draft")
    # the covering email keeps email_body authority but is flagged as
    # transmitting a draft, so a hit on it carries the same caveat
    r2 = ch.update_many(
        {"email_id": mail["_id"], "source_type": "email_body"},
        {"$set": {"transmits_draft": True, "is_ours": True,
                  "party_alignment": "our_counsel",
                  "matter_context": "IPA sanctions brief"}})
    print(f"flagged {r2.modified_count} body chunk(s) as transmitting a draft")
    em.update_one({"_id": mail["_id"]},
                  {"$set": {"is_ours": True, "party_alignment": "our_counsel",
                            "transmits_draft": True}})
    print("\n=== after ===")
    for c in ch.find({"sha256": SHA}, {"chunk_index": 1, "doc_authority_score": 1,
                                       "is_draft": 1, "is_filed": 1,
                                       "instrument_subtype": 1, "n_tokens": 1}):
        print(f"  idx={c.get('chunk_index')} tok={c.get('n_tokens'):<5} "
              f"auth={c.get('doc_authority_score')} draft={c.get('is_draft')} "
              f"filed={c.get('is_filed')} subtype={c.get('instrument_subtype')}")
else:
    print("\nDRY — pass --apply to stamp.")
m.close()
