# app/knowledge_base/retrieval/rag_service.py
"""
RAG retrieval service for querying the knowledge base.

Provides:
- Vector similarity search using pgvector
- Filtering by element type, service, etc.
- Context formatting for LLM prompts
"""

import logging
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

from sqlalchemy import text

from app.config import settings
from app.db.session import get_db_session
from app.knowledge_base.embedding.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """A single retrieval result from the knowledge base."""

    element_id: int
    service_code: str
    service_name: str
    element_type: str
    element_name: str
    qualified_name: Optional[str]
    signature: Optional[str]
    description: Optional[str]
    metadata: Dict[str, Any]
    similarity: float

    def to_context_string(self) -> str:
        """Convert to a string suitable for LLM context."""
        parts = [f"[{self.service_name}] {self.element_type}: {self.element_name}"]

        if self.signature:
            parts.append(f"  Signature: {self.signature}")
        if self.description:
            parts.append(f"  Description: {self.description}")
        if self.metadata:
            if 'path' in self.metadata:
                parts.append(f"  Path: {self.metadata['path']}")
            if 'http_method' in self.metadata:
                parts.append(f"  HTTP: {self.metadata['http_method']}")
            if 'error_code' in self.metadata:
                parts.append(f"  Error Code: {self.metadata['error_code']}")
            if 'target_service' in self.metadata:
                parts.append(f"  Calls: {self.metadata['target_service']}")
            if 'log_level' in self.metadata:
                parts.append(f"  Log Level: {self.metadata['log_level']}")

        return "\n".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'element_id': self.element_id,
            'service_code': self.service_code,
            'service_name': self.service_name,
            'element_type': self.element_type,
            'element_name': self.element_name,
            'qualified_name': self.qualified_name,
            'signature': self.signature,
            'description': self.description,
            'metadata': self.metadata,
            'similarity': self.similarity,
        }


