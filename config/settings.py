"""Centralized configuration loaded from .env."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=True)


def _get(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.getenv(name, default)
    if required and (value is None or value == ""):
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value or ""


def _get_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be an integer") from exc


def _get_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _get_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be a float") from exc


@dataclass(frozen=True)
class Settings:
    mongo_uri: str
    mongo_db_name: str
    pst_file_path: Path
    batch_size: int
    max_body_chars: int
    attachment_max_bytes: int
    anthropic_api_key: str
    voyage_api_key: str
    project_root: Path
    logs_dir: Path
    excel_rows_per_file: int
    export_dir: Path
    attachments_dir: Path

    # Phase 2 — RAG
    embedding_model: str
    embedding_dim: int
    rerank_model: str
    claude_model: str
    claude_max_output_tokens: int
    chunk_size_tokens: int
    chunk_overlap_tokens: int
    retrieval_top_k: int
    rerank_top_k: int
    vector_index_name: str
    ocr_lang: str
    ocr_dpi: int
    ocr_text_layer_min_chars: int
    ocr_vision_enabled: bool
    ocr_vision_model: str
    ocr_vision_min_pages: int
    ocr_vision_dpi: int
    ocr_vision_max_concurrency: int
    ocr_vision_budget_usd: float

    # =====================================================================
    # RAG v2 — drop-in upgrades (all default OFF, no re-embedding required)
    # =====================================================================
    # Master switch — when False, every v2 feature stays off regardless of
    # individual flags below.
    rag_v2_enabled: bool

    # Sprint 1 — retrieval-side improvements
    rag_v2_hybrid_search: bool        # BM25 + vector with Reciprocal Rank Fusion
    rag_v2_filename_lookup: bool      # Direct filename matching when query names a doc
    rag_v2_hyde: bool                 # Hypothetical Document Embeddings
    rag_v2_multi_query: bool          # Generate 2-3 alternate query phrasings
    rag_v2_date_filters: bool         # Auto-extract date filters from queries
    rag_v2_enhanced_prompt: bool      # New system prompt with self-critique block

    # Sprint 2 — context + temporal awareness
    rag_v2_parent_doc: bool           # Pull parent document context when chunks cluster
    rag_v2_temporal_diversity: bool   # Ensure newest version of each fact retained
    rag_v2_adaptive_k: bool           # Dynamic top-K (20-40 based on query complexity)
    rag_v2_rescoring: bool            # Recency/authority/exact-match scoring boost
    rag_v2_summary_memory: bool       # Conversation summary memory for long chats

    # Sprint 2.5 (pre-Sprint-3) accuracy levers
    rag_v2_full_doc_mode: bool        # Pull whole document when query names it
    rag_v2_interleaved_ordering: bool # Best chunks at start AND end (primacy/recency)
    rag_v2_xml_sources: bool          # Wrap each source in <doc>...</doc> XML

    # Sprint 3 finish — verified-answer pipeline (structured output + citation
    # verifier + self-correction loop). Each fact must ship with a verbatim
    # quote from a retrieved chunk; the deterministic verifier checks it; if a
    # fact fails, Opus is asked to re-extract; if it still fails, we ship the
    # original answer as-is per the "trust Opus when self-consistent" policy.
    rag_v2_structured_output: bool    # Force submit_answer tool-use shape
    rag_v2_citation_verifier: bool    # Run the deterministic verifier
    rag_v2_verifier_retry: bool       # Self-correction loop on failed claims
    rag_v2_verifier_threshold: float  # rapidfuzz partial_ratio cutoff (default 85)
    rag_v2_verifier_log: bool         # Persist verification_log records to Mongo

    # Sprint 4 — Agentic Legal Investigator. When `rag_v3_agent_enabled` is on,
    # the chat layer routes through `src/rag/v3/agent.py` which gives Opus a
    # tool palette (search, fetch_full_document, compare_versions, verify_claim,
    # etc.) and lets it reason iteratively. Falls back gracefully to Sprint 3
    # verified one-shot if the agent fails / hits budget.
    rag_v3_agent_enabled: bool             # Master switch for the agent loop
    rag_v3_agent_max_tool_calls: int       # Per-query hard cap (default 8)
    rag_v3_agent_max_total_tokens: int     # Per-query token budget (default 60000)
    rag_v3_agent_max_wall_clock_s: float   # Per-query wall-clock cap (seconds)
    rag_v3_agent_model: str                # Planner model (Opus recommended)
    rag_v3_agent_max_tokens_per_call: int  # max_tokens per planner LLM call
    rag_v3_agent_seed_with_initial_search: bool   # Seed with v2 retrieve first
    rag_v3_agent_trace_log: bool           # Persist agent_trace to Mongo
    rag_v3_agent_effort: str               # Opus 4.8 adaptive-thinking effort (xhigh)

    # v2 tunables — models
    rag_v2_query_rewriter_model: str  # LLM used for HyDE + multi-query (Sonnet 4.6 default)
    rag_v2_summary_model: str         # LLM used for conversation summary

    # Sprint 7.1 — LLM-as-reranker (Opus final relevance pass on top-N)
    rag_v2_llm_reranker: bool
    rag_v2_llm_reranker_model: str
    rag_v2_llm_reranker_top_n: int

    # v2 tunables — channel-level retrieval
    rag_v2_max_alt_queries: int       # How many alternate phrasings to generate
    rag_v2_rrf_k: int                 # RRF formula constant (literature default 60)
    rag_v2_rrf_fused_cap: int         # Max unique chunks kept after fusion
    rag_v2_vector_top_k: int          # Candidates per query embedding
    rag_v2_vector_min_score: float    # Vector recall floor (0.0 = off)
    rag_v2_bm25_top_k: int            # Candidates per BM25 phrasing
    rag_v2_phrase_top_k: int          # Candidates per quoted-phrase BM25
    rag_v2_body_regex_top_k: int      # Candidates per literal substring lookup
    rag_v2_filename_top_k: int        # Candidates per filename hint
    rag_v2_cluster_cap_per_parent: int  # Max chunks per parent post-diversification

    # v2 tunables — adaptive K (chunks delivered to Claude)
    rag_v2_adaptive_k_simple: int         # Lookup-style queries
    rag_v2_adaptive_k_complex: int        # Compare/timeline/opinion queries
    rag_v2_adaptive_k_comprehensive: int  # "all/every" or 4+ entity signals

    # v2 tunables — parent-doc expansion
    rag_v2_parent_doc_token_budget: int  # Budget when only one parent expands
    rag_v2_parent_doc_max_parents: int   # Cap on hot parents that get expansion
    rag_v2_parent_doc_max_per_parent: int  # Per-parent chunk-count safety cap

    # v2 tunables — full-doc mode
    rag_v2_full_doc_token_budget: int  # Cap for a single named doc
    rag_v2_full_doc_max_docs: int      # Cap on docs that get full-doc treatment

    # v2 safety — total evidence cap (Opus 4.6 multi-needle safe zone)
    rag_v2_total_evidence_cap_tokens: int

    # v2 tunables — conversation summary memory
    rag_v2_summary_after_turns: int   # Start summarizing after N turns
    rag_v2_summary_keep_recent: int   # Keep last N turns verbatim

    # v2 corpus — Option B targets a SEPARATE chunks collection and its
    # own Atlas Vector Search index. Defaults point at the v2 collection.
    rag_v2_chunks_collection: str
    rag_v2_vector_index_name: str

    @classmethod
    def load(cls) -> "Settings":
        pst_raw = _get("PST_FILE_PATH", required=True)
        pst_path = Path(pst_raw)
        if not pst_path.is_absolute():
            pst_path = PROJECT_ROOT / pst_path

        logs_dir = PROJECT_ROOT / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        export_raw = _get("EXPORT_DIR", "exports")
        export_dir = Path(export_raw)
        if not export_dir.is_absolute():
            export_dir = PROJECT_ROOT / export_dir

        attachments_raw = _get("ATTACHMENTS_DIR", "attachments")
        attachments_dir = Path(attachments_raw)
        if not attachments_dir.is_absolute():
            attachments_dir = PROJECT_ROOT / attachments_dir

        return cls(
            mongo_uri=_get("MONGO_URI", required=True),
            mongo_db_name=_get("MONGO_DB_NAME", default="fraud_emails"),
            pst_file_path=pst_path,
            batch_size=_get_int("BATCH_SIZE", 100),
            max_body_chars=_get_int("MAX_BODY_CHARS", 2_000_000),
            attachment_max_bytes=_get_int("ATTACHMENT_MAX_BYTES", 50 * 1024 * 1024),
            anthropic_api_key=_get("ANTHROPIC_API_KEY"),
            voyage_api_key=_get("VOYAGE_API_KEY"),
            project_root=PROJECT_ROOT,
            logs_dir=logs_dir,
            excel_rows_per_file=_get_int("EXCEL_ROWS_PER_FILE", 500),
            export_dir=export_dir,
            attachments_dir=attachments_dir,
            embedding_model=_get("EMBEDDING_MODEL", "voyage-4-large"),
            embedding_dim=_get_int("EMBEDDING_DIM", 1024),
            rerank_model=_get("RERANK_MODEL", "rerank-2.5"),
            claude_model=_get("CLAUDE_MODEL", "claude-opus-4-8"),
            claude_max_output_tokens=_get_int("CLAUDE_MAX_OUTPUT_TOKENS", 40960),
            # Defaults aligned to the LIVE email_chunks_v2 corpus (1000/200).
            chunk_size_tokens=_get_int("CHUNK_SIZE_TOKENS", 1000),
            chunk_overlap_tokens=_get_int("CHUNK_OVERLAP_TOKENS", 200),
            retrieval_top_k=_get_int("RETRIEVAL_TOP_K", 50),
            rerank_top_k=_get_int("RERANK_TOP_K", 8),
            vector_index_name=_get("VECTOR_INDEX_NAME", "email_chunks_vector"),
            ocr_lang=_get("OCR_LANG", "en"),
            ocr_dpi=_get_int("OCR_DPI", 300),
            ocr_text_layer_min_chars=_get_int("OCR_TEXT_LAYER_MIN_CHARS", 80),
            ocr_vision_enabled=_get("OCR_VISION_ENABLED", "true").lower() in ("1", "true", "yes"),
            ocr_vision_model=_get("OCR_VISION_MODEL", "claude-sonnet-4-6"),
            ocr_vision_min_pages=_get_int("OCR_VISION_MIN_PAGES", 3),
            ocr_vision_dpi=_get_int("OCR_VISION_DPI", 180),
            ocr_vision_max_concurrency=_get_int("OCR_VISION_MAX_CONCURRENCY", 8),
            ocr_vision_budget_usd=float(_get("OCR_VISION_BUDGET_USD", "15.0")),

            # ---- RAG v2 feature flags (drop-in, no re-embedding) ----
            rag_v2_enabled=_get_bool("RAG_V2_ENABLED", False),
            rag_v2_hybrid_search=_get_bool("RAG_V2_HYBRID_SEARCH", False),
            rag_v2_filename_lookup=_get_bool("RAG_V2_FILENAME_LOOKUP", False),
            rag_v2_hyde=_get_bool("RAG_V2_HYDE", False),
            rag_v2_multi_query=_get_bool("RAG_V2_MULTI_QUERY", False),
            rag_v2_date_filters=_get_bool("RAG_V2_DATE_FILTERS", False),
            rag_v2_enhanced_prompt=_get_bool("RAG_V2_ENHANCED_PROMPT", False),
            rag_v2_parent_doc=_get_bool("RAG_V2_PARENT_DOC", False),
            rag_v2_temporal_diversity=_get_bool("RAG_V2_TEMPORAL_DIVERSITY", False),
            rag_v2_adaptive_k=_get_bool("RAG_V2_ADAPTIVE_K", False),
            rag_v2_rescoring=_get_bool("RAG_V2_RESCORING", False),
            rag_v2_summary_memory=_get_bool("RAG_V2_SUMMARY_MEMORY", False),

            # Sprint 2.5 levers
            rag_v2_full_doc_mode=_get_bool("RAG_V2_FULL_DOC_MODE", False),
            rag_v2_interleaved_ordering=_get_bool("RAG_V2_INTERLEAVED_ORDERING", False),
            rag_v2_xml_sources=_get_bool("RAG_V2_XML_SOURCES", False),

            # Sprint 3 finish — verified-answer pipeline
            rag_v2_structured_output=_get_bool("RAG_V2_STRUCTURED_OUTPUT", False),
            rag_v2_citation_verifier=_get_bool("RAG_V2_CITATION_VERIFIER", False),
            rag_v2_verifier_retry=_get_bool("RAG_V2_VERIFIER_RETRY", False),
            rag_v2_verifier_threshold=_get_float("RAG_V2_VERIFIER_THRESHOLD", 85.0),
            rag_v2_verifier_log=_get_bool("RAG_V2_VERIFIER_LOG", False),

            # Sprint 4 — Agentic Legal Investigator (worst-case ceilings;
            # see .env for rationale). These are intentionally far above
            # typical usage so the agent never gets cut off on a hard
            # legal query.
            rag_v3_agent_enabled=_get_bool("RAG_V3_AGENT_ENABLED", False),
            rag_v3_agent_max_tool_calls=_get_int("RAG_V3_AGENT_MAX_TOOL_CALLS", 30),
            rag_v3_agent_max_total_tokens=_get_int("RAG_V3_AGENT_MAX_TOTAL_TOKENS", 15_000_000),
            rag_v3_agent_max_wall_clock_s=_get_float("RAG_V3_AGENT_MAX_WALL_CLOCK_S", 1200.0),
            rag_v3_agent_model=_get("RAG_V3_AGENT_MODEL", "claude-opus-4-8"),
            rag_v3_agent_max_tokens_per_call=_get_int("RAG_V3_AGENT_MAX_TOKENS_PER_CALL", 64000),
            rag_v3_agent_seed_with_initial_search=_get_bool("RAG_V3_AGENT_SEED_WITH_INITIAL_SEARCH", True),
            rag_v3_agent_trace_log=_get_bool("RAG_V3_AGENT_TRACE_LOG", True),
            rag_v3_agent_effort=_get("RAG_V3_AGENT_EFFORT", "xhigh"),

            # tunables — models
            rag_v2_query_rewriter_model=_get(
                "RAG_V2_QUERY_REWRITER_MODEL", "claude-sonnet-4-6"
            ),
            rag_v2_summary_model=_get(
                "RAG_V2_SUMMARY_MODEL", "claude-sonnet-4-6"
            ),
            rag_v2_llm_reranker=_get_bool("RAG_V2_LLM_RERANKER", True),
            rag_v2_llm_reranker_model=_get("RAG_V2_LLM_RERANKER_MODEL", "claude-opus-4-8"),
            rag_v2_llm_reranker_top_n=_get_int("RAG_V2_LLM_RERANKER_TOP_N", 50),

            # tunables — channels
            rag_v2_max_alt_queries=_get_int("RAG_V2_MAX_ALT_QUERIES", 3),
            rag_v2_rrf_k=_get_int("RAG_V2_RRF_K", 60),
            rag_v2_rrf_fused_cap=_get_int("RAG_V2_RRF_FUSED_CAP", 200),
            rag_v2_vector_top_k=_get_int("RAG_V2_VECTOR_TOP_K", 150),
            rag_v2_vector_min_score=_get_float("RAG_V2_VECTOR_MIN_SCORE", 0.0),
            rag_v2_bm25_top_k=_get_int("RAG_V2_BM25_TOP_K", 100),
            rag_v2_phrase_top_k=_get_int("RAG_V2_PHRASE_TOP_K", 80),
            rag_v2_body_regex_top_k=_get_int("RAG_V2_BODY_REGEX_TOP_K", 80),
            rag_v2_filename_top_k=_get_int("RAG_V2_FILENAME_TOP_K", 50),
            rag_v2_cluster_cap_per_parent=_get_int("RAG_V2_CLUSTER_CAP_PER_PARENT", 5),

            # tunables — adaptive K
            rag_v2_adaptive_k_simple=_get_int("RAG_V2_ADAPTIVE_K_SIMPLE", 70),
            rag_v2_adaptive_k_complex=_get_int("RAG_V2_ADAPTIVE_K_COMPLEX", 100),
            rag_v2_adaptive_k_comprehensive=_get_int("RAG_V2_ADAPTIVE_K_COMPREHENSIVE", 120),

            # tunables — parent-doc
            rag_v2_parent_doc_token_budget=_get_int("RAG_V2_PARENT_DOC_TOKEN_BUDGET", 8000),
            rag_v2_parent_doc_max_parents=_get_int("RAG_V2_PARENT_DOC_MAX_PARENTS", 5),
            rag_v2_parent_doc_max_per_parent=_get_int("RAG_V2_PARENT_DOC_MAX_PER_PARENT", 20),

            # tunables — full-doc mode
            rag_v2_full_doc_token_budget=_get_int("RAG_V2_FULL_DOC_TOKEN_BUDGET", 50000),
            rag_v2_full_doc_max_docs=_get_int("RAG_V2_FULL_DOC_MAX_DOCS", 4),

            # safety
            rag_v2_total_evidence_cap_tokens=_get_int(
                "RAG_V2_TOTAL_EVIDENCE_CAP_TOKENS", 500000
            ),

            # tunables — summary memory
            rag_v2_summary_after_turns=_get_int("RAG_V2_SUMMARY_AFTER_TURNS", 8),
            rag_v2_summary_keep_recent=_get_int("RAG_V2_SUMMARY_KEEP_RECENT", 5),

            # Option B corpus targets
            rag_v2_chunks_collection=_get(
                "RAG_V2_CHUNKS_COLLECTION", "email_chunks_v2"
            ),
            rag_v2_vector_index_name=_get(
                "RAG_V2_VECTOR_INDEX_NAME", "email_chunks_v2_vector"
            ),
        )


settings = Settings.load() if os.getenv("MONGO_URI") and os.getenv("MONGO_URI") != "placeholder" else None
