# Phase 3: RAG Pipeline Plan

## Executive Summary

This phase implements a production-ready RAG (Retrieval-Augmented Generation) pipeline for agent-loggy. The system will use **late chunking** for log context preservation, **pgvector** for vector storage, **hybrid search** combining BM25 keyword matching with semantic similarity, and **reranking** for improved relevance. This enables intelligent log analysis where the LLM has access to contextually relevant documentation and historical patterns.

**Timeline**: Week 3-5
**Dependencies**: Phase 1 (Database), Phase 2 (Configuration)
**Blocking**: Phase 5 (Testing requires RAG metrics)

---

## Current State Analysis

### What Exists
| Component | Location | Status |
|-----------|----------|--------|
| RAGContextManager | `app/agents/verify_agent.py:57` | CSV-based, keyword matching only |
| Context Rules | `app/app_settings/context_rules.csv` | Static, no embeddings |
| Log Search | `app/tools/log_searcher.py` | Regex-based search |
| Embeddings | None | No embedding support |
| Vector Storage | pgvector enabled in DB | Unused |

### Current RAGContextManager (verify_agent.py:57-200)
```python
class RAGContextManager:
    """CSV-based rule matching - NO semantic search"""

    def get_relevant_rules(self, domain, query_keys):
        # Simple string matching
        for rule in self.rules:
            if rule.context.lower() == domain.lower():
                relevant_rules.append(rule)
        return relevant_rules
```

### Problems with Current Approach
1. **No Semantic Understanding**: Pure keyword matching misses semantic similarity
2. **No Chunking**: Entire documents processed as single units
3. **No Embeddings**: Cannot find semantically similar content
4. **No Hybrid Search**: Missing BM25 for exact matches
5. **No Reranking**: First retrieval is final retrieval
6. **No Context Preservation**: Log entries lose surrounding context

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RAG Pipeline Overview                              │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                         INDEXING PIPELINE (Offline)                          │
│                                                                              │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────┐    ┌─────────────┐ │
│  │ Log Files / │───▶│  Chunker     │───▶│  Embedder   │───▶│  pgvector   │ │
│  │ Documents   │    │  (Late/      │    │  (OpenAI/   │    │  Storage    │ │
│  │             │    │   Contextual)│    │   Local)    │    │             │ │
│  └─────────────┘    └──────────────┘    └─────────────┘    └─────────────┘ │
│                            │                                                 │
│                            ▼                                                 │
│                     ┌──────────────┐    ┌─────────────┐                     │
│                     │  BM25 Index  │───▶│  PostgreSQL │                     │
│                     │  (Keywords)  │    │  tsvector   │                     │
│                     └──────────────┘    └─────────────┘                     │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                         RETRIEVAL PIPELINE (Online)                          │
│                                                                              │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────────────────┐ │
│  │ User Query  │───▶│  Query       │───▶│  Hybrid Search                  │ │
│  │             │    │  Transformer │    │  ┌────────────┐ ┌────────────┐  │ │
│  └─────────────┘    └──────────────┘    │  │ BM25       │ │ Vector     │  │ │
│                            │            │  │ (Keywords) │ │ (Semantic) │  │ │
│                            │            │  └─────┬──────┘ └─────┬──────┘  │ │
│                            │            │        └──────┬───────┘         │ │
│                            │            │               ▼                 │ │
│                            │            │        ┌────────────┐          │ │
│                            │            │        │ RRF Fusion │          │ │
│                            │            │        └─────┬──────┘          │ │
│                            │            └──────────────┼──────────────────┘ │
│                            │                           │                    │
│                            │                           ▼                    │
│                            │            ┌──────────────────────────┐       │
│                            │            │  Reranker (Cohere/BGE)   │       │
│                            │            │  Top 50 → Top 10         │       │
│                            │            └───────────┬──────────────┘       │
│                            │                        │                       │
│                            │                        ▼                       │
│                            │            ┌──────────────────────────┐       │
│                            │            │  Context Builder          │       │
│                            │            │  (Assemble LLM Context)  │       │
│                            │            └───────────┬──────────────┘       │
│                            │                        │                       │
│                            ▼                        ▼                       │
│                     ┌──────────────────────────────────────────────┐       │
│                     │           LLM Generation                      │       │
│                     │  Query + Retrieved Context → Response         │       │
│                     └──────────────────────────────────────────────┘       │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema (RAG Tables)

### File: `app/db/models_rag.py`

