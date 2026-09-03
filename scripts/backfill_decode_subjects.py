"""Decode RFC2047-encoded subjects already stored raw in the corpus.

Both ingestion parsers read `msg.get("Subject")` off a compat32 message, which
returns '=?utf-8?B?...?=' verbatim for any subject with a non-ASCII character.
An em-dash was enough, so the affected rows are disproportionately the recent
Heuer/Rakesh threads ("IPA Brief — MangoTree Position on Scope", "Plan
Administrator Agreement — Hold Pending September 14 Hearing", ...). Stored
raw, those subjects are invisible to BM25 and their subject-derived thread_id
fragments the thread.

Repairs, on `emails`:  subject, subject_normalized, conversation_topic, and
thread_id where it was built from the (encoded) subject.
On `email_chunks_v2`:  subject.

Idempotent — only touches rows whose subject still starts with '=?'.

    python -m scripts.backfill_decode_subjects            # dry run
    python -m scripts.backfill_decode_subjects --apply
"""
from __future__ import annotations

import argparse
import sys
from typing import Dict, List

from pymongo import UpdateOne

from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.utils.logger import logger
from scripts.ingest_eml_folder import _decode_mime_header, _normalize_subject


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    s = Settings.load()
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    em, ch = m.db["emails"], m.db["email_chunks_v2"]
    q = {"subject": {"$regex": r"^\s*=\?"}}

    # ---- emails --------------------------------------------------------
    email_ops: List[UpdateOne] = []
    decoded_by_id: Dict = {}
    for d in em.find(q, {"subject": 1, "thread_id": 1}):
        dec = _decode_mime_header(d["subject"])
        if dec == d["subject"]:
            logger.warning(f"could not decode {d['_id']}: {d['subject'][:60]}")
            continue
        norm = _normalize_subject(dec)
        upd = {"subject": dec, "subject_normalized": norm, "conversation_topic": norm}
        # thread_id built from the encoded subject -> rebuild from the decoded one
        if str(d.get("thread_id") or "").startswith("subj:"):
            upd["thread_id"] = "subj:" + norm[:120]
        decoded_by_id[d["_id"]] = dec
        email_ops.append(UpdateOne({"_id": d["_id"]}, {"$set": upd}))
        logger.info(f"  {str(d['_id'])[-6:]}  {d['subject'][:34]}...  ->  {dec[:60]}")

    # ---- chunks ----------------------------------------------------------
    chunk_ops: List[UpdateOne] = []
    for c in ch.find(q, {"subject": 1}):
        dec = _decode_mime_header(c["subject"])
        if dec != c["subject"]:
            chunk_ops.append(UpdateOne({"_id": c["_id"]}, {"$set": {"subject": dec}}))

    logger.info(f"emails to repair: {len(email_ops)}   chunks to repair: {len(chunk_ops)}")
    if not args.apply:
        logger.info("DRY RUN — re-run with --apply to write.")
        m.close()
        return 0

    if email_ops:
        r = em.bulk_write(email_ops, ordered=False)
        logger.info(f"emails repaired: {r.modified_count}")
    if chunk_ops:
        r = ch.bulk_write(chunk_ops, ordered=False)
        logger.info(f"chunks repaired: {r.modified_count}")
    logger.info(f"remaining encoded — emails: {em.count_documents(q)}  "
                f"chunks: {ch.count_documents(q)}")
    m.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
