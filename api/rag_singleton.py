"""
Lazy singleton for the RAG components.

Initialised once on first use so the FastAPI startup is instant.
The RAG system (mongo, embedder, reranker, retriever, chat class) is
kept in module-level globals and reused across all WebSocket connections
and HTTP requests.

When `RAG_V2_ENABLED=true` (and any v2 feature flags are also true),
we additionally construct a `V2Pipeline` and attach it to the retriever.
The retriever transparently routes through v2; on any v2 error it falls
back to v1 so production never breaks because of a v2 bug.

IMPORTANT: We do NOT mutate any RAG source files at runtime. We only
import, instantiate, and inject.
"""
from __future__ import annotations

from typing import Optional

import anthropic

from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.rag.chat import LegalAdvisorChat
from src.rag.embedder import VoyageEmbedder
from src.rag.reranker import VoyageReranker
from src.rag.retriever import Retriever
from src.utils.logger import logger


_settings: Optional[Settings] = None
_mongo: Optional[MongoClientWrapper] = None
_embedder: Optional[VoyageEmbedder] = None
_reranker: Optional[VoyageReranker] = None
_retriever: Optional[Retriever] = None
_anthropic_client: Optional[anthropic.Anthropic] = None
_v2_pipeline = None  # type: Optional[object] — circular-import-friendly


# ---------------------------------------------------------------------------
# Settings + connection components
# ---------------------------------------------------------------------------

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings.load()
    return _settings


def get_mongo() -> MongoClientWrapper:
    global _mongo
    if _mongo is None:
        s = get_settings()
        _mongo = MongoClientWrapper(s.mongo_uri, s.mongo_db_name)
        _mongo.ping()
    return _mongo


def get_anthropic_client() -> anthropic.Anthropic:
    """Single shared Anthropic client (thread-safe per SDK docs)."""
    global _anthropic_client
    if _anthropic_client is None:
        s = get_settings()
        _anthropic_client = anthropic.Anthropic(api_key=s.anthropic_api_key)
    return _anthropic_client


# ---------------------------------------------------------------------------
# v2 pipeline — built only when RAG_V2_ENABLED is true
# ---------------------------------------------------------------------------

def _build_v2_pipeline_if_enabled():
    """
    Returns a V2Pipeline or None.

    All flags off → returns None and the retriever stays in v1 mode.
    We import lazily so v1-only deployments don't pay the import cost.
    """
    s = get_settings()
    if not s.rag_v2_enabled:
        return None

    # Lazy import keeps v1 deployments completely free of v2 module loads.
    from src.rag.v2.orchestrator import V2Pipeline, V2Settings

    v2_settings = V2Settings(
        enabled=s.rag_v2_enabled,
        hybrid_search=s.rag_v2_hybrid_search,
        filename_lookup=s.rag_v2_filename_lookup,
        hyde=s.rag_v2_hyde,
        multi_query=s.rag_v2_multi_query,
        date_filters=s.rag_v2_date_filters,
        parent_doc=s.rag_v2_parent_doc,
        temporal_diversity=s.rag_v2_temporal_diversity,
        adaptive_k=s.rag_v2_adaptive_k,
        rescoring=s.rag_v2_rescoring,
        # Sprint 2.5 levers
        full_doc_mode=s.rag_v2_full_doc_mode,
        interleaved_ordering=s.rag_v2_interleaved_ordering,
        # Channel-level tunables
        rrf_k=s.rag_v2_rrf_k,
        rrf_fused_cap=s.rag_v2_rrf_fused_cap,
        vector_top_k=s.rag_v2_vector_top_k,
        vector_min_score=s.rag_v2_vector_min_score,
        bm25_top_k=s.rag_v2_bm25_top_k,
        phrase_top_k=s.rag_v2_phrase_top_k,
        body_regex_top_k=s.rag_v2_body_regex_top_k,
        filename_top_k=s.rag_v2_filename_top_k,
        max_per_cluster=s.rag_v2_cluster_cap_per_parent,
        max_alt_queries=s.rag_v2_max_alt_queries,
        # Adaptive K
        rerank_top_k_default=s.rerank_top_k,
        adaptive_k_simple=s.rag_v2_adaptive_k_simple,
        adaptive_k_complex=s.rag_v2_adaptive_k_complex,
        adaptive_k_comprehensive=s.rag_v2_adaptive_k_comprehensive,
        # Parent-doc
        parent_doc_token_budget=s.rag_v2_parent_doc_token_budget,
        parent_doc_max_parents=s.rag_v2_parent_doc_max_parents,
        parent_doc_max_per_parent=s.rag_v2_parent_doc_max_per_parent,
        # Full-doc
        full_doc_token_budget=s.rag_v2_full_doc_token_budget,
        full_doc_max_docs=s.rag_v2_full_doc_max_docs,
        # Safety cap
        total_evidence_cap_tokens=s.rag_v2_total_evidence_cap_tokens,
        # Models
        query_rewriter_model=s.rag_v2_query_rewriter_model,
        # Sprint 7.1 LLM-as-reranker (Opus final pass)
        llm_reranker=s.rag_v2_llm_reranker,
        llm_reranker_model=s.rag_v2_llm_reranker_model,
        llm_reranker_top_n=s.rag_v2_llm_reranker_top_n,
        llm_reranker_effort=s.rag_v2_llm_reranker_effort,
        # Option B targets — when v2 is enabled we point at the v2
        # chunks collection and its dedicated Atlas index.
        chunks_collection_name=s.rag_v2_chunks_collection,
    )

    return V2Pipeline.build(
        mongo=get_mongo(),
        embedder=_get_embedder(),
        reranker=_get_reranker(),
        anthropic_client=get_anthropic_client(),
        # v2 has its own Atlas Vector Search index over `email_chunks_v2`.
        vector_index_name=s.rag_v2_vector_index_name,
        v2_settings=v2_settings,
    )