```python
"""
ORM Models for RAG pipeline storage.
"""

from datetime import datetime
from typing import Optional, List, Any
from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, Float,
    ForeignKey, UniqueConstraint, Index, func, Computed
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, ARRAY, TSVECTOR
from pgvector.sqlalchemy import Vector

from app.db.base import Base


class DocumentChunk(Base):
    """
    Chunked document segments for RAG retrieval.
    Supports late chunking with full document context embeddings.
    """
    __tablename__ = "document_chunks"
    __table_args__ = (
        Index('idx_chunks_source', 'source_type', 'source_id'),
        Index('idx_chunks_embedding', 'embedding', postgresql_using='ivfflat'),
        Index('idx_chunks_tsv', 'tsv_content', postgresql_using='gin'),
        {"schema": "agent_loggy"}
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # Source tracking
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # 'log', 'doc', 'rule'
    source_id: Mapped[str] = mapped_column(String(255), nullable=False)   # file path or ID
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)  # SHA256 of source

    # Chunk content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    total_chunks: Mapped[int] = mapped_column(Integer, nullable=False)

    # Context (for contextual chunking)
    context_prefix: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Embeddings (384 for all-MiniLM, 1536 for OpenAI, 1024 for Cohere)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector(1536), nullable=True)

    # Full-text search vector
    tsv_content: Mapped[Any] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', content)", persisted=True)
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )

    def __repr__(self):
        return f"<DocumentChunk(source={self.source_id}, idx={self.chunk_index})>"


class LogEmbedding(Base):
    """
    Embeddings for log trace summaries.
    Used for finding similar past incidents.
    """
    __tablename__ = "log_embeddings"
    __table_args__ = (
        UniqueConstraint('trace_id', 'chunk_index', name='uq_log_embedding_trace_chunk'),
        Index('idx_log_embeddings_trace', 'trace_id'),
        Index('idx_log_embeddings_vector', 'embedding', postgresql_using='ivfflat'),
        {"schema": "agent_loggy"}
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    trace_id: Mapped[str] = mapped_column(String(128), nullable=False)

    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Embedding
    embedding: Mapped[Optional[Any]] = mapped_column(Vector(1536), nullable=True)

    # Metadata
    services: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    error_types: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    timestamp_start: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    timestamp_end: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    total_entries: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Analysis results
    analysis_result: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())

    def __repr__(self):
        return f"<LogEmbedding(trace_id={self.trace_id})>"


class ContextRuleEmbedding(Base):
    """
    Embeddings for context rules to enable semantic rule matching.
    """
    __tablename__ = "context_rule_embeddings"
    __table_args__ = (
        Index('idx_context_rule_emb_vector', 'embedding', postgresql_using='ivfflat'),
        {"schema": "agent_loggy"}
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('agent_loggy.context_rules.id'),
        nullable=False
    )

    # Combined text for embedding
    combined_text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector(1536), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())

    def __repr__(self):
        return f"<ContextRuleEmbedding(rule_id={self.rule_id})>"


class SearchHistory(Base):
    """
    Track search queries for analytics and improvement.
    """
    __tablename__ = "search_history"
    __table_args__ = (
        Index('idx_search_history_timestamp', 'created_at'),
        {"schema": "agent_loggy"}
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    query_embedding: Mapped[Optional[Any]] = mapped_column(Vector(1536), nullable=True)

    # Search parameters
    search_type: Mapped[str] = mapped_column(String(20), nullable=False)  # 'hybrid', 'vector', 'bm25'
    top_k: Mapped[int] = mapped_column(Integer, default=10)

    # Results
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    result_ids: Mapped[Optional[List[int]]] = mapped_column(ARRAY(Integer), nullable=True)

    # Performance
    latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rerank_latency_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Feedback (optional)
    user_feedback: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # 'helpful', 'not_helpful'

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())

    def __repr__(self):
        return f"<SearchHistory(query={self.query[:50]}...)>"
```

---

## Chunking Strategies

### File: `app/rag/chunkers.py`

