# app/knowledge_base/__init__.py
"""
Knowledge Base module for RAG-based log analysis.

This module provides:
- Code parsing and extraction from Java/TypeScript codebases
- Embedding generation for semantic search
- Vector-based retrieval for context injection
- Ingestion pipeline for populating the knowledge base

Usage:
    # Run ingestion
    from app.knowledge_base.ingestion import IngestionPipeline
    pipeline = IngestionPipeline()
    stats = pipeline.run_full_ingestion()

    # Query knowledge base
    from app.knowledge_base.retrieval import get_rag_service
    rag = get_rag_service()
    results = rag.retrieve("payment processing error")

    # CLI usage
    uv run python -m app.knowledge_base.ingestion.cli ingest
    uv run python -m app.knowledge_base.ingestion.cli search "payment"
    uv run python -m app.knowledge_base.ingestion.cli stats
"""

from app.knowledge_base.models.kb_models import KBService, KBElement, KBIngestionRun
from app.knowledge_base.embedding.embedding_service import EmbeddingService, get_embedding_service
from app.knowledge_base.retrieval.rag_service import RAGService, RetrievalResult, get_rag_service
from app.knowledge_base.ingestion.pipeline import IngestionPipeline, run_ingestion

__all__ = [
    # Models
    "KBService",
    "KBElement",
    "KBIngestionRun",
    # Embedding
    "EmbeddingService",
    "get_embedding_service",
    # Retrieval
    "RAGService",
    "RetrievalResult",
    "get_rag_service",
    # Ingestion
    "IngestionPipeline",
    "run_ingestion",
]
