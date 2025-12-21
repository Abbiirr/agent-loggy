# app/knowledge_base/embedding/embedding_service.py
"""
Embedding service for generating text embeddings using Ollama.

This service provides:
- Single text embedding generation
- Batch embedding for multiple texts
- In-memory caching with TTL
- Query-optimized embeddings with prefixes
"""

import hashlib
import logging
from dataclasses import dataclass
from typing import List, Optional, Dict
from functools import lru_cache

from ollama import Client

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    text: str
    embedding: List[float]
    model: str
    dimensions: int
    cached: bool = False


class EmbeddingCache:
    """Simple TTL-based embedding cache."""

    def __init__(self, max_entries: int = 10000, ttl_seconds: int = 86400):
        self._cache: Dict[str, tuple] = {}  # key -> (embedding, timestamp)
        self._max_entries = max_entries
        self._ttl_seconds = ttl_seconds

    def _cache_key(self, text: str, model: str) -> str:
        """Generate cache key from text and model."""
        combined = f"{model}:{text}"
        return hashlib.sha256(combined.encode('utf-8')).hexdigest()[:32]

    def get(self, text: str, model: str) -> Optional[List[float]]:
        """Get embedding from cache if exists and not expired."""
        import time
        key = self._cache_key(text, model)
        if key in self._cache:
            embedding, timestamp = self._cache[key]
            if time.time() - timestamp < self._ttl_seconds:
                return embedding
            else:
                # Expired, remove it
                del self._cache[key]
        return None

    def set(self, text: str, model: str, embedding: List[float]) -> None:
        """Store embedding in cache."""
        import time

        # Evict oldest entries if at capacity
        if len(self._cache) >= self._max_entries:
            # Remove 10% oldest entries
            items = sorted(self._cache.items(), key=lambda x: x[1][1])
            for key, _ in items[:len(items) // 10]:
                del self._cache[key]

        key = self._cache_key(text, model)
        self._cache[key] = (embedding, time.time())


class EmbeddingService:
    """
    Service for generating text embeddings using Ollama.

    Uses the nomic-embed-text model by default (768 dimensions).
    Supports caching to avoid redundant embedding generation.
    """

    def __init__(
        self,
        model: Optional[str] = None,
        ollama_host: Optional[str] = None,
    ):
        self.model = model or settings.KB_EMBEDDING_MODEL
        self.ollama_host = ollama_host or settings.OLLAMA_HOST
        self._client: Optional[Client] = None

        # Initialize cache if enabled
        if settings.KB_EMBEDDING_CACHE_ENABLED:
            self._cache = EmbeddingCache(
                max_entries=10000,
                ttl_seconds=settings.KB_EMBEDDING_CACHE_TTL_SECONDS
            )
        else:
            self._cache = None

    def _get_client(self) -> Client:
        """Lazy-load Ollama client."""
        if self._client is None:
            self._client = Client(host=self.ollama_host)
        return self._client

    def embed_text(self, text: str, use_cache: bool = True) -> EmbeddingResult:
        """
        Generate embedding for a single text.

        Args:
            text: The text to embed
            use_cache: Whether to use caching (default: True)

        Returns:
            EmbeddingResult with the embedding vector
        """
        # Check cache first
        if use_cache and self._cache is not None:
            cached_embedding = self._cache.get(text, self.model)
            if cached_embedding is not None:
                logger.debug(f"Embedding cache hit for text (len={len(text)})")
                return EmbeddingResult(
                    text=text,
                    embedding=cached_embedding,
                    model=self.model,
                    dimensions=len(cached_embedding),
                    cached=True
                )

        # Generate embedding via Ollama
        client = self._get_client()
        try:
            response = client.embeddings(
                model=self.model,
                prompt=text
            )
            embedding = response['embedding']

            # Cache the result
            if use_cache and self._cache is not None:
                self._cache.set(text, self.model, embedding)

            logger.debug(f"Generated embedding for text (len={len(text)}), dims={len(embedding)}")

            return EmbeddingResult(
                text=text,
                embedding=embedding,
                model=self.model,
                dimensions=len(embedding),
                cached=False
            )

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise

    def embed_batch(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        use_cache: bool = True,
    ) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once (for logging)
            use_cache: Whether to use caching

        Returns:
            List of EmbeddingResult objects
        """
        batch_size = batch_size or settings.KB_EMBEDDING_BATCH_SIZE
        results = []
        total = len(texts)
        cache_hits = 0

        for i, text in enumerate(texts):
            result = self.embed_text(text, use_cache=use_cache)
            results.append(result)
            if result.cached:
                cache_hits += 1

            # Log progress every batch_size items
            if (i + 1) % batch_size == 0:
                logger.info(f"Embedded {i + 1}/{total} texts (cache hits: {cache_hits})")

        logger.info(f"Batch embedding complete: {total} texts, {cache_hits} cache hits")
        return results

    def embed_for_query(self, query: str) -> List[float]:
        """
        Generate embedding optimized for search queries.

        Adds a prefix to improve retrieval quality with some embedding models.

        Args:
            query: The search query

        Returns:
            Embedding vector as list of floats
        """
        # For nomic-embed-text, adding "search_query:" prefix can improve retrieval
        prefixed_query = f"search_query: {query}"
        result = self.embed_text(prefixed_query, use_cache=True)
        return result.embedding

    def embed_for_document(self, document: str) -> List[float]:
        """
        Generate embedding optimized for documents.

        Args:
            document: The document text

        Returns:
            Embedding vector as list of floats
        """
        # For nomic-embed-text, adding "search_document:" prefix can improve retrieval
        prefixed_doc = f"search_document: {document}"
        result = self.embed_text(prefixed_doc, use_cache=True)
        return result.embedding


# Singleton instance
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the singleton embedding service."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