```python
"""
Chunking strategies for the RAG pipeline.

Implements:
- Late chunking (embed full doc, then chunk at embedding level)
- Contextual chunking (prepend LLM-generated context)
- Semantic chunking (split on topic boundaries)
- Fixed-size chunking (baseline)
"""

import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

import tiktoken
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a document chunk."""
    content: str
    index: int
    total_chunks: int
    source_id: str
    source_hash: str
    context_prefix: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BaseChunker(ABC):
    """Abstract base class for chunkers."""

    def __init__(self, chunk_size: int = 512, chunk_overlap: int = 50):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.tokenizer.encode(text))

    def _hash_content(self, content: str) -> str:
        """Generate SHA256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()

    @abstractmethod
    def chunk(self, text: str, source_id: str, metadata: Optional[Dict] = None) -> List[Chunk]:
        """Split text into chunks."""
        pass


class FixedSizeChunker(BaseChunker):
    """
    Fixed-size chunking with token-based splitting.
    Baseline approach for comparison.
    """

    def chunk(self, text: str, source_id: str, metadata: Optional[Dict] = None) -> List[Chunk]:
        """Split text into fixed-size chunks with overlap."""
        tokens = self.tokenizer.encode(text)
        source_hash = self._hash_content(text)
        chunks = []

        start = 0
        chunk_index = 0

        while start < len(tokens):
            end = min(start + self.chunk_size, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self.tokenizer.decode(chunk_tokens)

            chunks.append(Chunk(
                content=chunk_text,
                index=chunk_index,
                total_chunks=0,  # Updated after loop
                source_id=source_id,
                source_hash=source_hash,
                metadata=metadata
            ))

            chunk_index += 1
            start = end - self.chunk_overlap

            if start >= len(tokens):
                break

        # Update total_chunks
        for chunk in chunks:
            chunk.total_chunks = len(chunks)

        return chunks


class LateChunker(BaseChunker):
    """
    Late chunking: embed full document, then chunk at embedding level.

    Preserves document-wide context in embeddings by computing
    token embeddings with full document attention before chunking.

    Reference: Jina AI's late chunking approach
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        model_name: str = "jinaai/jina-embeddings-v3"
    ):
        super().__init__(chunk_size, chunk_overlap)
        self.model = SentenceTransformer(model_name, trust_remote_code=True)
        self.model.max_seq_length = 8192  # Long context support

    def chunk(self, text: str, source_id: str, metadata: Optional[Dict] = None) -> List[Chunk]:
        """
        Create chunks with late chunking strategy.

        The embedding computation happens in the embedding phase,
        where full document attention is used before mean pooling per chunk.
        """
        # For late chunking, we still create text chunks
        # but the embedding phase handles the late pooling
        base_chunker = FixedSizeChunker(self.chunk_size, self.chunk_overlap)
        chunks = base_chunker.chunk(text, source_id, metadata)

        # Mark chunks for late chunking processing
        for chunk in chunks:
            if chunk.metadata is None:
                chunk.metadata = {}
            chunk.metadata["chunking_strategy"] = "late"
            chunk.metadata["full_document_length"] = len(text)

        return chunks

    def compute_late_embeddings(self, text: str, chunks: List[Chunk]) -> List[List[float]]:
        """
        Compute embeddings using late chunking strategy.

        This embeds the full document and then performs mean pooling
        over the token ranges corresponding to each chunk.
        """
        # Get token embeddings for full document
        inputs = self.model.tokenize([text])
        outputs = self.model.forward(inputs)
        token_embeddings = outputs["token_embeddings"][0]  # [seq_len, dim]

        # Tokenize chunks to get boundaries
        chunk_embeddings = []

        current_position = 0
        for chunk in chunks:
            chunk_tokens = self.model.tokenize([chunk.content])
            chunk_length = chunk_tokens["attention_mask"].sum().item()

            # Mean pool over chunk's token range
            start_idx = current_position
            end_idx = min(start_idx + chunk_length, token_embeddings.shape[0])

            chunk_emb = token_embeddings[start_idx:end_idx].mean(dim=0)
            chunk_embeddings.append(chunk_emb.tolist())

            # Account for overlap
            current_position = end_idx - self.chunk_overlap

        return chunk_embeddings


class ContextualChunker(BaseChunker):
    """
    Contextual chunking: prepend LLM-generated context to each chunk.

    Uses an LLM to generate a short context prefix that explains
    where the chunk fits in the larger document.

    Reference: Anthropic's contextual retrieval approach
    """

    CONTEXT_PROMPT = """<document>
{document}
</document>

Here is the chunk we want to situate within the whole document:
<chunk>
{chunk}
</chunk>

Please give a short succinct context to situate this chunk within the overall document for the purposes of improving search retrieval of the chunk. Answer only with the succinct context and nothing else."""

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        llm_client: Any = None,
        max_context_tokens: int = 100
    ):
        super().__init__(chunk_size, chunk_overlap)
        self.llm_client = llm_client
        self.max_context_tokens = max_context_tokens

    def chunk(self, text: str, source_id: str, metadata: Optional[Dict] = None) -> List[Chunk]:
        """Create chunks with contextual prefixes."""
        # First, create base chunks
        base_chunker = FixedSizeChunker(self.chunk_size, self.chunk_overlap)
        chunks = base_chunker.chunk(text, source_id, metadata)

        # Generate context for each chunk
        for chunk in chunks:
            context = self._generate_context(text, chunk.content)
            chunk.context_prefix = context

            if chunk.metadata is None:
                chunk.metadata = {}
            chunk.metadata["chunking_strategy"] = "contextual"

        return chunks

    def _generate_context(self, document: str, chunk: str) -> str:
        """Generate context prefix using LLM."""
        if self.llm_client is None:
            return ""

        prompt = self.CONTEXT_PROMPT.format(document=document, chunk=chunk)

        try:
            response = self.llm_client.generate(
                model="qwen3:14b",
                prompt=prompt,
                options={"num_predict": self.max_context_tokens}
            )
            return response["response"].strip()
        except Exception as e:
            logger.warning(f"Context generation failed: {e}")
            return ""


class SemanticChunker(BaseChunker):
    """
    Semantic chunking: split on topic/semantic boundaries.

    Uses embedding similarity between consecutive sentences
    to detect natural topic transitions.
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        breakpoint_percentile: float = 95.0,
        model_name: str = "all-MiniLM-L6-v2"
    ):
        super().__init__(chunk_size, chunk_overlap)
        self.breakpoint_percentile = breakpoint_percentile
        self.model = SentenceTransformer(model_name)

    def chunk(self, text: str, source_id: str, metadata: Optional[Dict] = None) -> List[Chunk]:
        """Split text at semantic boundaries."""
        import numpy as np
        from nltk import sent_tokenize

        # Split into sentences
        sentences = sent_tokenize(text)

        if len(sentences) <= 1:
            return [Chunk(
                content=text,
                index=0,
                total_chunks=1,
                source_id=source_id,
                source_hash=self._hash_content(text),
                metadata=metadata
            )]

        # Embed sentences
        embeddings = self.model.encode(sentences)

        # Compute similarities between consecutive sentences
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = np.dot(embeddings[i], embeddings[i + 1]) / (
                np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i + 1])
            )
            similarities.append(sim)

        # Find breakpoints (low similarity = topic change)
        threshold = np.percentile(1 - np.array(similarities), self.breakpoint_percentile)
        breakpoints = [i for i, sim in enumerate(similarities) if (1 - sim) > threshold]

        # Create chunks at breakpoints
        chunks = []
        start = 0
        source_hash = self._hash_content(text)

        for bp in breakpoints:
            chunk_text = " ".join(sentences[start:bp + 1])
            chunks.append(Chunk(
                content=chunk_text,
                index=len(chunks),
                total_chunks=0,
                source_id=source_id,
                source_hash=source_hash,
                metadata={**(metadata or {}), "chunking_strategy": "semantic"}
            ))
            start = bp + 1

        # Add remaining sentences
        if start < len(sentences):
            chunk_text = " ".join(sentences[start:])
            chunks.append(Chunk(
                content=chunk_text,
                index=len(chunks),
                total_chunks=0,
                source_id=source_id,
                source_hash=source_hash,
                metadata={**(metadata or {}), "chunking_strategy": "semantic"}
            ))

        # Update total_chunks
        for chunk in chunks:
            chunk.total_chunks = len(chunks)

        return chunks


class LogChunker(BaseChunker):
    """
    Specialized chunker for log files.

    Preserves log entry integrity and groups related entries
    (e.g., stack traces, request/response pairs).
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        max_entries_per_chunk: int = 50
    ):
        super().__init__(chunk_size, chunk_overlap)
        self.max_entries_per_chunk = max_entries_per_chunk

    def chunk(self, text: str, source_id: str, metadata: Optional[Dict] = None) -> List[Chunk]:
        """Chunk log file preserving entry boundaries."""
        import re

        # Split on common log entry patterns
        # Matches: 2025-01-15 10:30:45 or [2025-01-15T10:30:45] or similar
        log_pattern = r'(?=(?:\d{4}-\d{2}-\d{2}[\sT]\d{2}:\d{2}:\d{2}|\[\d{4}-\d{2}-\d{2}))'

        entries = re.split(log_pattern, text)
        entries = [e.strip() for e in entries if e.strip()]

        if not entries:
            return [Chunk(
                content=text,
                index=0,
                total_chunks=1,
                source_id=source_id,
                source_hash=self._hash_content(text),
                metadata=metadata
            )]

        chunks = []
        current_chunk_entries = []
        current_token_count = 0
        source_hash = self._hash_content(text)

        for entry in entries:
            entry_tokens = self._count_tokens(entry)

            # Check if adding this entry would exceed limits
            if (current_token_count + entry_tokens > self.chunk_size or
                    len(current_chunk_entries) >= self.max_entries_per_chunk):

                if current_chunk_entries:
                    chunks.append(Chunk(
                        content="\n".join(current_chunk_entries),
                        index=len(chunks),
                        total_chunks=0,
                        source_id=source_id,
                        source_hash=source_hash,
                        metadata={
                            **(metadata or {}),
                            "chunking_strategy": "log",
                            "entry_count": len(current_chunk_entries)
                        }
                    ))

                # Start new chunk with overlap (last few entries)
                overlap_entries = current_chunk_entries[-2:] if len(current_chunk_entries) > 2 else []
                current_chunk_entries = overlap_entries + [entry]
                current_token_count = sum(self._count_tokens(e) for e in current_chunk_entries)
            else:
                current_chunk_entries.append(entry)
                current_token_count += entry_tokens

        # Add remaining entries
        if current_chunk_entries:
            chunks.append(Chunk(
                content="\n".join(current_chunk_entries),
                index=len(chunks),
                total_chunks=0,
                source_id=source_id,
                source_hash=source_hash,
                metadata={
                    **(metadata or {}),
                    "chunking_strategy": "log",
                    "entry_count": len(current_chunk_entries)
                }
            ))

        # Update total_chunks
        for chunk in chunks:
            chunk.total_chunks = len(chunks)

        return chunks


def get_chunker(strategy: str, **kwargs) -> BaseChunker:
    """Factory function to get appropriate chunker."""
    chunkers = {
        "fixed": FixedSizeChunker,
        "late": LateChunker,
        "contextual": ContextualChunker,
        "semantic": SemanticChunker,
        "log": LogChunker
    }

    chunker_class = chunkers.get(strategy, FixedSizeChunker)
    return chunker_class(**kwargs)
```

