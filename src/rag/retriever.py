"""
Hybrid retriever:

  1. Embed the query with Voyage.
  2. Run Atlas $vectorSearch over `email_chunks.embedding` to fetch
     `RETRIEVAL_TOP_K` candidates.
  3. (Optional) merge in a literal-text $text search to catch keyword
     matches that embeddings miss (dollar amounts, file names).
  4. Rerank with Voyage rerank-2.5 down to `RERANK_TOP_K`.
  5. Return enriched candidates ready for the prompt.

Atlas filter expressions can be passed in to narrow by date / sender /
folder before vector search runs (this is much faster than retrieving
1k docs and filtering in Python).

Timeline mode: `retrieve_timeline()` returns chunks SORTED BY DATE
(ascending) instead of by similarity, and pulls a wider net so a
single chronological summary covers the whole period. This is the
right mode when the user asks for a chronological summary or any
"what happened from year X to year Y" question.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from src.db.mongo import MongoClientWrapper
from src.rag.embedder import VoyageEmbedder
from src.rag.reranker import VoyageReranker
from src.utils.logger import logger


def build_date_filter(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """Helper to build an Atlas $vectorSearch date filter."""
    if not date_from and not date_to:
        return None
    expr: Dict[str, Any] = {}
    if date_from:
        expr["$gte"] = date_from
    if date_to:
        expr["$lte"] = date_to
    return {"date": expr}


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    body: str
    source_type: str            # "email_body" | "attachment"
    email_id: str
    attachment_id: Optional[str]
    filename: Optional[str]
    page_start: Optional[int]
    page_end: Optional[int]
    date: Any
    from_email: Optional[str]
    to_emails: List[str]
    subject: Optional[str]
    folder_path: Optional[str]
    vector_score: Optional[float]
    rerank_score: Optional[float]


class Retriever:
    def __init__(
        self,
        mongo: MongoClientWrapper,
        embedder: VoyageEmbedder,
        reranker: VoyageReranker,
        *,
        vector_index_name: str,
        retrieval_top_k: int = 50,
        rerank_top_k: int = 8,
    ) -> None:
        self.mongo = mongo
        self.embedder = embedder
        self.reranker = reranker
        self.vector_index_name = vector_index_name
        self.retrieval_top_k = retrieval_top_k
        self.rerank_top_k = rerank_top_k

    # ----- vector search -----

    def _vector_search(
        self,
        query_vec: List[float],
        atlas_filter: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        stage_vector: Dict[str, Any] = {
            "$vectorSearch": {
                "index": self.vector_index_name,
                "path": "embedding",
                "queryVector": query_vec,
                "numCandidates": max(150, self.retrieval_top_k * 5),
                "limit": self.retrieval_top_k,
            }
        }
        if atlas_filter:
            stage_vector["$vectorSearch"]["filter"] = atlas_filter

        pipeline = [
            stage_vector,
            {
                "$project": {
                    "_id": 1,
                    "text": 1,
                    "body": 1,
                    "source_type": 1,
                    "email_id": 1,
                    "attachment_id": 1,
                    "filename": 1,
                    "page_start": 1,
                    "page_end": 1,
                    "date": 1,
                    "from_email": 1,
                    "to_emails": 1,
                    "subject": 1,
                    "folder_path": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]
        return list(self.mongo.chunks.aggregate(pipeline))

    # ----- public API -----

    def retrieve(
        self,
        query: str,
        atlas_filter: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedChunk]:
        """End-to-end: embed → vector search → rerank → return chunks."""
        if not query.strip():
            return []

        logger.debug(f"Embedding query ({len(query)} chars)")
        qvec = self.embedder.embed_query(query)

        logger.debug(f"Running $vectorSearch (limit={self.retrieval_top_k})")
        candidates = self._vector_search(qvec, atlas_filter=atlas_filter)
        if not candidates:
            return []

        logger.debug(f"Reranking {len(candidates)} candidates → top {self.rerank_top_k}")
        docs = [c.get("text") or c.get("body") or "" for c in candidates]
        rerank_results = self.reranker.rerank(query, docs, top_k=self.rerank_top_k)

        out: List[RetrievedChunk] = []
        for r in rerank_results:
            c = candidates[r["index"]]
            out.append(_to_chunk(c, rerank_score=r["score"]))
        return out

    # ----- timeline mode -----

    def retrieve_timeline(
        self,
        query: str,
        *,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        max_chunks: int = 50,
        atlas_filter: Optional[Dict[str, Any]] = None,
    ) -> List[RetrievedChunk]:
        """
        Timeline-mode retrieval.

        Returns chunks **sorted by date ASC**, not by similarity. We pull a
        wider net (`max_chunks`, default 50) so Claude sees enough
        spread-across-time evidence to build a full chronological summary.

        Use this for queries like:
          - "Summarize the events from 2021 to 2026"
          - "What happened to the Mango Tree settlement over time?"
          - "Build me a timeline of all communications about Fort Hill"
        """
        if not query.strip():
            return []

        # Combine user-supplied filter with date-range filter.
        date_f = build_date_filter(date_from, date_to)
        merged = {**(atlas_filter or {}), **(date_f or {})}

        logger.debug(f"Timeline retrieve: filter={merged}, top={max_chunks}")
        qvec = self.embedder.embed_query(query)

        # Increase pull size for timeline mode.
        old_top_k = self.retrieval_top_k
        self.retrieval_top_k = max_chunks
        try:
            candidates = self._vector_search(qvec, atlas_filter=merged or None)
        finally:
            self.retrieval_top_k = old_top_k

        if not candidates:
            return []

        # Sort by date ASC (None dates last).
        def sort_key(c: Dict[str, Any]):
            d = c.get("date")
            return (d is None, d)
        candidates.sort(key=sort_key)

        # Optional rerank for relevance score, but DO NOT use rerank order.
        # (Rerank can demote dated chunks that are essential for timeline.)
        return [_to_chunk(c, rerank_score=None) for c in candidates]


def _to_chunk(c: Dict[str, Any], *, rerank_score: Optional[float]) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=str(c["_id"]),
        text=c.get("text") or "",
        body=c.get("body") or "",
        source_type=c.get("source_type") or "",
        email_id=str(c.get("email_id")) if c.get("email_id") else "",
        attachment_id=str(c.get("attachment_id")) if c.get("attachment_id") else None,
        filename=c.get("filename"),
        page_start=c.get("page_start"),
        page_end=c.get("page_end"),
        date=c.get("date"),
        from_email=c.get("from_email"),
        to_emails=c.get("to_emails") or [],
        subject=c.get("subject"),
        folder_path=c.get("folder_path"),
        vector_score=c.get("score"),
        rerank_score=rerank_score,
    )
