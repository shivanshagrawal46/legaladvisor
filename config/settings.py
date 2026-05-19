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
            embedding_model=_get("EMBEDDING_MODEL", "voyage-3"),
            embedding_dim=_get_int("EMBEDDING_DIM", 1024),
            rerank_model=_get("RERANK_MODEL", "rerank-2.5"),
            claude_model=_get("CLAUDE_MODEL", "claude-sonnet-4-6"),
            chunk_size_tokens=_get_int("CHUNK_SIZE_TOKENS", 500),
            chunk_overlap_tokens=_get_int("CHUNK_OVERLAP_TOKENS", 100),
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
        )


settings = Settings.load() if os.getenv("MONGO_URI") and os.getenv("MONGO_URI") != "placeholder" else None
