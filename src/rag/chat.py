"""
Claude Sonnet 4.5 chat layer with structured citations.

Architecture:

  - We treat Claude as a senior legal advisor.
  - For every user question we (a) retrieve top-K chunks via Atlas
    Vector Search + Voyage rerank, and (b) inject them as numbered
    sources into a structured prompt.
  - Claude is instructed to cite sources inline using `[#N]` markers
    referencing the numbered list, and to clearly mark when something is
    from its own legal expertise (not the corpus).
  - We support conversation continuity (multi-turn) by keeping a list of
    {role, content} messages.

The prompt is intentionally explicit about:
  - hallucination guardrails (don't invent facts about the corpus)
  - citation format ([#1], [#2], …)
  - separation of corpus-grounded vs. expertise-grounded statements
  - awareness of OCR fallibility (low-confidence pages are flagged)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple

import anthropic

from src.rag.retriever import RetrievedChunk, Retriever
from src.utils.logger import logger


# Heuristic detection of timeline-style questions.
_TIMELINE_KEYWORDS = re.compile(
    r"\b(timeline|chronolog(?:y|ical)|chrono|sequence of events|over time|"
    r"from\s+\d{4}\s+to\s+\d{4}|between\s+\d{4}\s+and\s+\d{4}|"
    r"summari[sz]e\s+(?:everything|all)|how\s+did\s+\w+\s+evolve|"
    r"what\s+happened\s+(?:between|from|during))\b",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(r"\b(20\d{2})\b")


def detect_timeline_intent(question: str) -> Tuple[bool, Optional[datetime], Optional[datetime]]:
    """
    Returns (is_timeline_query, date_from, date_to).

    If the user asks "summarize from 2021 to 2024" we extract the years and
    pass them as Atlas date filters.
    """
    if not _TIMELINE_KEYWORDS.search(question):
        return False, None, None
    years = [int(y) for y in _YEAR_RE.findall(question)]
    date_from = date_to = None
    if len(years) >= 2:
        ys, ye = sorted([years[0], years[1]])
        date_from = datetime(ys, 1, 1)
        date_to = datetime(ye, 12, 31, 23, 59, 59)
    elif len(years) == 1:
        y = years[0]
        date_from = datetime(y, 1, 1)
        date_to = datetime(y, 12, 31, 23, 59, 59)
    return True, date_from, date_to


SYSTEM_PROMPT = """You are a senior legal advisor reviewing a body of email correspondence and attached documents that constitute evidence in a fraud investigation. Your role is to help the investigator understand the facts, identify suspicious patterns, locate corroborating documents, and reason about legal implications.

## Operating principles

1. **Two sources of knowledge.** You have:
   - **Corpus knowledge** — the numbered SOURCES block provided with each user question. This is the ground truth for what was said, when, and by whom in this case.
   - **Legal expertise** — your general legal, financial, and investigative knowledge. Use this to interpret the corpus, identify relevant doctrines, suggest follow-up questions, and explain implications.

2. **Cite the corpus inline.** When you state any factual claim drawn from the SOURCES, append a citation marker `[#N]` referring to the numbered source. If a claim draws on multiple sources, cite all of them, e.g. `[#1][#3]`. Do not cite legal-expertise statements; those flow naturally and uncited.

3. **Never invent corpus facts.** If the SOURCES do not contain information needed to answer the question, say so plainly ("The provided emails do not show…") and then offer your professional perspective on what *would* be relevant to look for.

4. **Dates are first-class.** Every SOURCE block carries a date in its header. When reasoning, ALWAYS anchor claims to dates. If the same fact appears at different dates with different values (e.g., a verdict in 2023 reversed in 2024), surface BOTH versions and identify which is most recent / operative. Never collapse a time-evolved fact into a single statement without dates.

5. **Skip unreadable text silently.** Some attachments were extracted via OCR and may contain garbled passages. If a piece of text is clearly unreadable or contains obvious recognition errors, simply ignore it and use only the cleanly extracted text. DO NOT add notes like "OCR impaired", "OCR error", "garbled", or similar caveats in your answer. If you cannot read a figure or fact cleanly, just leave it out entirely — never call attention to the imperfection.

6. **Be direct and structured.** Investigators are time-pressed. Lead with the bottom line, follow with the evidence chain, then add nuance. Use short paragraphs and bullet lists when listing facts.

7. **Flag suspicious patterns proactively.** When you notice red flags (round-number transfers, unusual urgency, off-domain emails, contradictions across emails, signature mismatches, gaps in timeline), call them out even if the user didn't ask.

8. **Maintain attorney-client style discretion.** Treat the corpus as confidential. Don't speculate about parties not in the corpus."""


