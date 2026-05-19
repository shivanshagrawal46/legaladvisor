"""
Voyage AI reranker (rerank-2.5).

Takes the top-K candidates from vector search and reorders them by
*query-specific* relevance. This single step is the highest-leverage
quality improvement in modern RAG: it routinely doubles top-3 precision.
"""
from __future__ import annotations

from typing import List, Sequence

import voyageai
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class VoyageReranker:
    def __init__(self, api_key: str, model: str = "rerank-2.5") -> None:
        if not api_key:
            raise RuntimeError(
                "VOYAGE_API_KEY is missing. Add it to .env before running rerank."
            )
        self.client = voyageai.Client(api_key=api_key)
        self.model = model

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        retry=retry_if_exception_type(Exception),
        reraise=True,
    )
    def rerank(
        self,
        query: str,
        documents: Sequence[str],
        top_k: int = 8,
    ) -> List[dict]:
        """
        Returns a list of {"index": int, "score": float} sorted by score
        descending, length min(top_k, len(documents)).
        """
        if not documents:
            return []
        result = self.client.rerank(
            query=query,
            documents=list(documents),
            model=self.model,
            top_k=min(top_k, len(documents)),
            truncation=True,
        )
        return [
            {"index": r.index, "score": float(r.relevance_score)}
            for r in result.results
        ]