---

## Embedding Service

### File: `app/rag/embeddings.py`

```python
"""
Embedding service supporting multiple providers.

Providers:
- OpenAI (text-embedding-3-small, text-embedding-3-large)
- Local (sentence-transformers models)
- Jina (for late chunking)
- Cohere (embed-english-v3.0)
"""

import logging
from abc import ABC, abstractmethod
from typing import List, Optional, Union
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


class BaseEmbedder(ABC):
    """Abstract base class for embedding providers."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return embedding dimension."""
        pass

    @abstractmethod
    def embed(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """Embed one or more texts."""
        pass

    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        """Embed a query (may use different model/prefix)."""
        pass


class OpenAIEmbedder(BaseEmbedder):
    """OpenAI embedding provider."""

    MODELS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536
    }

    def __init__(self, model: str = "text-embedding-3-small", api_key: Optional[str] = None):
        from openai import OpenAI

        self.model = model
        self._dimension = self.MODELS.get(model, 1536)
        self.client = OpenAI(api_key=api_key or settings.get("OPENAI_API_KEY"))

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """Embed texts using OpenAI API."""
        if isinstance(texts, str):
            texts = [texts]

        # Batch in groups of 100 (API limit)
        all_embeddings = []
        batch_size = 100

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            response = self.client.embeddings.create(
                model=self.model,
                input=batch
            )
            batch_embeddings = [item.embedding for item in response.data]
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def embed_query(self, query: str) -> List[float]:
        """Embed a query."""
        return self.embed([query])[0]


class LocalEmbedder(BaseEmbedder):
    """Local embedding using sentence-transformers."""

    MODELS = {
        "all-MiniLM-L6-v2": 384,
        "all-mpnet-base-v2": 768,
        "bge-large-en-v1.5": 1024,
        "bge-m3": 1024
    }

    def __init__(self, model: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer

        self.model_name = model
        self._dimension = self.MODELS.get(model, 384)
        self.model = SentenceTransformer(model)

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """Embed texts locally."""
        if isinstance(texts, str):
            texts = [texts]

        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        """Embed a query."""
        return self.embed([query])[0]


class BGEEmbedder(BaseEmbedder):
    """
    BGE-M3 embedder supporting dense, sparse, and ColBERT representations.
    Best for hybrid search scenarios.
    """

    def __init__(self, model: str = "BAAI/bge-m3"):
        from FlagEmbedding import BGEM3FlagModel

        self.model = BGEM3FlagModel(model, use_fp16=True)
        self._dimension = 1024

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: Union[str, List[str]]) -> List[List[float]]:
        """Get dense embeddings."""
        if isinstance(texts, str):
            texts = [texts]

        output = self.model.encode(
            texts,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False
        )
        return output["dense_vecs"].tolist()

    def embed_query(self, query: str) -> List[float]:
        """Embed a query."""
        return self.embed([query])[0]

    def embed_hybrid(self, texts: Union[str, List[str]]) -> dict:
        """
        Get dense, sparse, and ColBERT representations.

        Returns:
            {
                "dense": List[List[float]],
                "sparse": List[Dict[int, float]],  # token_id -> weight
                "colbert": List[List[List[float]]]  # multi-vector
            }
        """
        if isinstance(texts, str):
            texts = [texts]

        output = self.model.encode(
            texts,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=True
        )

        return {
            "dense": output["dense_vecs"].tolist(),
            "sparse": output["lexical_weights"],
            "colbert": [v.tolist() for v in output["colbert_vecs"]]
        }


class JinaEmbedder(BaseEmbedder):
    """
    Jina AI embedder with late chunking support.
    """

    def __init__(self, model: str = "jinaai/jina-embeddings-v3", api_key: Optional[str] = None):
        self.model_name = model
        self._dimension = 1024
        self.api_key = api_key or settings.get("JINA_API_KEY")

        # Use local model if no API key
        if not self.api_key:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model, trust_remote_code=True)
            self.use_api = False
        else:
            self.use_api = True

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed(self, texts: Union[str, List[str]], late_chunking: bool = False) -> List[List[float]]:
        """
        Embed texts, optionally using late chunking.

        Args:
            texts: Texts to embed
            late_chunking: If True, uses Jina's late chunking API
        """
        if isinstance(texts, str):
            texts = [texts]

        if self.use_api:
            return self._embed_api(texts, late_chunking)
        else:
            return self._embed_local(texts)

    def _embed_api(self, texts: List[str], late_chunking: bool) -> List[List[float]]:
        """Embed using Jina API."""
        import requests

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "jina-embeddings-v3",
            "input": texts,
            "late_chunking": late_chunking
        }

        response = requests.post(
            "https://api.jina.ai/v1/embeddings",
            headers=headers,
            json=data
        )
        response.raise_for_status()

        result = response.json()
        return [item["embedding"] for item in result["data"]]

    def _embed_local(self, texts: List[str]) -> List[List[float]]:
        """Embed using local model."""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def embed_query(self, query: str) -> List[float]:
        """Embed a query."""
        return self.embed([query])[0]


def get_embedder(provider: str = "openai", **kwargs) -> BaseEmbedder:
    """Factory function to get appropriate embedder."""
    embedders = {
        "openai": OpenAIEmbedder,
        "local": LocalEmbedder,
        "bge": BGEEmbedder,
        "jina": JinaEmbedder
    }

    embedder_class = embedders.get(provider, OpenAIEmbedder)
    return embedder_class(**kwargs)
```