class RAGService:
    """
    Service for RAG-based knowledge retrieval.

    Uses pgvector for vector similarity search.
    """

    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.top_k = settings.KB_RETRIEVAL_TOP_K
        self.min_similarity = settings.KB_RETRIEVAL_MIN_SIMILARITY
        self.schema = settings.DATABASE_SCHEMA

    def retrieve(
        self,
        query: str,
        element_types: Optional[List[str]] = None,
        services: Optional[List[str]] = None,
        top_k: Optional[int] = None,
        min_similarity: Optional[float] = None,
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant knowledge base entries for a query.

        Args:
            query: Natural language query
            element_types: Filter by element types (endpoint, exception, etc.)
            services: Filter by service codes
            top_k: Number of results to return
            min_similarity: Minimum cosine similarity threshold

        Returns:
            List of RetrievalResult sorted by similarity (highest first)
        """
        top_k = top_k or self.top_k
        min_similarity = min_similarity or self.min_similarity

        # Generate query embedding
        query_embedding = self.embedding_service.embed_for_query(query)
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        # Build SQL query with filters
        filters = ["e.is_active = TRUE", "s.is_active = TRUE"]
        params: Dict[str, Any] = {
            'min_sim': min_similarity,
            'limit': top_k,
        }

        if element_types:
            filters.append("e.element_type = ANY(:element_types)")
            params['element_types'] = element_types

        if services:
            filters.append("s.service_code = ANY(:services)")
            params['services'] = services

        where_clause = " AND ".join(filters)

        # pgvector uses <=> for cosine distance (1 - similarity)
        # We compute similarity as 1 - distance
        sql = text(f"""
            SELECT
                e.id,
                s.service_code,
                s.service_name,
                e.element_type,
                e.element_name,
                e.qualified_name,
                e.signature,
                e.description,
                e.metadata,
                1 - (e.content_embedding <=> '{embedding_str}'::vector) as similarity
            FROM {self.schema}.kb_elements e
            JOIN {self.schema}.kb_services s ON e.service_id = s.id
            WHERE {where_clause}
                AND e.content_embedding IS NOT NULL
                AND 1 - (e.content_embedding <=> '{embedding_str}'::vector) >= :min_sim
            ORDER BY e.content_embedding <=> '{embedding_str}'::vector
            LIMIT :limit
        """)

        with get_db_session() as db:
            result = db.execute(sql, params)
            rows = result.fetchall()

        return [
            RetrievalResult(
                element_id=row.id,
                service_code=row.service_code,
                service_name=row.service_name,
                element_type=row.element_type,
                element_name=row.element_name,
                qualified_name=row.qualified_name,
                signature=row.signature,
                description=row.description,
                metadata=row.metadata or {},
                similarity=float(row.similarity),
            )
            for row in rows
        ]

    def retrieve_for_context(
        self,
        query: str,
        domain: Optional[str] = None,
        query_keys: Optional[List[str]] = None,
        max_context_chars: int = 4000,
    ) -> str:
        """
        Retrieve and format knowledge for LLM context injection.

        Args:
            query: User query
            domain: Domain hint (e.g., 'payment', 'mfs')
            query_keys: Specific keywords from extracted parameters
            max_context_chars: Maximum characters for context

        Returns:
            Formatted context string for LLM
        """
        # Build enhanced query from domain and keys
        enhanced_query = query
        if domain:
            enhanced_query = f"{domain} {enhanced_query}"
        if query_keys:
            enhanced_query = f"{enhanced_query} {' '.join(query_keys)}"

        results = self.retrieve(enhanced_query, top_k=20)

        if not results:
            return ""

        # Format results within character limit
        context_parts = ["RELEVANT SYSTEM KNOWLEDGE:"]
        current_length = len(context_parts[0])

        for result in results:
            entry = result.to_context_string()
            entry_length = len(entry) + 2  # +2 for newlines

            if current_length + entry_length > max_context_chars:
                break

            context_parts.append(entry)
            current_length += entry_length

        return "\n\n".join(context_parts)

    def retrieve_error_patterns(self, error_message: str) -> List[RetrievalResult]:
        """
        Specialized retrieval for error messages.

        Args:
            error_message: The error message to search for

        Returns:
            Matching exception and error code elements
        """
        return self.retrieve(
            query=error_message,
            element_types=['exception', 'error_code'],
            top_k=5
        )

    def retrieve_endpoints(self, description: str) -> List[RetrievalResult]:
        """
        Retrieve API endpoints matching a description.

        Args:
            description: Description of the endpoint functionality

        Returns:
            Matching endpoint elements
        """
        return self.retrieve(
            query=description,
            element_types=['endpoint'],
            top_k=10
        )

    def retrieve_service_calls(self, service_name: str) -> List[RetrievalResult]:
        """
        Retrieve inter-service calls related to a service.

        Args:
            service_name: Name of the service

        Returns:
            Matching service call elements
        """
        return self.retrieve(
            query=f"service call {service_name}",
            element_types=['service_call'],
            top_k=15
        )

    def retrieve_log_patterns(self, log_message: str) -> List[RetrievalResult]:
        """
        Find log patterns matching a log message.

        Args:
            log_message: The log message to search for

        Returns:
            Matching log pattern elements
        """
        return self.retrieve(
            query=log_message,
            element_types=['log_pattern'],
            top_k=10
        )

    def get_service_overview(self, service_code: str) -> Optional[Dict[str, Any]]:
        """
        Get an overview of a service from the knowledge base.

        Args:
            service_code: The service code to look up

        Returns:
            Service information or None if not found
        """
        sql = text(f"""
            SELECT
                s.id,
                s.service_code,
                s.service_name,
                s.service_type,
                s.base_package,
                s.description,
                s.api_endpoints_count,
                s.classes_count,
                s.error_codes_count,
                s.metadata,
                s.indexed_at
            FROM {self.schema}.kb_services s
            WHERE s.service_code = :service_code
                AND s.is_active = TRUE
        """)

        with get_db_session() as db:
            result = db.execute(sql, {'service_code': service_code})
            row = result.fetchone()

        if not row:
            return None

        return {
            'id': row.id,
            'service_code': row.service_code,
            'service_name': row.service_name,
            'service_type': row.service_type,
            'base_package': row.base_package,
            'description': row.description,
            'api_endpoints_count': row.api_endpoints_count,
            'classes_count': row.classes_count,
            'error_codes_count': row.error_codes_count,
            'metadata': row.metadata,
            'indexed_at': row.indexed_at.isoformat() if row.indexed_at else None,
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get knowledge base statistics.

        Returns:
            Statistics dictionary
        """
        with get_db_session() as db:
            # Get service count
            services_result = db.execute(text(f"""
                SELECT COUNT(*) as count
                FROM {self.schema}.kb_services
                WHERE is_active = TRUE
            """))
            services_count = services_result.fetchone().count

            # Get element count
            elements_result = db.execute(text(f"""
                SELECT COUNT(*) as count
                FROM {self.schema}.kb_elements
                WHERE is_active = TRUE
            """))
            elements_count = elements_result.fetchone().count

            # Get counts by element type
            by_type_result = db.execute(text(f"""
                SELECT element_type, COUNT(*) as count
                FROM {self.schema}.kb_elements
                WHERE is_active = TRUE
                GROUP BY element_type
                ORDER BY count DESC
            """))
            by_type = {row.element_type: row.count for row in by_type_result.fetchall()}

            # Get last ingestion run
            last_run_result = db.execute(text(f"""
                SELECT *
                FROM {self.schema}.kb_ingestion_runs
                ORDER BY started_at DESC
                LIMIT 1
            """))
            last_run = last_run_result.fetchone()

        return {
            'services_count': services_count,
            'elements_count': elements_count,
            'by_element_type': by_type,
            'last_ingestion': {
                'id': last_run.id,
                'type': last_run.run_type,
                'status': last_run.status,
                'started_at': last_run.started_at.isoformat() if last_run.started_at else None,
                'completed_at': last_run.completed_at.isoformat() if last_run.completed_at else None,
            } if last_run else None,
        }


# Singleton instance
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get or create the singleton RAG service."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
