# app/knowledge_base/embedding/__init__.py
"""Embedding service for knowledge base."""

from app.knowledge_base.embedding.embedding_service import (
    EmbeddingService,
    EmbeddingResult,
    get_embedding_service,
)

__all__ = [
    "EmbeddingService",
    "EmbeddingResult",
    "get_embedding_service",
]