---

## Hybrid Search & Reranking

### File: `app/rag/retrieval.py`

```python
"""
Hybrid retrieval combining vector search with BM25 keyword matching.
Includes reranking for improved relevance.
"""

import logging
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
import numpy as np

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models_rag import DocumentChunk, LogEmbedding
from app.rag.embeddings import BaseEmbedder, get_embedder
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Search result with scores."""
    id: int
    content: str
    score: float
    source_type: str
    source_id: str
    metadata: Optional[Dict] = None
    vector_score: Optional[float] = None
    bm25_score: Optional[float] = None
    rerank_score: Optional[float] = None


class HybridRetriever:
    """
    Hybrid retrieval combining:
    - pgvector for semantic similarity (cosine distance)
    - PostgreSQL full-text search (tsvector/tsquery) for BM25-like keyword matching
    - Reciprocal Rank Fusion (RRF) for combining results
    """

    RRF_K = 60  # Constant for RRF formula

    def __init__(
        self,
        session: Session,
        embedder: Optional[BaseEmbedder] = None,
        vector_weight: float = 0.5,
        bm25_weight: float = 0.5
    ):
        self.session = session
        self.embedder = embedder or get_embedder()
        self.vector_weight = vector_weight
        self.bm25_weight = bm25_weight

    def search(
        self,
        query: str,
        top_k: int = 20,
        source_types: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Perform hybrid search combining vector and BM25.

        Args:
            query: Search query
            top_k: Number of results to return
            source_types: Filter by source type ('log', 'doc', 'rule')
            filters: Additional metadata filters

        Returns:
            List of SearchResult sorted by combined score
        """
        # Get results from both methods
        vector_results = self._vector_search(query, top_k * 2, source_types, filters)
        bm25_results = self._bm25_search(query, top_k * 2, source_types, filters)

        # Combine using RRF
        combined = self._rrf_fusion(vector_results, bm25_results)

        return combined[:top_k]

    def _vector_search(
        self,
        query: str,
        top_k: int,
        source_types: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[int, float]]:
        """
        Vector similarity search using pgvector.

        Returns: List of (chunk_id, score) tuples
        """
        # Embed query
        query_embedding = self.embedder.embed_query(query)

        # Build SQL query
        sql = """
        SELECT id, 1 - (embedding <=> :embedding) as score
        FROM agent_loggy.document_chunks
        WHERE embedding IS NOT NULL
        """

        params = {"embedding": str(query_embedding)}

        if source_types:
            sql += " AND source_type = ANY(:source_types)"
            params["source_types"] = source_types

        sql += " ORDER BY embedding <=> :embedding LIMIT :limit"
        params["limit"] = top_k

        result = self.session.execute(text(sql), params)
        return [(row.id, row.score) for row in result]

    def _bm25_search(
        self,
        query: str,
        top_k: int,
        source_types: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tuple[int, float]]:
        """
        BM25-style full-text search using PostgreSQL tsvector.

        Returns: List of (chunk_id, score) tuples
        """
        # Convert query to tsquery
        # Split on spaces, join with &
        query_terms = query.strip().split()
        tsquery = " & ".join(query_terms)

        sql = """
        SELECT id, ts_rank_cd(tsv_content, plainto_tsquery('english', :query)) as score
        FROM agent_loggy.document_chunks
        WHERE tsv_content @@ plainto_tsquery('english', :query)
        """

        params = {"query": query}

        if source_types:
            sql += " AND source_type = ANY(:source_types)"
            params["source_types"] = source_types

        sql += " ORDER BY score DESC LIMIT :limit"
        params["limit"] = top_k

        result = self.session.execute(text(sql), params)
        return [(row.id, row.score) for row in result]

    def _rrf_fusion(
        self,
        vector_results: List[Tuple[int, float]],
        bm25_results: List[Tuple[int, float]]
    ) -> List[SearchResult]:
        """
        Combine results using Reciprocal Rank Fusion (RRF).

        RRF_score = sum(1 / (k + rank_i)) for each result list
        """
        scores = {}
        vector_scores = {}
        bm25_scores = {}

        # Score from vector search
        for rank, (doc_id, score) in enumerate(vector_results):
            rrf_score = self.vector_weight * (1 / (self.RRF_K + rank + 1))
            scores[doc_id] = scores.get(doc_id, 0) + rrf_score
            vector_scores[doc_id] = score

        # Score from BM25 search
        for rank, (doc_id, score) in enumerate(bm25_results):
            rrf_score = self.bm25_weight * (1 / (self.RRF_K + rank + 1))
            scores[doc_id] = scores.get(doc_id, 0) + rrf_score
            bm25_scores[doc_id] = score

        # Sort by combined score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        # Fetch chunk details
        results = []
        for doc_id in sorted_ids:
            chunk = self.session.query(DocumentChunk).get(doc_id)
            if chunk:
                results.append(SearchResult(
                    id=chunk.id,
                    content=chunk.content,
                    score=scores[doc_id],
                    source_type=chunk.source_type,
                    source_id=chunk.source_id,
                    metadata=chunk.metadata,
                    vector_score=vector_scores.get(doc_id),
                    bm25_score=bm25_scores.get(doc_id)
                ))

        return results


class Reranker:
    """
    Reranks search results using cross-encoder models.

    Supported:
    - Cohere Rerank v3
    - BGE-reranker-v2-m3 (local)
    """

    def __init__(self, provider: str = "cohere", model: Optional[str] = None):
        self.provider = provider

        if provider == "cohere":
            import cohere
            self.client = cohere.Client(settings.get("COHERE_API_KEY"))
            self.model = model or "rerank-english-v3.0"
        else:
            from sentence_transformers import CrossEncoder
            self.model = CrossEncoder(model or "BAAI/bge-reranker-v2-m3")

    def rerank(
        self,
        query: str,
        results: List[SearchResult],
        top_k: int = 10
    ) -> List[SearchResult]:
        """
        Rerank results using cross-encoder.

        Args:
            query: Original search query
            results: Initial search results
            top_k: Number of results to return after reranking

        Returns:
            Reranked list of SearchResult
        """
        if not results:
            return []

        documents = [r.content for r in results]

        if self.provider == "cohere":
            return self._rerank_cohere(query, results, documents, top_k)
        else:
            return self._rerank_local(query, results, documents, top_k)

    def _rerank_cohere(
        self,
        query: str,
        results: List[SearchResult],
        documents: List[str],
        top_k: int
    ) -> List[SearchResult]:
        """Rerank using Cohere API."""
        response = self.client.rerank(
            model=self.model,
            query=query,
            documents=documents,
            top_n=top_k,
            return_documents=False
        )

        reranked = []
        for item in response.results:
            result = results[item.index]
            result.rerank_score = item.relevance_score
            reranked.append(result)

        return reranked

    def _rerank_local(
        self,
        query: str,
        results: List[SearchResult],
        documents: List[str],
        top_k: int
    ) -> List[SearchResult]:
        """Rerank using local cross-encoder."""
        pairs = [[query, doc] for doc in documents]
        scores = self.model.predict(pairs)

        # Sort by score
        scored_results = list(zip(results, scores))
        scored_results.sort(key=lambda x: x[1], reverse=True)

        reranked = []
        for result, score in scored_results[:top_k]:
            result.rerank_score = float(score)
            reranked.append(result)

        return reranked


class RAGPipeline:
    """
    Complete RAG pipeline combining retrieval and reranking.
    """

    def __init__(
        self,
        session: Session,
        embedder: Optional[BaseEmbedder] = None,
        reranker: Optional[Reranker] = None,
        retrieval_top_k: int = 50,
        final_top_k: int = 10
    ):
        self.retriever = HybridRetriever(session, embedder)
        self.reranker = reranker or Reranker()
        self.retrieval_top_k = retrieval_top_k
        self.final_top_k = final_top_k

    def search(
        self,
        query: str,
        source_types: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        skip_rerank: bool = False
    ) -> List[SearchResult]:
        """
        Execute full RAG search pipeline.

        Args:
            query: Search query
            source_types: Filter by source type
            filters: Additional filters
            skip_rerank: Skip reranking step (faster but less accurate)

        Returns:
            List of relevant SearchResult
        """
        # Initial retrieval
        results = self.retriever.search(
            query,
            top_k=self.retrieval_top_k,
            source_types=source_types,
            filters=filters
        )

        if not results:
            return []

        # Rerank if enabled
        if not skip_rerank and self.reranker:
            results = self.reranker.rerank(
                query,
                results,
                top_k=self.final_top_k
            )
        else:
            results = results[:self.final_top_k]

        return results

    def search_logs(self, query: str, trace_id: Optional[str] = None) -> List[SearchResult]:
        """Search specifically in log embeddings."""
        filters = {"trace_id": trace_id} if trace_id else None
        return self.search(query, source_types=["log"], filters=filters)

    def search_context_rules(self, query: str) -> List[SearchResult]:
        """Search in context rules for relevant patterns."""
        return self.search(query, source_types=["rule"], skip_rerank=True)
```

