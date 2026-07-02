"""The 8 recovered emails are forwarded/threaded fraud correspondence whose
evidence lives in the quoted portion. Re-derive body_text WITHOUT quote
stripping (preserve full thread) and re-chunk. body_html is already the
corrected real HTML from the recovery step."""
from __future__ import annotations
import sys
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bson import ObjectId

from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.cleaner import clean_email_body, html_to_text
from src.utils.logger import logger
from scripts.build_email_chunks_v2 import (
    VoyageEmbedder, ContextualSummarizer, _Flusher, _process_one_body,
    EMBEDDING_MODEL, CHUNK_SIZE_TOKENS, CHUNK_OVERLAP_TOKENS,
)

EIDS = ["6a082dc49a4a41f30e351ead", "6a082db39a4a41f30e351e4a",
        "6a0830d39a4a41f30e352dbe", "6a0830d39a4a41f30e352dbf",
        "6a0830d39a4a41f30e352dc1", "6a0837a254c72cee2b866b4e",
        "6a0837c654c72cee2b866c43", "6a083cd654c72cee2b8686ae"]


def main() -> int:
    s = Settings.load()
    mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    emails = mongo.db["emails"]
    chunks = mongo.db["email_chunks_v2"]
    embedder = VoyageEmbedder(api_key=s.voyage_api_key, model=EMBEDDING_MODEL)
    summarizer = ContextualSummarizer(api_key=s.anthropic_api_key,
                                      model="claude-sonnet-4-6")
    now = datetime.now(timezone.utc)
    try:
        mongo.ping()
        flusher = _Flusher(chunks_col=chunks, embedder=embedder,
                           embedding_model=EMBEDDING_MODEL, batch_size=64, dry=False)
        written = 0
        for e in EIDS:
            eid = ObjectId(e)
            em = emails.find_one({"_id": eid}, {"body_html": 1})
            full = clean_email_body(html_to_text(em.get("body_html") or ""),
                                    strip_quotes=False)
            emails.update_one({"_id": eid}, {"$set": {
                "body_text": full,
                "body_quotes_preserved": True,
                "body_recovered_at": now}})
            res = _process_one_body(
                eid, emails_col=emails, chunk_size=CHUNK_SIZE_TOKENS,
                chunk_overlap=CHUNK_OVERLAP_TOKENS, summarizer=summarizer)
            if not res or not res.get("docs"):
                chunks.delete_many({"email_id": eid, "source_type": "email_body"})
                logger.warning(f"  {e}: no chunks (body empty)")
                continue
            flusher.add_body_group(eid, res["docs"])
            flusher.flush(force=True)
            written += len(res["docs"])
            logger.info(f"  {e}: body={len(full)} -> {len(res['docs'])} chunks")
        u = summarizer.usage_summary
        logger.info(f"DONE: {len(EIDS)} emails, {written} chunks; ctx_cost=${u['approx_cost_usd']:.2f}")
        return 0
    finally:
        mongo.close()


if __name__ == "__main__":
    raise SystemExit(main())
