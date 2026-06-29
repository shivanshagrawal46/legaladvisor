"""Targeted re-chunk of ONLY the zip sha (Attachments.zip / Closing Documents
PDF, now 1.09M chars of GPT-5 text). Reuses the exact build_email_chunks_v2
functions so the chunk docs are byte-identical in shape to the main run,
but skips the slow/hung full-corpus Phase A gather.
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.utils.logger import logger
from scripts.build_email_chunks_v2 import (
    VoyageEmbedder, ContextualSummarizer,
    _process_one_sha256, _build_occurrence, _date_sort_key, _Flusher,
    _ensure_v2_indexes,
    V2_CHUNKS_COLLECTION, V2_ATTACHMENTS_COLLECTION, EMBEDDING_MODEL,
    CHUNK_SIZE_TOKENS, CHUNK_OVERLAP_TOKENS,
)

ZIP_PFX = "33c8d9696d14"


def main() -> int:
    s = Settings.load()
    mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    chunks_v2 = mongo.db[V2_CHUNKS_COLLECTION]
    attachments_v2 = mongo.db[V2_ATTACHMENTS_COLLECTION]
    embedder = VoyageEmbedder(api_key=s.voyage_api_key, model=EMBEDDING_MODEL)
    summarizer = ContextualSummarizer(api_key=s.anthropic_api_key,
                                      model="claude-sonnet-4-6")
    try:
        mongo.ping()
        _ensure_v2_indexes(chunks_v2)

        zrows = list(attachments_v2.find(
            {"sha256": {"$regex": f"^{ZIP_PFX}"}},
            {"_id": 1, "sha256": 1, "filename": 1, "extension": 1},
        ))
        if not zrows:
            logger.error("zip sha not found"); return 1
        sha = zrows[0]["sha256"]
        att_ids = [r["_id"] for r in zrows]
        ext = zrows[0].get("extension")
        fn_by_id = {r["_id"]: r.get("filename") for r in zrows}

        # Reconstruct occurrences exactly like Phase A: every email that
        # references one of these attachment ids.
        occ = []
        proj = {"_id": 1, "attachment_ids": 1, "date": 1, "date_ym": 1,
                "from": 1, "to": 1, "subject": 1, "folder_path": 1}
        for em in mongo.emails.find({"attachment_ids": {"$in": att_ids}}, proj):
            for aid in em.get("attachment_ids") or []:
                if aid in fn_by_id:
                    occ.append(_build_occurrence(em, attachment_id=aid,
                                                 filename=fn_by_id[aid]))
        occ.sort(key=_date_sort_key)
        logger.info(f"zip sha={sha[:16]} att_ids={len(att_ids)} occurrences={len(occ)}")
        if not occ:
            logger.error("no emails reference this zip; cannot build occurrences")
            return 1

        result = _process_one_sha256(
            sha, occ, extension=ext, attachments_v2=attachments_v2,
            chunk_size=CHUNK_SIZE_TOKENS, chunk_overlap=CHUNK_OVERLAP_TOKENS,
            summarizer=summarizer,
        )
        if not result:
            logger.error("_process_one_sha256 returned None (no text?)"); return 1
        docs = result["docs"]
        logger.info(f"built {len(docs)} chunk docs (ctx_calls={result['n_ctx']}); "
                    f"embedding + writing (delete-then-insert)...")

        flusher = _Flusher(chunks_col=chunks_v2, embedder=embedder,
                           embedding_model=EMBEDDING_MODEL, batch_size=64,
                           dry=False)
        flusher.add_attachment_group(sha, docs)
        flusher.flush(force=True)

        n = chunks_v2.count_documents({"sha256": sha, "source_type": "attachment"})
        u = summarizer.usage_summary
        logger.info(f"DONE: zip now has {n} chunks in v2. "
                    f"ctx_cost=${u['approx_cost_usd']:.2f}")
        return 0
    finally:
        mongo.close()


if __name__ == "__main__":
    raise SystemExit(main())
