"""Targeted re-chunk of the 27 fraud pdf_mixed sha that were just force-visioned
(_fraud_mixed_done_sha.txt). Reuses the exact build_email_chunks_v2 functions so
chunk docs are byte-identical in shape to the main run, deleting old chunks and
re-inserting with fresh contextual summaries + embeddings from the new OCR text.
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

SHA_FILE = "_fraud_mixed_done_sha.txt"


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

        shas = [ln.strip() for ln in Path(SHA_FILE).read_text(
            encoding="utf-8").splitlines() if ln.strip()]
        logger.info(f"re-chunking {len(shas)} fraud pdf_mixed sha")

        proj = {"_id": 1, "attachment_ids": 1, "date": 1, "date_ym": 1,
                "from": 1, "to": 1, "subject": 1, "folder_path": 1}
        total_chunks = 0
        done = 0
        for i, sha in enumerate(shas, 1):
            rows = list(attachments_v2.find(
                {"sha256": sha},
                {"_id": 1, "sha256": 1, "filename": 1, "extension": 1}))
            if not rows:
                logger.warning(f"  [{i}/{len(shas)}] sha {sha[:12]} not in v2; skip")
                continue
            att_ids = [r["_id"] for r in rows]
            ext = rows[0].get("extension")
            fn_by_id = {r["_id"]: r.get("filename") for r in rows}

            occ = []
            for em in mongo.emails.find({"attachment_ids": {"$in": att_ids}}, proj):
                for aid in em.get("attachment_ids") or []:
                    if aid in fn_by_id:
                        occ.append(_build_occurrence(em, attachment_id=aid,
                                                     filename=fn_by_id[aid]))
            occ.sort(key=_date_sort_key)
            if not occ:
                logger.warning(f"  [{i}/{len(shas)}] sha {sha[:12]} no emails ref; skip")
                continue

            result = _process_one_sha256(
                sha, occ, extension=ext, attachments_v2=attachments_v2,
                chunk_size=CHUNK_SIZE_TOKENS, chunk_overlap=CHUNK_OVERLAP_TOKENS,
                summarizer=summarizer)
            if not result:
                logger.warning(f"  [{i}/{len(shas)}] sha {sha[:12]} no text; skip")
                continue
            docs = result["docs"]
            flusher = _Flusher(chunks_col=chunks_v2, embedder=embedder,
                               embedding_model=EMBEDDING_MODEL, batch_size=64,
                               dry=False)
            flusher.add_attachment_group(sha, docs)
            flusher.flush(force=True)
            n = chunks_v2.count_documents({"sha256": sha, "source_type": "attachment"})
            total_chunks += n
            done += 1
            logger.info(f"  [{i}/{len(shas)}] sha {sha[:12]} -> {n} chunks "
                        f"(occ={len(occ)}, ctx={result['n_ctx']})")

        u = summarizer.usage_summary
        logger.info(f"\nDONE: re-chunked {done}/{len(shas)} sha -> "
                    f"{total_chunks} attachment chunks. ctx_cost=${u['approx_cost_usd']:.2f}")
        return 0
    finally:
        mongo.close()


if __name__ == "__main__":
    raise SystemExit(main())
