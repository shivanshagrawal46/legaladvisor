"""Backfill contextual summaries for the chunks that were left with empty
context (transient summarizer failure during the credit-exhaustion incident).
Regenerates context per chunk against the parent doc, recomposes the embed
text ([Context] + body), and re-embeds with Voyage. Scoped ONLY to chunks that
currently lack a context."""
from __future__ import annotations
import sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.utils.logger import logger
from scripts.build_email_chunks_v2 import (
    VoyageEmbedder, ContextualSummarizer, _compose_embed_text, EMBEDDING_MODEL,
)

NOCTX = {"$or": [{"context": {"$exists": False}}, {"context": None}, {"context": ""}]}


def _email_body(em: dict) -> str:
    for k in ("body_text", "clean_body", "body", "text", "plain_body", "content"):
        v = em.get(k)
        if isinstance(v, str) and v.strip():
            return v
    return ""


def main() -> int:
    s = Settings.load()
    mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    ch = mongo.db["email_chunks_v2"]
    emails = mongo.db["emails"]
    av2 = mongo.db["attachments_v2"]
    embedder = VoyageEmbedder(api_key=s.voyage_api_key, model=EMBEDDING_MODEL)
    summarizer = ContextualSummarizer(api_key=s.anthropic_api_key,
                                      model="claude-sonnet-4-6")
    try:
        rows = list(ch.find(NOCTX, {"_id": 1, "email_id": 1, "sha256": 1,
                                    "source_type": 1, "body": 1, "text": 1,
                                    "chunk_index": 1}))
        logger.info(f"chunks missing context: {len(rows)}")

        # group by parent doc (email_id for bodies, sha256 for attachments)
        by_email = defaultdict(list)
        by_sha = defaultdict(list)
        for r in rows:
            if r.get("source_type") == "attachment":
                by_sha[r["sha256"]].append(r)
            else:
                by_email[r["email_id"]].append(r)

        fixed = 0

        def process(doc_text, group):
            nonlocal fixed
            group.sort(key=lambda r: r.get("chunk_index") or 0)
            bodies = [(r.get("body") or r.get("text") or "") for r in group]
            ctxs = summarizer.summarize_doc_chunks(doc_text=doc_text,
                                                   chunk_texts=bodies)
            embed_texts, valid = [], []
            for r, body, ctx in zip(group, bodies, ctxs):
                if not ctx:
                    logger.warning(f"   still empty ctx for {r['_id']}")
                    continue
                embed_texts.append(_compose_embed_text(body, ctx))
                valid.append((r, body, ctx))
            if not valid:
                return
            vecs = embedder.embed_documents(embed_texts)
            for (r, body, ctx), vec in zip(valid, vecs):
                ch.update_one({"_id": r["_id"]}, {"$set": {
                    "context": ctx,
                    "text": _compose_embed_text(body, ctx),
                    "embedding": vec,
                    "embedding_model": EMBEDDING_MODEL,
                }})
                fixed += 1

        for eid, group in by_email.items():
            em = emails.find_one({"_id": eid}) or {}
            doc_text = _email_body(em) or "\n\n".join(
                (r.get("body") or r.get("text") or "") for r in group)
            logger.info(f"email {eid}: {len(group)} chunks, doc_text={len(doc_text)} chars")
            process(doc_text, group)

        for sha, group in by_sha.items():
            att = av2.find_one({"sha256": sha}) or {}
            doc_text = (att.get("extracted_text") or "") or "\n\n".join(
                (r.get("body") or r.get("text") or "") for r in group)
            logger.info(f"attachment {sha[:12]}: {len(group)} chunks, doc_text={len(doc_text)} chars")
            process(doc_text, group)

        u = summarizer.usage_summary
        logger.info(f"DONE: fixed {fixed}/{len(rows)} chunks; ctx_cost=${u['approx_cost_usd']:.2f}")
        remaining = ch.count_documents(NOCTX)
        logger.info(f"chunks still missing context: {remaining}")
        return 0
    finally:
        mongo.close()


if __name__ == "__main__":
    raise SystemExit(main())