---

## Indexing Service

### File: `app/rag/indexer.py`

```python
"""
Indexing service for adding documents to the RAG pipeline.
"""

import logging
import hashlib
from pathlib import Path
from typing import List, Optional, Dict, Any

from sqlalchemy.orm import Session

from app.db.models_rag import DocumentChunk, LogEmbedding, ContextRuleEmbedding
from app.db.models import ContextRule
from app.rag.chunkers import get_chunker, Chunk
from app.rag.embeddings import get_embedder, BaseEmbedder
from app.config import settings

logger = logging.getLogger(__name__)


class RAGIndexer:
    """
    Indexes documents, logs, and context rules for RAG retrieval.
    """

    def __init__(
        self,
        session: Session,
        embedder: Optional[BaseEmbedder] = None,
        chunking_strategy: str = "late"
    ):
        self.session = session
        self.embedder = embedder or get_embedder(
            provider=settings.get("EMBEDDING_PROVIDER", "openai")
        )
        self.chunking_strategy = chunking_strategy
        self.chunker = get_chunker(
            chunking_strategy,
            chunk_size=settings.get("CHUNK_SIZE", 512),
            chunk_overlap=settings.get("CHUNK_OVERLAP", 50)
        )

    def index_document(
        self,
        content: str,
        source_id: str,
        source_type: str = "doc",
        metadata: Optional[Dict[str, Any]] = None,
        force_reindex: bool = False
    ) -> List[DocumentChunk]:
        """
        Index a document by chunking and embedding.

        Args:
            content: Document content
            source_id: Unique identifier (e.g., file path)
            source_type: Type of source ('doc', 'log', 'rule')
            metadata: Additional metadata
            force_reindex: Re-index even if content hash matches

        Returns:
            List of created DocumentChunk objects
        """
        # Check if already indexed
        content_hash = hashlib.sha256(content.encode()).hexdigest()

        existing = self.session.query(DocumentChunk).filter(
            DocumentChunk.source_id == source_id,
            DocumentChunk.source_hash == content_hash
        ).first()

        if existing and not force_reindex:
            logger.info(f"Document already indexed: {source_id}")
            return self.session.query(DocumentChunk).filter(
                DocumentChunk.source_id == source_id
            ).all()

        # Delete existing chunks if reindexing
        if force_reindex:
            self.session.query(DocumentChunk).filter(
                DocumentChunk.source_id == source_id
            ).delete()

        # Chunk document
        chunks = self.chunker.chunk(content, source_id, metadata)

        # Embed chunks
        chunk_texts = [
            f"{c.context_prefix}\n\n{c.content}" if c.context_prefix else c.content
            for c in chunks
        ]
        embeddings = self.embedder.embed(chunk_texts)

        # Store chunks
        db_chunks = []
        for chunk, embedding in zip(chunks, embeddings):
            db_chunk = DocumentChunk(
                source_type=source_type,
                source_id=source_id,
                source_hash=content_hash,
                content=chunk.content,
                chunk_index=chunk.index,
                total_chunks=chunk.total_chunks,
                context_prefix=chunk.context_prefix,
                metadata=chunk.metadata,
                embedding=embedding
            )
            self.session.add(db_chunk)
            db_chunks.append(db_chunk)

        self.session.commit()
        logger.info(f"Indexed {len(db_chunks)} chunks from {source_id}")

        return db_chunks

    def index_log_trace(
        self,
        trace_id: str,
        content: str,
        summary: Optional[str] = None,
        services: Optional[List[str]] = None,
        error_types: Optional[List[str]] = None,
        analysis_result: Optional[Dict] = None
    ) -> LogEmbedding:
        """
        Index a log trace for similarity search.

        Args:
            trace_id: Unique trace identifier
            content: Log content (may be summarized)
            summary: Optional human-readable summary
            services: List of services involved
            error_types: List of error types found
            analysis_result: Analysis results from agents

        Returns:
            Created LogEmbedding object
        """
        # Check if exists
        existing = self.session.query(LogEmbedding).filter(
            LogEmbedding.trace_id == trace_id
        ).first()

        if existing:
            # Update existing
            existing.content = content
            existing.summary = summary
            existing.services = services
            existing.error_types = error_types
            existing.analysis_result = analysis_result
            existing.embedding = self.embedder.embed_query(content)
            self.session.commit()
            return existing

        # Create new
        log_embedding = LogEmbedding(
            trace_id=trace_id,
            content=content,
            summary=summary,
            services=services,
            error_types=error_types,
            analysis_result=analysis_result,
            embedding=self.embedder.embed_query(content)
        )

        self.session.add(log_embedding)
        self.session.commit()

        logger.info(f"Indexed log trace: {trace_id}")
        return log_embedding

    def index_context_rules(self) -> int:
        """
        Index all active context rules from database.

        Returns:
            Number of rules indexed
        """
        rules = self.session.query(ContextRule).filter(
            ContextRule.is_active == True
        ).all()

        count = 0
        for rule in rules:
            # Combine rule fields for embedding
            combined_text = f"""
Context: {rule.context}
Important patterns: {rule.important}
Ignore patterns: {rule.ignore}
Description: {rule.description or 'No description'}
""".strip()

            # Check if embedding exists
            existing = self.session.query(ContextRuleEmbedding).filter(
                ContextRuleEmbedding.rule_id == rule.id
            ).first()

            embedding = self.embedder.embed_query(combined_text)

            if existing:
                existing.combined_text = combined_text
                existing.embedding = embedding
            else:
                rule_embedding = ContextRuleEmbedding(
                    rule_id=rule.id,
                    combined_text=combined_text,
                    embedding=embedding
                )
                self.session.add(rule_embedding)

            count += 1

        self.session.commit()
        logger.info(f"Indexed {count} context rules")

        return count

    def index_directory(
        self,
        directory: str,
        patterns: List[str] = ["*.txt", "*.md", "*.log"],
        source_type: str = "doc"
    ) -> int:
        """
        Index all matching files in a directory.

        Args:
            directory: Directory path
            patterns: Glob patterns for files to index
            source_type: Source type for all files

        Returns:
            Number of files indexed
        """
        from pathlib import Path

        dir_path = Path(directory)
        count = 0

        for pattern in patterns:
            for file_path in dir_path.glob(pattern):
                try:
                    content = file_path.read_text(encoding='utf-8')
                    self.index_document(
                        content=content,
                        source_id=str(file_path),
                        source_type=source_type,
                        metadata={"filename": file_path.name}
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to index {file_path}: {e}")

        return count
```

