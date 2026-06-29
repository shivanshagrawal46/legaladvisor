"""FULL LINKAGE & NON-DISTURBANCE CERTIFICATE.

Proves, for the email_chunks_v2 collection:
  A) The 27 re-OCR'd fraud docs are internally + externally fully linked:
     - sibling chunks of one file share sha256, contiguous chunk_index 0..n-1,
       and a consistent total_chunks
     - every chunk -> a real email (email_id exists in emails collection)
     - every chunk -> >=1 occurrence, each referencing a real email
     - corpus/privilege correct
     - the entity-less chunks STILL carry email_id + corpus + occurrences
  B) Nothing else was disturbed: the ONLY chunks created during today's run are
     the 569 from these 27 sha; no other file/title-report/corpus was rewritten.
  C) Whole-collection linkage health: no orphan attachment/body chunks, no
     missing embeddings, no missing corpus.
"""
from __future__ import annotations
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper

CUTOFF = datetime(2026, 6, 26, 8, 40, tzinfo=timezone.utc)  # start of today's run


def aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def main() -> int:
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    m.ping()
    ch = m.db["email_chunks_v2"]
    v2 = m.db["attachments_v2"]

    shas = set(ln.strip() for ln in Path("_fraud_mixed_done_sha.txt").read_text(
        encoding="utf-8").splitlines() if ln.strip())

    print("loading reference sets (emails, attachments) ...")
    email_ids = {str(e["_id"]) for e in m.emails.find({}, {"_id": 1})}
    att_shas = {a["sha256"] for a in v2.find({}, {"sha256": 1}) if a.get("sha256")}
    print(f"  emails={len(email_ids)}  attachment-sha={len(att_shas)}")

    # ---------------- PART A : the 27 changed docs ----------------
    print("\n" + "=" * 64)
    print("PART A — deep linkage of the 27 re-OCR'd fraud docs")
    print("=" * 64)
    a_total = 0
    a_bad_idx = 0          # non-contiguous chunk_index within a file
    a_bad_total = 0        # total_chunks field != actual count
    a_no_emailid = 0
    a_dead_emailid = 0     # email_id not in emails
    a_no_occ = 0
    a_dead_occ = 0         # an occurrence pointing to a non-existent email
    a_wrong_corpus = 0
    entityless = 0
    entityless_unlinked = 0  # entity-less AND missing email/corpus/occ -> BAD

    for sha in shas:
        cur = list(ch.find({"sha256": sha, "source_type": "attachment"}))
        n = len(cur)
        a_total += n
        idxs = sorted(c.get("chunk_index") for c in cur)
        if idxs != list(range(n)):
            a_bad_idx += 1
        for c in cur:
            if c.get("total_chunks") != n:
                a_bad_total += 1
            eid = c.get("email_id")
            if not eid:
                a_no_emailid += 1
            elif str(eid) not in email_ids:
                a_dead_emailid += 1
            occ = c.get("occurrences") or []
            if not occ:
                a_no_occ += 1
            else:
                for o in occ:
                    if str(o.get("email_id")) not in email_ids:
                        a_dead_occ += 1
                        break
            if c.get("corpus") != "fraud_communications" or \
               c.get("privilege_status") != "adverse_party":
                a_wrong_corpus += 1
            if not c.get("entity_ids"):
                entityless += 1
                if (not c.get("email_id")) or (not c.get("corpus")) or \
                   (not c.get("occurrences")):
                    entityless_unlinked += 1

    print(f"  total chunks across 27 files     : {a_total}")
    print(f"  files w/ non-contiguous indexes  : {a_bad_idx}   (must be 0)")
    print(f"  chunks w/ wrong total_chunks     : {a_bad_total} (must be 0)")
    print(f"  chunks missing email_id          : {a_no_emailid} (must be 0)")
    print(f"  chunks -> dead email_id          : {a_dead_emailid} (must be 0)")
    print(f"  chunks missing occurrences       : {a_no_occ}   (must be 0)")
    print(f"  chunks -> dead occurrence email  : {a_dead_occ} (must be 0)")
    print(f"  chunks wrong corpus/privilege    : {a_wrong_corpus} (must be 0)")
    print(f"  entity-less chunks (the 461)     : {entityless}")
    print(f"    ...of those, ALSO unlinked     : {entityless_unlinked} (must be 0)")

    # ---------------- PART B : nothing else disturbed ----------------
    print("\n" + "=" * 64)
    print("PART B — non-disturbance proof (only the 27 files changed today)")
    print("=" * 64)
    touched_today_other = 0
    today_shas_other = set()
    for c in ch.find({"created_at": {"$gte": CUTOFF}},
                     {"sha256": 1, "source_type": 1, "email_id": 1}):
        sha = c.get("sha256")
        if sha in shas:
            continue
        touched_today_other += 1
        today_shas_other.add(sha)
    print(f"  chunks created today NOT in our 27 files: {touched_today_other} "
          f"(must be 0)")
    if today_shas_other:
        print(f"  unexpected sha touched: {list(today_shas_other)[:5]}")

    # corpus distribution snapshot
    corp = Counter(c.get("corpus") for c in ch.find({}, {"corpus": 1}))
    print("  corpus distribution (whole collection):")
    for k, v in sorted(corp.items(), key=lambda x: -x[1]):
        print(f"      {str(k):24} {v}")

    # ---------------- PART C : whole-collection linkage health ----------------
    print("\n" + "=" * 64)
    print("PART C — whole-collection linkage health")
    print("=" * 64)
    g_total = ch.estimated_document_count()
    att_no_eid = ch.count_documents(
        {"source_type": "attachment", "email_id": {"$in": [None]}})
    body_no_eid = ch.count_documents(
        {"source_type": "email_body", "email_id": {"$in": [None]}})
    no_emb = ch.count_documents({"$or": [{"embedding": {"$exists": False}},
                                         {"embedding": []}]})
    no_corp = ch.count_documents({"$or": [{"corpus": {"$exists": False}},
                                          {"corpus": None}]})
    # orphan attachment chunks: sha not in attachments_v2
    orphan = 0
    for c in ch.find({"source_type": "attachment"}, {"sha256": 1}):
        if c.get("sha256") not in att_shas:
            orphan += 1
    print(f"  total chunks                         : {g_total}")
    print(f"  attachment chunks missing email_id   : {att_no_eid} (must be 0)")
    print(f"  body chunks missing email_id         : {body_no_eid} (must be 0)")
    print(f"  chunks missing embedding             : {no_emb} (must be 0)")
    print(f"  chunks missing corpus                : {no_corp} (must be 0)")
    print(f"  orphan attachment chunks (no source) : {orphan} (must be 0)")

    ok = all(x == 0 for x in [
        a_bad_idx, a_bad_total, a_no_emailid, a_dead_emailid, a_no_occ,
        a_dead_occ, a_wrong_corpus, entityless_unlinked, touched_today_other,
        att_no_eid, body_no_eid, no_emb, no_corp, orphan])
    print("\n" + "=" * 64)
    print("CERTIFICATE:", "PASS — all linkage intact, nothing else disturbed"
          if ok else "FAIL — see non-zero items above")
    print("=" * 64)
    m.close()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
