"""PARALLEL re-chunk of the fraud born-digital sha that were force-visioned
(extracted_via='reocr_fraud_borndigital_v1'). 12 worker threads (re-chunk is
API-I/O bound: contextual summary + embedding), reusing the exact
build_email_chunks_v2 functions. Deletes stale chunks for these sha first, then
re-inserts fresh chunks (1000/200) with contextual summaries + Voyage embeddings.
"""
from __future__ import annotations
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.utils.logger import logger
from scripts.build_email_chunks_v2 import (
    VoyageEmbedder, ContextualSummarizer,
    _process_one_sha256, _build_occurrence, _date_sort_key, _Flusher,
    EMBEDDING_MODEL, CHUNK_SIZE_TOKENS, CHUNK_OVERLAP_TOKENS,
)

TAG = "reocr_fraud_borndigital_v1"
WORKERS = 12


def main() -> int:
    s = Settings.load()
    mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    av2 = mongo.db["attachments_v2"]
    chunks = mongo.db["email_chunks_v2"]
    emails = mongo.db["emails"]
    embedder = VoyageEmbedder(api_key=s.voyage_api_key, model=EMBEDDING_MODEL)
    summarizer = ContextualSummarizer(api_key=s.anthropic_api_key,
                                      model="claude-sonnet-4-6")
    try:
        mongo.ping()
        rows = list(av2.find({"extracted_via": TAG},
                             {"_id": 1, "sha256": 1, "filename": 1, "extension": 1}))
        sha_atts = defaultdict(list)
        sha_meta = {}
        fn_by_id = {}
        for r in rows:
            sha_atts[r["sha256"]].append(r["_id"])
            sha_meta.setdefault(r["sha256"], (r.get("extension"), r.get("filename")))
            fn_by_id[r["_id"]] = r.get("filename")
        shas = list(sha_atts.keys())
        logger.info(f"fraud born-digital sha to re-chunk: {len(shas)} ({WORKERS} workers)")

        all_aids = [a for v in sha_atts.values() for a in v]
        aid_to_sha = {a: sha for sha, aids in sha_atts.items() for a in aids}
        occ_by_sha = defaultdict(list)
        proj = {"_id": 1, "attachment_ids": 1, "date": 1, "date_ym": 1,
                "from": 1, "to": 1, "subject": 1, "folder_path": 1}
        for em in emails.find({"attachment_ids": {"$in": all_aids}}, proj):
            for aid in em.get("attachment_ids") or []:
                sha = aid_to_sha.get(aid)
                if sha:
                    occ_by_sha[sha].append(
                        _build_occurrence(em, attachment_id=aid,
                                          filename=fn_by_id.get(aid)))
        for sha in occ_by_sha:
            occ_by_sha[sha].sort(key=_date_sort_key)

        del_res = chunks.delete_many(
            {"sha256": {"$in": shas}, "source_type": "attachment"})
        logger.info(f"deleted {del_res.deleted_count} stale chunks; re-chunking...")

        flusher = _Flusher(chunks_col=chunks, embedder=embedder,
                           embedding_model=EMBEDDING_MODEL, batch_size=64, dry=False)

        def work(sha):
            occ = occ_by_sha.get(sha) or []
            if not occ:
                return sha, None, "no-occurrences"
            ext = sha_meta[sha][0]
            res = _process_one_sha256(
                sha, occ, extension=ext, attachments_v2=av2,
                chunk_size=CHUNK_SIZE_TOKENS, chunk_overlap=CHUNK_OVERLAP_TOKENS,
                summarizer=summarizer)
            if not res:
                return sha, None, "no-text"
            return sha, res["docs"], None

        done = no_text = no_occ = 0
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futs = {pool.submit(work, sha): sha for sha in shas}
            for f in as_completed(futs):
                sha, docs, err = f.result()
                done += 1
                if err == "no-occurrences":
                    no_occ += 1
                elif err == "no-text":
                    no_text += 1
                elif docs:
                    flusher.add_attachment_group(sha, docs)
                    flusher.flush(force=False)
                if done % 25 == 0:
                    u = summarizer.usage_summary
                    logger.info(f"  [{done}/{len(shas)}] written={flusher.n_chunks_written} "
                                f"no_text={no_text} no_occ={no_occ} "
                                f"ctx_cost=${u['approx_cost_usd']:.2f}")
        flusher.flush(force=True)

        u = summarizer.usage_summary
        logger.info(f"DONE: re-chunked {done} sha -> chunks_written={flusher.n_chunks_written} "
                    f"(no_text={no_text}, no_occ={no_occ}) ctx_cost=${u['approx_cost_usd']:.2f}")
        return 0
    finally:
        mongo.close()


if __name__ == "__main__":
    raise SystemExit(main())