def _get_embedder() -> VoyageEmbedder:
    global _embedder
    if _embedder is None:
        s = get_settings()
        _embedder = VoyageEmbedder(api_key=s.voyage_api_key, model=s.embedding_model)
    return _embedder


def _get_reranker() -> VoyageReranker:
    global _reranker
    if _reranker is None:
        s = get_settings()
        _reranker = VoyageReranker(api_key=s.voyage_api_key, model=s.rerank_model)
    return _reranker


def _get_v2_pipeline():
    global _v2_pipeline
    # Allow None as a valid cached value when v2 is off.
    if _v2_pipeline is None:
        _v2_pipeline = _build_v2_pipeline_if_enabled()
    return _v2_pipeline


# ---------------------------------------------------------------------------
# Retriever (with optional v2 pipeline attached)
# ---------------------------------------------------------------------------

def get_retriever() -> Retriever:
    global _retriever
    if _retriever is None:
        s = get_settings()
        _retriever = Retriever(
            mongo=get_mongo(),
            embedder=_get_embedder(),
            reranker=_get_reranker(),
            vector_index_name=s.vector_index_name,
            retrieval_top_k=s.retrieval_top_k,
            rerank_top_k=s.rerank_top_k,
            v2_pipeline=_get_v2_pipeline(),
        )
    return _retriever


# ---------------------------------------------------------------------------
# Chat — fresh instance per session (each has its own history)
# ---------------------------------------------------------------------------

def make_chat() -> LegalAdvisorChat:
    """Return a fresh LegalAdvisorChat per session (each has its own history)."""
    s = get_settings()
    retr = get_retriever()
    client = get_anthropic_client()

    summary_memory = None
    if s.rag_v2_enabled and s.rag_v2_summary_memory:
        # Lazy import keeps v1 deployments lean.
        from src.rag.v2.memory import SummaryMemory
        summary_memory = SummaryMemory(
            client=client,
            model=s.rag_v2_summary_model,
            summary_after_turns=s.rag_v2_summary_after_turns,
            keep_recent=s.rag_v2_summary_keep_recent,
        )

    # Sprint 3 finish — wire verified-answer pipeline.
    use_structured = bool(s.rag_v2_enabled and s.rag_v2_structured_output)
    use_verifier = bool(s.rag_v2_enabled and s.rag_v2_citation_verifier)
    verifier_log_db = None
    if use_verifier and s.rag_v2_verifier_log:
        # Best-effort: surface the chunks-collection's database object so
        # the verifier can write to verification_log alongside the corpus.
        try:
            verifier_log_db = get_retriever().mongo.db
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"verification_log disabled (no Mongo handle): {exc}")

    # Sprint 4 — Agentic Legal Investigator is the SOLE production path.
    # In normal deployment the agent is always on; chat.py's `ask()`
    # routes every query through `_ask_agent`. The env flag
    # `RAG_V3_AGENT_ENABLED` is kept only as an explicit debug
    # escape-hatch: when set to false, chat.py still calls _ask_agent
    # but `agent_v2_pipeline=None` triggers an immediate graceful
    # degrade to the verified one-shot.
    #
    # The agent requires the v2 pipeline (used as its tool palette) and
    # internally always runs the Sprint-3 verifier + retry pass on its
    # output regardless of the verifier env flags. The verifier flags
    # below still gate the FALLBACK `_ask_verified` path used when the
    # agent loop crashes or is disabled.
    use_agent = bool(
        s.rag_v2_enabled
        and s.rag_v3_agent_enabled
    )
    agent_v2_pipeline = _get_v2_pipeline() if use_agent else None
    agent_trace_log_db = None
    if use_agent and s.rag_v3_agent_trace_log:
        try:
            agent_trace_log_db = get_retriever().mongo.db
        except Exception as exc:  # noqa: BLE001
            logger.warning(f"agent_trace_log disabled (no Mongo handle): {exc}")
    if not use_agent:
        logger.warning(
            "RAG_V3_AGENT_ENABLED is off — every query will degrade to "
            "the verified one-shot. Re-enable it in production."
        )

    return LegalAdvisorChat(
        anthropic_api_key=s.anthropic_api_key,
        retriever=retr,
        model=s.claude_model,
        max_tokens=s.claude_max_output_tokens,
        anthropic_client=client,
        use_enhanced_prompt=(s.rag_v2_enabled and s.rag_v2_enhanced_prompt),
        summary_memory=summary_memory,
        xml_sources=(s.rag_v2_enabled and s.rag_v2_xml_sources),
        use_structured_output=use_structured,
        use_citation_verifier=use_verifier,
        use_verifier_retry=bool(s.rag_v2_enabled and s.rag_v2_verifier_retry),
        verifier_threshold=s.rag_v2_verifier_threshold,
        verifier_log_db=verifier_log_db,
        # Sprint 4 wiring
        use_agent=use_agent,
        agent_v2_pipeline=agent_v2_pipeline,
        agent_max_tool_calls=s.rag_v3_agent_max_tool_calls,
        agent_max_total_tokens=s.rag_v3_agent_max_total_tokens,
        agent_max_wall_clock_s=s.rag_v3_agent_max_wall_clock_s,
        agent_model=s.rag_v3_agent_model,
        agent_max_tokens_per_call=s.rag_v3_agent_max_tokens_per_call,
        agent_effort=s.rag_v3_agent_effort,
        agent_seed_with_initial_search=s.rag_v3_agent_seed_with_initial_search,
        agent_trace_log_db=agent_trace_log_db,
    )
