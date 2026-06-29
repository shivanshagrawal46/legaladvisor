"""Re-chunk every attachment sha that was just re-OCR'd via frontier vision
(extracted_via='reocr_vision_v1'). Their old chunks were built from RapidOCR
text and are now stale. Parallel across sha (each doc summarised sequentially
internally for cache warmth), reusing the exact build functions.
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
        # sha that were just re-OCR'd via frontier vision.
        rows = list(av2.find({"extracted_via": "reocr_borndigital_v1"},
                             {"_id": 1, "sha256": 1, "filename": 1, "extension": 1}))
        # group sha -> att_ids + meta
        sha_atts = defaultdict(list)
        sha_meta = {}
        for r in rows:
            sha_atts[r["sha256"]].append(r["_id"])
            sha_meta.setdefault(r["sha256"], (r.get("extension"), r.get("filename")))
        shas = list(sha_atts.keys())
        logger.info(f"re-OCR'd sha to re-chunk: {len(shas)}")

        # Build occurrences for all involved att_ids in one pass.
        all_aids = [a for v in sha_atts.values() for a in v]
        fn_by_id = {}
        for r in rows:
            fn_by_id[r["_id"]] = r.get("filename")
        occ_by_sha = defaultdict(list)
        aid_to_sha = {}
        for sha, aids in sha_atts.items():
            for a in aids:
                aid_to_sha[a] = sha
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

        # Delete stale chunks for all these sha first.
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

        done = 0
        no_text = 0
        no_occ = 0
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
                                f"no_text={no_text} no_occ={no_occ} ctx_cost=${u['approx_cost_usd']:.2f}")
        flusher.flush(force=True)

        u = summarizer.usage_summary
        logger.info(f"DONE: re-chunked {done} sha -> chunks_written={flusher.n_chunks_written} "
                    f"(no_text={no_text}, no_occ={no_occ}) ctx_cost=${u['approx_cost_usd']:.2f}")
        return 0
    finally:
        mongo.close()


if __name__ == "__main__":
    raise SystemExit(main())
