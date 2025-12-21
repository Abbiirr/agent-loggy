# app/knowledge_base/ingestion/__init__.py
"""Ingestion pipeline for populating the knowledge base."""

from app.knowledge_base.ingestion.pipeline import IngestionPipeline

__all__ = [
    "IngestionPipeline",
]
