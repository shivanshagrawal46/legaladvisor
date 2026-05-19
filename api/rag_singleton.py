"""
Lazy singleton for the RAG components.

Initialised once on first use so the FastAPI startup is instant.
The RAG system (mongo, embedder, reranker, retriever, chat class) is
kept in module-level globals and reused across all WebSocket connections
and HTTP requests.

IMPORTANT: We do NOT touch any RAG source files. We only import and
instantiate them here.
"""
from __future__ import annotations

from typing import Optional

from config.settings import Settings
from src.db.mongo import MongoClientWrapper
from src.rag.chat import LegalAdvisorChat
from src.rag.embedder import VoyageEmbedder
from src.rag.reranker import VoyageReranker
from src.rag.retriever import Retriever

_settings: Optional[Settings] = None
_mongo: Optional[MongoClientWrapper] = None
_embedder: Optional[VoyageEmbedder] = None
_reranker: Optional[VoyageReranker] = None
_retriever: Optional[Retriever] = None


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


def get_retriever() -> Retriever:
    global _embedder, _reranker, _retriever
    if _retriever is None:
        s = get_settings()
        m = get_mongo()
        _embedder = VoyageEmbedder(api_key=s.voyage_api_key, model=s.embedding_model)
        _reranker = VoyageReranker(api_key=s.voyage_api_key, model=s.rerank_model)
        _retriever = Retriever(
            mongo=m,
            embedder=_embedder,
            reranker=_reranker,
            vector_index_name=s.vector_index_name,
            retrieval_top_k=s.retrieval_top_k,
            rerank_top_k=s.rerank_top_k,
        )
    return _retriever


def make_chat() -> LegalAdvisorChat:
    """Return a fresh LegalAdvisorChat per session (each has its own history)."""
    s = get_settings()
    retr = get_retriever()
    return LegalAdvisorChat(
        anthropic_api_key=s.anthropic_api_key,
        retriever=retr,
        model=s.claude_model,
    )
