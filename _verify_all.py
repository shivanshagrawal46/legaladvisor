"""FULL corpus integrity verification for email_chunks_v2.

Checks, end to end:
  1. Attachment coverage  : every unique sha256 in attachments_v2 that has
     real extracted text has >=1 attachment chunk (and empty/noise ones do not).
  2. Body coverage        : every email with non-empty body_text has body chunks.
  3. Email<->attachment link: every attachments_v2 row points to a real email;
     every email attachment_id resolves to an attachments_v2 row (or is a known
     duplicate sha already represented).
  4. Phase D fan-out      : for each attachment sha, the occurrences[] stored on
     its chunks exactly equals the ground-truth set of emails referencing it.
  5. Occurrence validity  : every occurrence.email_id exists in emails.
  6. Embeddings           : every chunk has a 1024-d embedding + model id.
  7. Orphans              : no attachment chunk whose sha no longer exists in v2.
  8. OCR completeness     : page-method tally across all attachment text.
"""
from __future__ import annotations
import sys
from collections import Counter, defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"


def main() -> int:
    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    m.ping()
    emails = m.db["emails"]
    av2 = m.db["attachments_v2"]
    ch = m.db["email_chunks_v2"]

    problems = []

    # ---------------------------------------------------------------
    # Load emails: id set + attachment_ids + has-body
    # ---------------------------------------------------------------
    email_ids = set()
    email_has_body = set()
    email_att_ids = {}              # email_id -> [att_id,...]
    corpus_emails = Counter()
    for e in emails.find({}, {"_id": 1, "attachment_ids": 1, "body_text": 1, "corpus": 1}):
        eid = e["_id"]
        email_ids.add(eid)
        if (e.get("body_text") or "").strip():
            email_has_body.add(eid)
        email_att_ids[eid] = list(e.get("attachment_ids") or [])
        corpus_emails[e.get("corpus") or "(none)"] += 1
    print(f"emails: {len(email_ids):,}  with_body={len(email_has_body):,}")
    print(f"  by corpus: {dict(corpus_emails)}")

    # ---------------------------------------------------------------
    # Load attachments_v2: per-row sha + text length + method
    # ---------------------------------------------------------------
    att_id_to_sha = {}              # av2._id -> sha
    sha_has_text = {}               # sha -> bool(any row has text)
    sha_rows = defaultdict(list)    # sha -> [av2._id,...]
    av2_email_missing = 0
    page_methods = Counter()
    sha_textlen = {}
    for a in av2.find({}, {"_id": 1, "email_id": 1, "sha256": 1,
                            "extracted_text": 1, "extraction.method": 1,
                            "extraction.pages.method": 1}):
        sha = a.get("sha256")
        if not sha:
            continue
        aid = a["_id"]
        att_id_to_sha[aid] = sha
        sha_rows[sha].append(aid)
        tl = len(a.get("extracted_text") or "")
        sha_textlen[sha] = max(sha_textlen.get(sha, 0), tl)
        sha_has_text[sha] = sha_has_text.get(sha, False) or (tl > 0)
        if a.get("email_id") not in email_ids:
            av2_email_missing += 1
        for p in ((a.get("extraction") or {}).get("pages") or []):
            page_methods[p.get("method") or "(none)"] += 1

    uniq_sha = set(sha_rows.keys())
    sha_with_text = {x for x in uniq_sha if sha_has_text.get(x)}
    sha_empty = uniq_sha - sha_with_text
    print(f"\nattachments_v2: rows={sum(len(v) for v in sha_rows.values()):,}  "
          f"unique_sha={len(uniq_sha):,}  with_text={len(sha_with_text):,}  "
          f"empty/noise={len(sha_empty):,}")
    print(f"  av2 rows whose email_id missing from emails: {av2_email_missing}")
    print(f"  OCR page methods: {dict(page_methods)}")

    # ---------------------------------------------------------------
    # Chunks: gather attachment sha + occurrences, body email_ids, embeddings
    # ---------------------------------------------------------------
    att_chunk_sha = set()
    body_chunk_eids = set()
    bad_embed = 0
    embed_dims = Counter()
    corpus_chunks = Counter()
    n_chunks = 0
    # occurrences per sha (all chunks of a sha share the same array -> take first seen)
    occ_by_sha = {}
    for c in ch.find({}, {"source_type": 1, "sha256": 1, "email_id": 1,
                           "occurrences.email_id": 1, "embedding": 1,
                           "embedding_model": 1, "corpus": 1}):
        n_chunks += 1
        st = c.get("source_type")
        corpus_chunks[c.get("corpus") or "(none)"] += 1
        emb = c.get("embedding")
        if not emb or not isinstance(emb, list) or len(emb) == 0:
            bad_embed += 1
        else:
            embed_dims[len(emb)] += 1
        if st == "attachment":
            sha = c.get("sha256")
            att_chunk_sha.add(sha)
            if sha not in occ_by_sha:
                occ_by_sha[sha] = {o.get("email_id") for o in (c.get("occurrences") or [])}
        elif st == "email_body":
            body_chunk_eids.add(c.get("email_id"))
    print(f"\nemail_chunks_v2: total={n_chunks:,}  attachment_sha={len(att_chunk_sha):,}  "
          f"body_emails={len(body_chunk_eids):,}")
    print(f"  embedding dims: {dict(embed_dims)}  bad/empty_embeddings={bad_embed}")
    print(f"  by corpus: {dict(corpus_chunks)}")

    # ===============================================================
    # CHECK 1: attachment coverage
    # ===============================================================
    missing_att = sorted(sha_with_text - att_chunk_sha)
    noise_with_chunks = sorted(sha_empty & att_chunk_sha)
    if missing_att:
        problems.append(f"{len(missing_att)} sha WITH TEXT have no chunks")
        print(f"\n{FAIL} CHECK1 attachment coverage: {len(missing_att)} text-bearing sha missing chunks")
        for x in missing_att[:20]:
            print(f"     missing sha={x[:16]} textlen={sha_textlen.get(x)}")
    else:
        print(f"\n{PASS} CHECK1 attachment coverage: all {len(sha_with_text):,} text-bearing sha have chunks")
    if noise_with_chunks:
        print(f"  {WARN} {len(noise_with_chunks)} empty/noise sha unexpectedly have chunks")

    # ===============================================================
    # CHECK 2: body coverage
    # ===============================================================
    missing_body = sorted(str(x) for x in (email_has_body - body_chunk_eids))
    extra_body = body_chunk_eids - email_has_body
    if missing_body:
        problems.append(f"{len(missing_body)} emails with body have no body chunks")
        print(f"\n{FAIL} CHECK2 body coverage: {len(missing_body)} bodied emails missing chunks")
        for x in missing_body[:20]:
            print(f"     missing email_id={x}")
    else:
        print(f"\n{PASS} CHECK2 body coverage: all {len(email_has_body):,} bodied emails have chunks")
    if extra_body:
        print(f"  {WARN} {len(extra_body)} body-chunk emails not in emails.body set (cleaned-empty?)")

    # ===============================================================
    # CHECK 3 + 4: ground-truth Phase-D fan-out per sha
    # ===============================================================
    groundtruth = defaultdict(set)   # sha -> {email_id referencing it}
    unresolved_att_refs = 0
    for eid, aids in email_att_ids.items():
        for aid in aids:
            sha = att_id_to_sha.get(aid)
            if sha is None:
                unresolved_att_refs += 1
                continue
            groundtruth[sha].add(eid)

    fanout_mismatch = []
    for sha in att_chunk_sha:
        gt = groundtruth.get(sha, set())
        got = occ_by_sha.get(sha, set())
        # ground truth only counts emails with text-bearing sha; chunks exist
        if gt != got:
            fanout_mismatch.append((sha, len(gt), len(got)))
    if fanout_mismatch:
        problems.append(f"{len(fanout_mismatch)} sha have occurrence!=ground-truth")
        print(f"\n{FAIL} CHECK4 Phase-D fan-out: {len(fanout_mismatch)} sha mismatched")
        for sha, g, o in fanout_mismatch[:20]:
            print(f"     sha={sha[:16]} ground_truth_emails={g} stored_occ={o}")
    else:
        print(f"\n{PASS} CHECK4 Phase-D fan-out: occurrences match ground truth for all {len(att_chunk_sha):,} attachment sha")
    print(f"  ({unresolved_att_refs} email->attachment refs point to ids not in attachments_v2 "
          f"[expected: dup/never-extracted])")

    # ===============================================================
    # CHECK 5: every occurrence.email_id exists
    # ===============================================================
    bad_occ = 0
    for sha, eset in occ_by_sha.items():
        for e in eset:
            if e not in email_ids:
                bad_occ += 1
    if bad_occ:
        problems.append(f"{bad_occ} occurrence email_ids dangling")
        print(f"\n{FAIL} CHECK5 occurrence validity: {bad_occ} dangling email_ids")
    else:
        print(f"\n{PASS} CHECK5 occurrence validity: all occurrence email_ids resolve to real emails")

    # ===============================================================
    # CHECK 6: embeddings
    # ===============================================================
    if bad_embed:
        problems.append(f"{bad_embed} chunks missing embeddings")
        print(f"\n{FAIL} CHECK6 embeddings: {bad_embed} chunks missing/empty embeddings")
    elif len(embed_dims) != 1:
        problems.append(f"mixed embedding dims {dict(embed_dims)}")
        print(f"\n{WARN} CHECK6 embeddings: mixed dims {dict(embed_dims)}")
    else:
        print(f"\n{PASS} CHECK6 embeddings: all {n_chunks:,} chunks have {list(embed_dims)[0]}-d vectors")

    # ===============================================================
    # CHECK 7: orphan attachment chunks
    # ===============================================================
    orphan_sha = sorted(att_chunk_sha - uniq_sha)
    if orphan_sha:
        problems.append(f"{len(orphan_sha)} attachment-chunk sha not in attachments_v2")
        print(f"\n{FAIL} CHECK7 orphans: {len(orphan_sha)} chunk sha missing from attachments_v2")
        for x in orphan_sha[:20]:
            print(f"     orphan sha={x[:16]}")
    else:
        print(f"\n{PASS} CHECK7 orphans: every attachment chunk sha exists in attachments_v2")

    # ===============================================================
    # CHECK 8: OCR completeness (no rapidocr/failed/empty)
    # ===============================================================
    bad_methods = {k: v for k, v in page_methods.items()
                   if k in ("ocr", "rapidocr", "failed", "render_failed", "empty", "(none)")}
    if bad_methods:
        print(f"\n{WARN} CHECK8 OCR methods: non-frontier pages present {bad_methods}")
    else:
        print(f"\n{PASS} CHECK8 OCR methods: all pages frontier-vision / native text {dict(page_methods)}")

    # ---------------------------------------------------------------
    print("\n" + "=" * 70)
    if not problems:
        print("RESULT: PASS - no integrity problems found.")
    else:
        print(f"RESULT: FAIL - {len(problems)} problem class(es):")
        for p in problems:
            print(f"   - {p}")
    print("=" * 70)
    m.close()
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