---

## Updated RAGContextManager

### File: `app/agents/verify_agent.py` (Updated RAGContextManager)

```python
class RAGContextManager:
    """
    Enhanced RAG context manager with semantic search.

    Replaces CSV-based rule matching with:
    - Vector similarity search for relevant rules
    - Hybrid search combining keywords and semantics
    - Configurable relevance thresholds
    """

    def __init__(
        self,
        session: Session,
        embedder: Optional[BaseEmbedder] = None,
        use_database: bool = True,
        fallback_csv: str = "app/app_settings/context_rules.csv"
    ):
        self.session = session
        self.use_database = use_database
        self.fallback_csv = fallback_csv

        if use_database:
            from app.rag.retrieval import RAGPipeline
            self.rag_pipeline = RAGPipeline(session, embedder)
        else:
            # Fallback to CSV-based (legacy)
            self.rules = self._load_csv_rules()

    def _load_csv_rules(self) -> List[ContextRule]:
        """Load rules from CSV (fallback mode)."""
        # Original implementation...
        pass

    def get_relevant_rules(
        self,
        domain: str,
        query_keys: List[str],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get semantically relevant context rules.

        Args:
            domain: Query domain (e.g., 'bkash', 'transactions')
            query_keys: Extracted query keys
            top_k: Number of rules to return

        Returns:
            List of relevant rule dictionaries
        """
        if not self.use_database:
            # Fallback to keyword matching
            return self._get_rules_keyword(domain, query_keys)

        # Build semantic query from domain and keys
        query = f"Context: {domain}. Keywords: {', '.join(query_keys)}"

        # Search using RAG pipeline
        results = self.rag_pipeline.search(
            query,
            source_types=["rule"],
            skip_rerank=True  # Rules don't need reranking
        )

        # Extract rule details
        rules = []
        for result in results[:top_k]:
            # Parse metadata or fetch from DB
            rules.append({
                "context": result.metadata.get("context", ""),
                "important": result.metadata.get("important", ""),
                "ignore": result.metadata.get("ignore", ""),
                "description": result.metadata.get("description", ""),
                "relevance_score": result.score
            })

        return rules

    def build_rag_context(
        self,
        query: str,
        domain: str,
        query_keys: List[str],
        trace_content: Optional[str] = None
    ) -> str:
        """
        Build RAG context string for LLM prompt.

        Args:
            query: Original user query
            domain: Query domain
            query_keys: Extracted keys
            trace_content: Optional trace content for additional context

        Returns:
            Formatted RAG context string
        """
        rules = self.get_relevant_rules(domain, query_keys)

        context_parts = ["RELEVANT CONTEXT RULES:"]

        for i, rule in enumerate(rules, 1):
            context_parts.append(f"""
Rule {i} (relevance: {rule.get('relevance_score', 'N/A'):.2f}):
- Context: {rule['context']}
- Important patterns: {rule['important']}
- Ignore patterns: {rule['ignore']}
- Description: {rule['description']}
""")

        # Add similar past incidents if trace content provided
        if trace_content:
            similar = self.rag_pipeline.search_logs(trace_content[:500])
            if similar:
                context_parts.append("\nSIMILAR PAST INCIDENTS:")
                for result in similar[:3]:
                    context_parts.append(f"- {result.content[:200]}...")

        return "\n".join(context_parts)
```

