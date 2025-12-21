# app/knowledge_base/models/kb_models.py
"""
SQLAlchemy models for the knowledge base tables.

These models support:
- Service-level knowledge with summary embeddings
- Element-level knowledge (endpoints, exceptions, etc.) with content embeddings
- Ingestion run tracking for audit and debugging
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    ForeignKey, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from app.db.base import Base
from app.config import settings


class KBService(Base):
    """
    Service-level knowledge base entry.

    Represents a microservice from the codebase with aggregated metadata
    and a summary embedding for high-level semantic search.
    """
    __tablename__ = "kb_services"
    __table_args__ = (
        Index("idx_kb_services_code", "service_code"),
        Index("idx_kb_services_type", "service_type"),
        Index("idx_kb_services_active", "is_active"),
        {"schema": settings.DATABASE_SCHEMA}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_code = Column(String(100), nullable=False, unique=True)
    service_name = Column(String(255), nullable=False)
    service_type = Column(String(50), nullable=False)  # 'spring-boot', 'angular', 'java'
    base_package = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)

    # Vector embedding for service-level semantic search (768 dims for nomic-embed-text)
    summary_embedding = Column(Vector(768), nullable=True)

    # Aggregated counts
    api_endpoints_count = Column(Integer, nullable=False, default=0)
    classes_count = Column(Integer, nullable=False, default=0)
    error_codes_count = Column(Integer, nullable=False, default=0)

    # Flexible metadata storage (using 'extra' to avoid SQLAlchemy reserved 'metadata')
    extra = Column('metadata', JSONB, nullable=False, default=dict)

    # Status and timestamps
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    indexed_at = Column(DateTime, nullable=True)

    # Relationship to elements
    elements = relationship("KBElement", back_populates="service", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<KBService(code={self.service_code}, type={self.service_type})>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "service_code": self.service_code,
            "service_name": self.service_name,
            "service_type": self.service_type,
            "base_package": self.base_package,
            "description": self.description,
            "api_endpoints_count": self.api_endpoints_count,
            "classes_count": self.classes_count,
            "error_codes_count": self.error_codes_count,
            "metadata": self.extra,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None,
        }


class KBElement(Base):
    """
    Element-level knowledge base entry.

    Represents a specific code element (endpoint, exception, DTO, etc.)
    with its own embedding for fine-grained semantic search.

    Element types:
    - 'endpoint': REST API endpoint
    - 'exception': Exception class
    - 'error_code': Error code constant
    - 'dto': Data Transfer Object
    - 'service_call': Inter-service call (Feign client, HTTP)
    - 'log_pattern': Logging statement pattern
    - 'class': General class
    - 'method': General method
    """
    __tablename__ = "kb_elements"
    __table_args__ = (
        Index("idx_kb_elements_service", "service_id"),
        Index("idx_kb_elements_type", "element_type"),
        Index("idx_kb_elements_name", "element_name"),
        Index("idx_kb_elements_qualified", "qualified_name"),
        Index("idx_kb_elements_active", "is_active"),
        Index("idx_kb_elements_service_type", "service_id", "element_type"),
        {"schema": settings.DATABASE_SCHEMA}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(
        Integer,
        ForeignKey(f"{settings.DATABASE_SCHEMA}.kb_services.id", ondelete="CASCADE"),
        nullable=False
    )

    # Element identification
    element_type = Column(String(50), nullable=False)
    element_name = Column(String(255), nullable=False)
    qualified_name = Column(String(500), nullable=True)  # Full qualified name

    # Source location
    file_path = Column(String(500), nullable=True)
    line_number = Column(Integer, nullable=True)

    # Content
    signature = Column(Text, nullable=True)  # Method/class signature
    description = Column(Text, nullable=True)  # Extracted or generated description
    content_hash = Column(String(64), nullable=True)  # SHA256 for change detection

    # Vector embedding for semantic search
    content_embedding = Column(Vector(768), nullable=True)

    # Type-specific metadata (flexible JSONB)
    # Examples:
    # - endpoint: {"http_method": "POST", "path": "/api/v1/...", "request_dto": "...", "response_dto": "..."}
    # - exception: {"error_code": "...", "http_status": 400, "message_template": "..."}
    # - service_call: {"target_service": "...", "feign_client": "...", "method": "..."}
    # - log_pattern: {"log_level": "INFO", "pattern": "...", "fields": [...]}
    extra = Column('metadata', JSONB, nullable=False, default=dict)

    # Status and timestamps
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to service
    service = relationship("KBService", back_populates="elements")

    def __repr__(self) -> str:
        return f"<KBElement(type={self.element_type}, name={self.element_name})>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "service_id": self.service_id,
            "element_type": self.element_type,
            "element_name": self.element_name,
            "qualified_name": self.qualified_name,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "signature": self.signature,
            "description": self.description,
            "metadata": self.extra,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_embedding_text(self) -> str:
        """Generate text representation for embedding."""
        parts = [
            f"Type: {self.element_type}",
            f"Name: {self.element_name}",
        ]
        if self.signature:
            parts.append(f"Signature: {self.signature}")
        if self.description:
            parts.append(f"Description: {self.description}")
        if self.extra:
            # Include relevant metadata fields
            if "path" in self.extra:
                parts.append(f"Path: {self.extra['path']}")
            if "http_method" in self.extra:
                parts.append(f"HTTP Method: {self.extra['http_method']}")
            if "error_code" in self.extra:
                parts.append(f"Error Code: {self.extra['error_code']}")
            if "target_service" in self.extra:
                parts.append(f"Calls: {self.extra['target_service']}")
        return " | ".join(parts)


class KBIngestionRun(Base):
    """
    Tracks knowledge base ingestion runs.

    Used for auditing, debugging, and monitoring the ingestion process.
    """
    __tablename__ = "kb_ingestion_runs"
    __table_args__ = (
        Index("idx_kb_ingestion_runs_status", "status"),
        Index("idx_kb_ingestion_runs_started", "started_at"),
        {"schema": settings.DATABASE_SCHEMA}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_type = Column(String(50), nullable=False)  # 'full', 'incremental', 'service'
    status = Column(String(50), nullable=False)  # 'running', 'completed', 'failed'
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # Statistics
    services_processed = Column(Integer, nullable=False, default=0)
    elements_created = Column(Integer, nullable=False, default=0)
    elements_updated = Column(Integer, nullable=False, default=0)
    elements_deleted = Column(Integer, nullable=False, default=0)
    embeddings_generated = Column(Integer, nullable=False, default=0)

    # Error tracking
    errors = Column(JSONB, nullable=False, default=list)

    # Additional metadata (using 'extra' to avoid SQLAlchemy reserved 'metadata')
    extra = Column('metadata', JSONB, nullable=False, default=dict)

    def __repr__(self) -> str:
        return f"<KBIngestionRun(id={self.id}, type={self.run_type}, status={self.status})>"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "run_type": self.run_type,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "services_processed": self.services_processed,
            "elements_created": self.elements_created,
            "elements_updated": self.elements_updated,
            "elements_deleted": self.elements_deleted,
            "embeddings_generated": self.embeddings_generated,
            "errors": self.errors,
            "metadata": self.extra,
        }
