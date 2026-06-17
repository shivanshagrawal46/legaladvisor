"""Sprint 7 · 7.1 — LLM-as-reranker (Opus 4.8 final relevance pass).

After Voyage rerank-2.5 orders the candidates, this re-scores the top N (default
50) by having Opus *read* each passage against the question — catching legal
relevance the embedding reranker misses (operative vs prior instrument, the
right party/date). Reorders; never drops a passage (falls back to the incoming
order on any error so the retrieval path can't break).
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Sequence

from src.utils.logger import logger

_RUBRIC = (
    "You are ranking evidence passages for a legal fraud-investigation query. "
    "Score each passage 0-10 for how directly it helps ANSWER THE QUERY "
    "(10 = directly answers / operative record; 5 = related context; "
    "0 = off-topic). Prefer operative/recorded instruments and the correct "
    "party/property/date over similar-but-wrong ones. Return ONLY the tool call."
)

_TOOL = {
    "name": "rank_passages",
    "description": "Return a relevance score (0-10) for every passage index.",
    "input_schema": {
        "type": "object",
        "properties": {
            "scores": {"type": "array", "items": {"type": "object", "properties": {
                "index": {"type": "integer"}, "score": {"type": "number"}},
                "required": ["index", "score"]}}},
        "required": ["scores"],
    },
}


class LLMReranker:
    def __init__(self, client, model: str = "claude-opus-4-8", *,
                 top_n: int = 50, snippet_chars: int = 480, max_tokens: int = 4000):
        self.client = client
        self.model = model
        self.top_n = top_n
        self.snippet_chars = snippet_chars
        self.max_tokens = max_tokens

    def rerank(self, query: str, docs: Sequence[Dict[str, Any]]) -> List[int]:
        """Return a NEW ordering (list of original indices, best-first) for docs.
        Only the top `top_n` are LLM-scored; the rest keep their order behind."""
        n = min(self.top_n, len(docs))
        if n <= 1:
            return list(range(len(docs)))
        head = docs[:n]
        passages = []
        for i, d in enumerate(head):
            body = (d.get("text") or d.get("body") or "")
            body = re.sub(r"\s+", " ", body)[: self.snippet_chars]
            passages.append(f"[{i}] {body}")
        user = f"QUERY: {query}\n\nPASSAGES:\n" + "\n".join(passages)
        try:
            resp = self.client.messages.create(
                model=self.model, max_tokens=self.max_tokens, system=_RUBRIC,
                tools=[_TOOL], tool_choice={"type": "tool", "name": "rank_passages"},
                messages=[{"role": "user", "content": user}])
            scores: Dict[int, float] = {}
            for block in resp.content:
                if getattr(block, "type", None) == "tool_use":
                    for it in (block.input or {}).get("scores", []):
                        scores[int(it["index"])] = float(it["score"])
            if not scores:
                raise ValueError("no scores returned")
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"LLM reranker fell back to base order: {str(exc)[:100]}")
            return list(range(len(docs)))
        # order head by LLM score desc (stable for ties), then append the tail
        head_order = sorted(range(n), key=lambda i: scores.get(i, 0.0), reverse=True)
        return head_order + list(range(n, len(docs)))