TIMELINE_INSTRUCTION = """\
The user has asked for a chronological / timeline-style summary. The SOURCES below have been pre-sorted by date ascending. Produce a CHRONOLOGICAL summary:

  - Group events by year (## 2021, ## 2022, …)
  - Within each year, list significant events as bullets, each starting with the date `**YYYY-MM-DD** —` followed by a one-sentence factual summary, followed by the citation `[#N]`
  - At the end, add a short "Key inflection points" subsection calling out events where positions changed, decisions were reversed, or major payments/transfers happened
  - If the corpus has gaps (long silent periods, missing months), call them out explicitly
"""


def _format_chunk_for_prompt(idx: int, chunk: RetrievedChunk) -> str:
    """Render a single retrieved chunk as a numbered SOURCE block."""
    head_parts: List[str] = [f"#{idx}"]
    if chunk.source_type == "email_body":
        head_parts.append("Email")
    elif chunk.source_type == "attachment":
        head_parts.append(f"Attachment: {chunk.filename or 'unknown'}")
        if chunk.page_start is not None:
            if chunk.page_end and chunk.page_end != chunk.page_start:
                head_parts.append(f"pp. {chunk.page_start}-{chunk.page_end}")
            else:
                head_parts.append(f"p. {chunk.page_start}")
    if chunk.date is not None:
        try:
            head_parts.append(chunk.date.strftime("%Y-%m-%d %H:%M"))
        except AttributeError:
            head_parts.append(str(chunk.date))
    if chunk.from_email:
        head_parts.append(f"from {chunk.from_email}")
    if chunk.to_emails:
        head_parts.append(f"to {', '.join(chunk.to_emails[:3])}")
    if chunk.subject:
        head_parts.append(f"subject: {chunk.subject}")

    header = " | ".join(head_parts)
    body = chunk.body or chunk.text
    return f"[{header}]\n{body}"


def _build_user_message(
    question: str,
    chunks: List[RetrievedChunk],
    *,
    timeline: bool = False,
) -> str:
    if not chunks:
        return (
            f"QUESTION:\n{question}\n\n"
            "(No corpus sources were retrieved for this question. "
            "Answer from your legal expertise alone, and explicitly note the "
            "absence of supporting corpus evidence.)"
        )

    sources_block = "\n\n".join(
        _format_chunk_for_prompt(i + 1, c) for i, c in enumerate(chunks)
    )
    instr = (
        "SOURCES (sorted by date ascending; cite as [#N]):"
        if timeline else
        "SOURCES (numbered, cite as [#N]):"
    )
    body = f"{instr}\n\n{sources_block}\n\n---\n\nQUESTION:\n{question}"
    if timeline:
        body = f"{TIMELINE_INSTRUCTION}\n\n{body}"
    return body


@dataclass
class Turn:
    question: str
    answer: str
    chunks: List[RetrievedChunk] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class LegalAdvisorChat:
    """Stateful multi-turn conversation manager over the email corpus."""

    def __init__(
        self,
        anthropic_api_key: str,
        retriever: Retriever,
        *,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 4096,
    ) -> None:
        if not anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is missing. Add it to .env before chatting."
            )
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.retriever = retriever
        self.model = model
        self.max_tokens = max_tokens
        self.history: List[Turn] = []

    def ask(
        self,
        question: str,
        *,
        atlas_filter: Optional[dict] = None,
        timeline: Optional[bool] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        max_chunks_timeline: int = 50,
    ) -> Turn:
        # Auto-detect timeline intent if not explicitly set.
        auto_timeline, auto_from, auto_to = detect_timeline_intent(question)
        if timeline is None:
            timeline = auto_timeline
        if date_from is None:
            date_from = auto_from
        if date_to is None:
            date_to = auto_to

        if timeline:
            logger.info(
                f"Timeline mode  (date_from={date_from}, date_to={date_to}, "
                f"max_chunks={max_chunks_timeline})"
            )
            chunks = self.retriever.retrieve_timeline(
                question,
                date_from=date_from,
                date_to=date_to,
                max_chunks=max_chunks_timeline,
                atlas_filter=atlas_filter,
            )
        else:
            chunks = self.retriever.retrieve(question, atlas_filter=atlas_filter)
        logger.info(f"Retrieved {len(chunks)} chunks for question")

        prior_messages = []
        for turn in self.history:
            prior_messages.append({"role": "user", "content": turn.question})
            prior_messages.append({"role": "assistant", "content": turn.answer})

        user_msg = _build_user_message(question, chunks, timeline=timeline)
        prior_messages.append({"role": "user", "content": user_msg})

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=SYSTEM_PROMPT,
            messages=prior_messages,
        )

        answer_parts: List[str] = []
        for block in response.content:
            if getattr(block, "type", None) == "text":
                answer_parts.append(block.text)
        answer = "\n".join(answer_parts).strip()

        turn = Turn(question=question, answer=answer, chunks=chunks)
        self.history.append(turn)
        return turn

    def reset(self) -> None:
        self.history.clear()