---

## File-by-File Implementation Steps

| Step | File | Action | Description |
|------|------|--------|-------------|
| 1 | `requirements.txt` | MODIFY | Add RAG dependencies |
| 2 | `app/db/models_rag.py` | CREATE | RAG-specific ORM models |
| 3 | `app/db/base.py` | MODIFY | Import RAG models |
| 4 | `alembic/versions/xxx_add_rag_tables.py` | CREATE | Migration for RAG tables |
| 5 | `app/rag/__init__.py` | CREATE | Package init |
| 6 | `app/rag/chunkers.py` | CREATE | Chunking strategies |
| 7 | `app/rag/embeddings.py` | CREATE | Embedding providers |
| 8 | `app/rag/retrieval.py` | CREATE | Hybrid search + reranking |
| 9 | `app/rag/indexer.py` | CREATE | Document indexing service |
| 10 | `app/agents/verify_agent.py` | MODIFY | Update RAGContextManager |
| 11 | `app/api/rag_routes.py` | CREATE | RAG API endpoints |
| 12 | `app/main.py` | MODIFY | Register RAG routes |
| 13 | `scripts/index_documents.py` | CREATE | Indexing script |
| 14 | `config/settings.toml` | MODIFY | Add RAG settings |

---

## Dependencies to Add

```txt
# requirements.txt additions for Phase 3

# Embeddings
openai>=1.0.0
sentence-transformers>=2.2.0
FlagEmbedding>=1.2.0

# Chunking
tiktoken>=0.5.0
nltk>=3.8.0

# Reranking
cohere>=4.0.0

# Vector operations
pgvector>=0.2.0
numpy>=1.24.0

# Optional: Jina embeddings
# jina>=3.0.0
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_chunkers.py

import pytest
from app.rag.chunkers import (
    FixedSizeChunker, LateChunker, SemanticChunker, LogChunker
)


class TestFixedSizeChunker:
    def test_basic_chunking(self):
        chunker = FixedSizeChunker(chunk_size=100, chunk_overlap=20)
        text = "word " * 200  # ~200 tokens

        chunks = chunker.chunk(text, "test_doc")

        assert len(chunks) > 1
        assert all(c.total_chunks == len(chunks) for c in chunks)

    def test_overlap(self):
        chunker = FixedSizeChunker(chunk_size=50, chunk_overlap=10)
        text = "word " * 100

        chunks = chunker.chunk(text, "test_doc")

        # Verify overlap exists
        for i in range(len(chunks) - 1):
            assert chunks[i].content[-20:] in chunks[i + 1].content


class TestLogChunker:
    def test_preserves_log_entries(self):
        chunker = LogChunker(chunk_size=500)

        logs = """2025-01-15 10:00:00 INFO Starting service
2025-01-15 10:00:01 DEBUG Connection established
2025-01-15 10:00:02 ERROR Failed to authenticate"""

        chunks = chunker.chunk(logs, "test.log")

        # Each log entry should be intact
        assert "Starting service" in chunks[0].content
```

### Integration Tests

```python
# tests/integration/test_rag_pipeline.py

import pytest
from app.rag.retrieval import HybridRetriever, RAGPipeline
from app.rag.indexer import RAGIndexer


class TestRAGPipeline:

    @pytest.fixture
    def indexed_docs(self, db_session):
        indexer = RAGIndexer(db_session)

        # Index test documents
        indexer.index_document(
            "bKash payment failed due to timeout",
            "doc1", "doc"
        )
        indexer.index_document(
            "Transaction completed successfully",
            "doc2", "doc"
        )

        return indexer

    def test_hybrid_search(self, db_session, indexed_docs):
        pipeline = RAGPipeline(db_session)

        results = pipeline.search("bkash payment error")

        assert len(results) > 0
        assert "bKash" in results[0].content

    def test_reranking_improves_relevance(self, db_session, indexed_docs):
        pipeline = RAGPipeline(db_session)

        # Search with and without reranking
        results_no_rerank = pipeline.search("payment", skip_rerank=True)
        results_reranked = pipeline.search("payment", skip_rerank=False)

        # Reranked results should have rerank_score
        assert results_reranked[0].rerank_score is not None
```

---

## Critical Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `app/rag/chunkers.py` | All | NEW - Chunking strategies |
| `app/rag/embeddings.py` | All | NEW - Embedding providers |
| `app/rag/retrieval.py` | All | NEW - Hybrid search + reranking |
| `app/rag/indexer.py` | All | NEW - Document indexing |
| `app/db/models_rag.py` | All | NEW - RAG ORM models |
| `app/agents/verify_agent.py` | 57-200 | Update RAGContextManager |
| `app/tools/log_searcher.py` | Add embedding hooks |

---

## Acceptance Criteria

| Criterion | Verification Procedure |
|-----------|------------------------|
| Documents can be chunked | Index a document, verify chunks in DB |
| Embeddings are computed | Query `document_chunks.embedding IS NOT NULL` |
| Vector search works | Search query, verify results sorted by similarity |
| BM25 search works | Search exact keyword, verify it's in results |
| Hybrid fusion works | Compare hybrid vs vector-only accuracy |
| Reranking improves quality | A/B test with/without reranking |
| Log traces indexed | Index trace, search for similar incidents |
| Context rules searchable | Query rules semantically |
| RAG context generated | Verify context string includes relevant rules |
