"""PHASE 5 - STAGE 2: chunk + contextual-summary + embed every doc_p5_* document
into the LIVE vector corpus `email_chunks_v2`.

Mirrors scripts/chunk_embed_documents.py exactly (structural 1000/200 chunking,
Claude Sonnet 4.6 contextual summary, voyage-4-large 1024-dim embeddings), but
scoped to the Phase-5 discovery documents. Resumable / crash-safe: a doc is
all-or-nothing (delete old chunks -> insert new -> stamp chunked_at). Re-run the
same command to continue.

Usage:
  python _phase5_chunk_embed.py            # all pending doc_p5_*
  python _phase5_chunk_embed.py --limit 5  # smoke test
  python _phase5_chunk_embed.py --reembed  # redo all
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from typing import Any, Dict

import config.settings  # noqa: F401
from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.rag.chunker import _chunk_text
from src.rag.tokens import count_tokens
from src.rag.embedder import VoyageEmbedder
from src.rag.v2.contextual_summary import ContextualSummarizer
from src.utils.logger import logger
from pymongo import ASCENDING

CHUNKS = "email_chunks_v2"


def _fmt(d) -> str:
    try:
        return d.strftime("%Y-%m-%d")
    except Exception:  # noqa: BLE001
        return ""


def header_for(doc: Dict[str, Any]) -> str:
    cat = (doc.get("doc_category") or doc.get("source_type") or "document").replace("_", " ").title()
    matter = (doc.get("matter_id") or "").replace("_", " ")
    bits = [cat, matter]
    if doc.get("primary_property_id"):
        bits.append(f"prop {doc['primary_property_id']}")
    if doc.get("bates_start"):
        bits.append(f"Bates {doc['bates_start']}-{doc.get('bates_end')}")
    return "[" + " | ".join(b for b in bits if b) + "]"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--reembed", action="store_true")
    ap.add_argument("--doc-id", default=None)
    ap.add_argument("--shard", default=None, help="k/N disjoint worker shard, e.g. 0/3")
    args = ap.parse_args()
    shard_k = shard_n = None
    if args.shard:
        shard_k, shard_n = (int(x) for x in args.shard.split("/"))
    s = Settings.load()
    now = datetime.now(timezone.utc)
    size, overlap = s.chunk_size_tokens, s.chunk_overlap_tokens

    summarizer = ContextualSummarizer(s.anthropic_api_key, model="claude-sonnet-4-6")
    embedder = VoyageEmbedder(s.voyage_api_key, model="voyage-4-large")
    m = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
    docs, chunks = m.db["documents"], m.db[CHUNKS]
    for keys, nm in [([("document_id", ASCENDING)], "ix_document_id"),
                     ([("entity_refs.properties", ASCENDING)], "ix_entity_props"),
                     ([("primary_property_id", ASCENDING)], "ix_primary_prop")]:
        try:
            chunks.create_index(keys, name=nm)
        except Exception:  # noqa: BLE001
            pass

    q: Dict[str, Any] = {"_id": {"$regex": "^doc_p5_"}}
    if args.doc_id:
        q = {"_id": args.doc_id}
        chunks.delete_many({"document_id": args.doc_id})
    elif not args.reembed:
        q["chunked_at"] = {"$exists": False}
    pending = list(docs.find(q, {"_id": 1}).sort("_id", ASCENDING))
    if shard_n:
        pending = [r for r in pending
                   if int(str(r["_id"]).split("_")[-1], 16) % shard_n == shard_k]
    if args.limit:
        pending = pending[: args.limit]
    total = docs.count_documents({"_id": {"$regex": "^doc_p5_"}})
    logger.info(f"{len(pending)} phase5 docs to chunk/embed "
                f"(shard={args.shard or 'all'}) | chunk {size}/{overlap}")

    done = total_chunks = 0
    for n, ref in enumerate(pending, 1):
        d = docs.find_one({"_id": ref["_id"]})
        text = (d.get("extracted_text") or "").strip()
        if not text:
            docs.update_one({"_id": d["_id"]}, {"$set": {"chunked_at": now, "chunk_count": 0,
                            "chunk_skip_reason": "empty_text"}})
            continue
        header = header_for(d)
        body_budget = max(128, size - count_tokens(header) - 4)
        bodies = _chunk_text(text, max_tokens=body_budget, overlap_tokens=overlap)
        full_texts = [f"{header}\n\n{b}" for b in bodies]
        try:
            summaries = summarizer.summarize_doc_chunks(text, bodies)
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"  [{n}/{len(pending)}] {d['_id']}: summary failed ({str(exc)[:80]})")
            summaries = [""] * len(bodies)
        embed_texts = [(f"[Context] {summaries[i]}\n\n{full_texts[i]}" if summaries[i] else full_texts[i])
                       for i in range(len(bodies))]
        vectors = embedder.embed_documents(embed_texts)
        prop_ids = d.get("property_ids") or []
        chunk_docs = []
        for i, body in enumerate(bodies):
            chunk_docs.append({
                "_id": f"{d['_id']}::{i}", "source_type": d.get("source_type"),
                "document_id": d["_id"], "sha256": (d.get("custody") or {}).get("sha256"),
                "chunk_index": i, "total_chunks": len(bodies),
                "text": embed_texts[i], "body": body, "context": summaries[i],
                "n_tokens": count_tokens(embed_texts[i]),
                "embedding": vectors[i], "embedding_model": "voyage-4-large",
                "matter_id": d.get("matter_id"), "corpus": d.get("corpus"),
                "privilege_status": d.get("privilege_status"),
                "doc_source_type": d.get("source_type"),
                "doc_category": d.get("doc_category"),
                "doc_authority_score": d.get("authority_score"),
                "bates_start": d.get("bates_start"), "bates_end": d.get("bates_end"),
                "property_ids": prop_ids, "primary_property_id": (prop_ids[0] if prop_ids else None),
                "case_ids": d.get("case_ids") or [],
                "entity_refs": {"properties": prop_ids, "cases": d.get("case_ids") or []},
                "doc_date": d.get("document_date") or d.get("as_of_date"),
                "created_at": now,
            })
        chunks.delete_many({"document_id": d["_id"]})
        if chunk_docs:
            chunks.insert_many(chunk_docs, ordered=False)
        docs.update_one({"_id": d["_id"]}, {"$set": {"chunked_at": now, "chunk_count": len(chunk_docs)}})
        done += 1
        total_chunks += len(chunk_docs)
        if n % 50 == 0 or n == len(pending):
            u = summarizer.total_usage
            logger.info(f"  [{n}/{len(pending)}] {d['_id'][:30]} -> {len(chunk_docs)} chunks "
                        f"| run_chunks={total_chunks} cache_read={getattr(u,'cache_read_tokens',0)}")

    logger.info("================ PHASE5 CHUNK+EMBED DONE (this run) ================")
    logger.info(f"docs processed={done}  chunks written={total_chunks}")
    logger.info(f"phase5 docs chunked={docs.count_documents({'_id':{'$regex':'^doc_p5_'},'chunked_at':{'$exists':True}})}/{total}")
    m.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
