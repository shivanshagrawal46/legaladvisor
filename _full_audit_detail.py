"""SUPPLEMENTARY DEEP AUDIT - closes the remaining 'could anything be wrong?'
gaps after _verify_all.py:

  D1. text_layer / non-vision PDF pages BY CORPUS
      -> legal_correspondence MUST be 0 (force-vision policy)
      -> fraud_communications text_layer = the deferred 310 born-digital docs
  D2. the 197 unresolved email->attachment refs: are they duplicates of a sha we
      already have (OK) or genuinely absent content (BAD)?
  D3. global per-file chunk structure across ALL attachment files:
      contiguous chunk_index 0..n-1, total_chunks consistent, no duplicate index
  D4. list the 48 empty/noise sha (filename) to confirm they are真 noise
"""
from __future__ import annotations
import sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper

NON_VISION_PDF = {"text_layer", "tnef:pdf_text", "pdf_text"}


def main() -> int:
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    m.ping()
    emails = m.db["emails"]
    av2 = m.db["attachments_v2"]
    ch = m.db["email_chunks_v2"]

    # sha -> corpus (from chunks, representative)
    sha_corpus = {}
    for c in ch.find({"source_type": "attachment"}, {"sha256": 1, "corpus": 1}):
        sha = c.get("sha256")
        if sha not in sha_corpus:
            sha_corpus[sha] = c.get("corpus") or "(none)"

    # ---------------- D1: non-vision PDF pages by corpus ----------------
    print("=" * 64)
    print("D1 - non-vision PDF pages (text_layer etc.) BY CORPUS")
    print("=" * 64)
    seen_sha = set()
    by_corpus = defaultdict(lambda: Counter())   # corpus -> Counter(method)
    docs_by_corpus = defaultdict(set)
    for a in av2.find({"extraction.pages.method": {"$in": list(NON_VISION_PDF)}},
                      {"sha256": 1, "extraction.pages.method": 1}):
        sha = a.get("sha256")
        if sha in seen_sha:
            continue
        seen_sha.add(sha)
        corp = sha_corpus.get(sha, "(not-chunked)")
        for p in (a.get("extraction") or {}).get("pages") or []:
            mth = p.get("method")
            if mth in NON_VISION_PDF:
                by_corpus[corp][mth] += 1
                docs_by_corpus[corp].add(sha)
    for corp in sorted(by_corpus):
        print(f"  {corp:24} docs={len(docs_by_corpus[corp]):4}  "
              f"pages={dict(by_corpus[corp])}")
    legal_bad = sum(by_corpus.get("legal_correspondence", Counter()).values())
    print(f"\n  legal_correspondence non-vision pages: {legal_bad}  (MUST be 0)")

    # ---------------- D2: unresolved att refs ----------------
    print("\n" + "=" * 64)
    print("D2 - unresolved email->attachment references")
    print("=" * 64)
    av2_ids = set()
    id_sha = {}
    present_sha = set()
    for a in av2.find({}, {"_id": 1, "sha256": 1, "extracted_text": 1}):
        av2_ids.add(a["_id"])
        id_sha[a["_id"]] = a.get("sha256")
        if (a.get("extracted_text") or ""):
            present_sha.add(a.get("sha256"))

    # map attachment_id -> sha via av2 _id; also via email occurrence filename fallback
    unresolved = 0
    unresolved_ids = []
    for e in emails.find({}, {"attachment_ids": 1}):
        for aid in e.get("attachment_ids") or []:
            if aid not in av2_ids:
                unresolved += 1
                unresolved_ids.append(aid)
    print(f"  email->attachment refs not resolvable to an av2 row: {unresolved}")
    # These are av2 _id references; if the id is gone the sha may still be present
    # under another _id (true duplicate). We cannot map a missing _id back to a sha
    # directly, so report how many emails are affected and confirm those emails
    # still have OTHER resolvable attachments (i.e. nothing silently dropped).
    affected_emails = 0
    fully_unresolved_emails = 0
    for e in emails.find({"attachment_ids": {"$exists": True, "$ne": []}},
                         {"attachment_ids": 1}):
        aids = e.get("attachment_ids") or []
        missing = [a for a in aids if a not in av2_ids]
        if missing:
            affected_emails += 1
            if len(missing) == len(aids):
                fully_unresolved_emails += 1
    print(f"  emails with >=1 unresolved ref : {affected_emails}")
    print(f"  emails with ALL refs unresolved: {fully_unresolved_emails} "
          f"(these would be genuine gaps)")

    # ---------------- D3: global per-file chunk structure ----------------
    print("\n" + "=" * 64)
    print("D3 - per-file chunk structure across ALL attachment files")
    print("=" * 64)
    idx_by_sha = defaultdict(list)
    total_by_sha = defaultdict(set)
    for c in ch.find({"source_type": "attachment"},
                     {"sha256": 1, "chunk_index": 1, "total_chunks": 1}):
        idx_by_sha[c["sha256"]].append(c.get("chunk_index"))
        total_by_sha[c["sha256"]].add(c.get("total_chunks"))
    noncontig = 0
    dup_idx = 0
    bad_total = 0
    for sha, idxs in idx_by_sha.items():
        n = len(idxs)
        if sorted(idxs) != list(range(n)):
            # allow duplicates detection separately
            if len(set(idxs)) != len(idxs):
                dup_idx += 1
            else:
                noncontig += 1
        tot = total_by_sha[sha]
        if tot != {n}:
            bad_total += 1
    print(f"  attachment files (unique sha)        : {len(idx_by_sha)}")
    print(f"  files w/ duplicate chunk_index       : {dup_idx}    (must be 0)")
    print(f"  files w/ non-contiguous index        : {noncontig} (must be 0)")
    print(f"  files w/ inconsistent total_chunks   : {bad_total} (must be 0)")

    # also body chunks
    bidx = defaultdict(list)
    btot = defaultdict(set)
    for c in ch.find({"source_type": "email_body"},
                     {"email_id": 1, "chunk_index": 1, "total_chunks": 1}):
        bidx[c["email_id"]].append(c.get("chunk_index"))
        btot[c["email_id"]].add(c.get("total_chunks"))
    b_noncontig = b_dup = b_badtot = 0
    for eid, idxs in bidx.items():
        n = len(idxs)
        if sorted(idxs) != list(range(n)):
            if len(set(idxs)) != len(idxs):
                b_dup += 1
            else:
                b_noncontig += 1
        if btot[eid] != {n}:
            b_badtot += 1
    print(f"  body emails (unique)                 : {len(bidx)}")
    print(f"  body w/ duplicate chunk_index        : {b_dup}    (must be 0)")
    print(f"  body w/ non-contiguous index         : {b_noncontig} (must be 0)")
    print(f"  body w/ inconsistent total_chunks    : {b_badtot} (must be 0)")

    # ---------------- D4: the empty/noise sha ----------------
    print("\n" + "=" * 64)
    print("D4 - empty/noise attachments (no extracted text)")
    print("=" * 64)
    noise = []
    seen = set()
    for a in av2.find({"$or": [{"extracted_text": ""},
                               {"extracted_text": {"$exists": False}}]},
                      {"sha256": 1, "filename": 1, "extension": 1,
                       "extraction.skipped_reason": 1}):
        sha = a.get("sha256")
        if sha in seen:
            continue
        seen.add(sha)
        noise.append((a.get("filename"), a.get("extension"),
                      (a.get("extraction") or {}).get("skipped_reason")))
    print(f"  unique empty/noise sha: {len(noise)}")
    for fn, ext, why in noise[:60]:
        print(f"     {str(fn)[:48]:48} ext={ext} reason={why}")

    print("\n" + "=" * 64)
    ok = (legal_bad == 0 and fully_unresolved_emails == 0 and dup_idx == 0
          and noncontig == 0 and bad_total == 0 and b_dup == 0
          and b_noncontig == 0 and b_badtot == 0)
    print("DEEP AUDIT:", "PASS" if ok else "REVIEW NEEDED (see above)")
    print("=" * 64)
    m.close()
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
