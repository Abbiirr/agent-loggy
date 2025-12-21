# app/knowledge_base/retrieval/__init__.py
"""RAG retrieval service for knowledge base queries."""

from app.knowledge_base.retrieval.rag_service import (
    RAGService,
    RetrievalResult,
    get_rag_service,
)

__all__ = [
    "RAGService",
    "RetrievalResult",
    "get_rag_service",
]
