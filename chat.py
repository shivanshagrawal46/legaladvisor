"""
Interactive Claude legal-advisor chat over the email corpus.

Usage (single question):
    python chat.py "Summarise every wire-transfer instruction Boris sent in 2024"

Usage (interactive REPL):
    python chat.py
    >>> What did Phil Campisi escalate about Fort Hill in March 2024?
    >>> /reset            (start a new conversation)
    >>> /sources          (show full citation details from the last answer)
    >>> /filter date_ym=2024-03    (constrain retrieval; '/filter clear' to remove)
    >>> /quit

Each answer prints inline citations like [#1] and a numbered list of
sources at the end. Sources show the email date, sender, and (for
attachments) the page span.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.rag.chat import LegalAdvisorChat, Turn
from src.rag.embedder import VoyageEmbedder
from src.rag.reranker import VoyageReranker
from src.rag.retriever import RetrievedChunk, Retriever
from src.utils.logger import configure_logger


# ----- pretty-printing -----

def _short_source(idx: int, c: RetrievedChunk) -> str:
    parts = [f"[#{idx}]"]
    if c.source_type == "email_body":
        parts.append("Email")
    else:
        parts.append(f"Attachment: {c.filename or 'unknown'}")
        if c.page_start is not None:
            if c.page_end and c.page_end != c.page_start:
                parts.append(f"pp.{c.page_start}-{c.page_end}")
            else:
                parts.append(f"p.{c.page_start}")

    if c.date is not None:
        try:
            parts.append(c.date.strftime("%Y-%m-%d"))
        except AttributeError:
            parts.append(str(c.date)[:10])

    if c.from_email:
        parts.append(f"from {c.from_email}")
    if c.subject:
        s = c.subject
        if len(s) > 60:
            s = s[:57] + "…"
        parts.append(f'"{s}"')

    rerank = f"  (relevance={c.rerank_score:.3f})" if c.rerank_score is not None else ""
    return " | ".join(parts) + rerank


def _print_turn(turn: Turn, full_sources: bool = False) -> None:
    print()
    print(turn.answer)
    print()
    if turn.chunks:
        print("─" * 72)
        print(f"Sources ({len(turn.chunks)}):")
        for i, c in enumerate(turn.chunks, start=1):
            print(f"  {_short_source(i, c)}")
            if full_sources:
                preview = (c.body or c.text)[:300].replace("\n", " ")
                print(f"      {preview}{'…' if len(c.body or c.text) > 300 else ''}")
        print()


# ----- filter parsing -----

def _parse_filter_spec(spec: str) -> Optional[dict]:
    """
    Tiny mini-DSL for retrieval filters:
      date_ym=2024-03
      from_email=boris@mblawfirm.com
      source_type=attachment
      date_ym=2024-03,from_email=boris@mblawfirm.com
    """
    spec = spec.strip()
    if not spec or spec.lower() == "clear":
        return None
    out: dict = {}
    for part in spec.split(","):
        if "=" not in part:
            continue
        k, _, v = part.partition("=")
        k = k.strip()
        v = v.strip()
        if not k or not v:
            continue
        out[k] = {"$eq": v}
    return out or None


# ----- runtime -----

def _build_chat(settings: Settings) -> LegalAdvisorChat:
    mongo = MongoClientWrapper(settings.mongo_uri, settings.mongo_db_name)
    mongo.ping()

    embedder = VoyageEmbedder(api_key=settings.voyage_api_key, model=settings.embedding_model)
    reranker = VoyageReranker(api_key=settings.voyage_api_key, model=settings.rerank_model)

    retriever = Retriever(
        mongo=mongo,
        embedder=embedder,
        reranker=reranker,
        vector_index_name=settings.vector_index_name,
        retrieval_top_k=settings.retrieval_top_k,
        rerank_top_k=settings.rerank_top_k,
    )
    return LegalAdvisorChat(
        anthropic_api_key=settings.anthropic_api_key,
        retriever=retriever,
        model=settings.claude_model,
    )


def _interactive(chat: LegalAdvisorChat) -> int:
    print("Legal-advisor chat. Type a question, /help, or /quit.")
    active_filter: Optional[dict] = None

    while True:
        try:
            q = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not q:
            continue
        if q in {"/quit", "/exit", "/q"}:
            return 0
        if q in {"/help", "/h", "/?"}:
            print(
                "Commands:\n"
                "  /reset                    start a fresh conversation\n"
                "  /sources                  show source previews from the last answer\n"
                "  /filter <spec>            apply retrieval filter (e.g. date_ym=2024-03)\n"
                "  /filter clear             remove the current filter\n"
                "  /quit                     exit\n"
            )
            continue
        if q == "/reset":
            chat.reset()
            print("Conversation history cleared.")
            continue
        if q == "/sources":
            if not chat.history:
                print("No turns yet.")
                continue
            _print_turn(chat.history[-1], full_sources=True)
            continue
        if q.startswith("/filter"):
            spec = q[len("/filter"):].strip()
            active_filter = _parse_filter_spec(spec) if spec else None
            print(f"Active filter: {active_filter}")
            continue

        try:
            turn = chat.ask(q, atlas_filter=active_filter)
        except Exception as exc:
            print(f"[error] {exc}")
            continue
        _print_turn(turn)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("question", nargs="*", help="Question to ask (omit to enter REPL)")
    p.add_argument("--filter", default="", help="Inline retrieval filter (e.g. 'date_ym=2024-03')")
    p.add_argument("--full-sources", action="store_true",
                   help="Print source previews after each answer")
    args = p.parse_args()

    settings = Settings.load()
    configure_logger(settings.logs_dir)

    chat = _build_chat(settings)

    if args.question:
        question = " ".join(args.question)
        atlas_filter = _parse_filter_spec(args.filter) if args.filter else None
        turn = chat.ask(question, atlas_filter=atlas_filter)
        _print_turn(turn, full_sources=args.full_sources)
        return 0
    return _interactive(chat)


if __name__ == "__main__":
    raise SystemExit(main())
