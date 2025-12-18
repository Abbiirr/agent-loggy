# RAG Implementation Plan for agent-loggy

## Overview

Add Retrieval-Augmented Generation (RAG) using PostgreSQL + pgvector to enhance log analysis with:
- Historical analysis lookup
- Error pattern knowledge base
- Log context enhancement
- Documentation search

## Architecture

```
                     User Query
                         │
                         ▼
              ┌──────────────────┐
              │  Orchestrator    │
              └────────┬─────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
   ┌──────────┐  ┌──────────┐  ┌──────────┐
   │ Parameter│  │ Embedding│  │ RAG      │
   │ Agent    │  │ Service  │  │ Service  │
   └──────────┘  └────┬─────┘  └────┬─────┘
                      │             │
                      ▼             ▼
              ┌───────────────────────────┐
              │   PostgreSQL + pgvector   │
              │   ┌─────────────────────┐ │
              │   │ embeddings          │ │
              │   │ rag_documents       │ │
              │   │ rag_collections     │ │
              │   └─────────────────────┘ │
              └───────────────────────────┘
```

## Implementation Steps

### Phase 1: Infrastructure

**1.1 Add Dependencies**

File: `pyproject.toml`
```toml
pgvector = "^0.3.0"
```

**1.2 Create Embedding Model**

File: `app/models/embedding.py`

Tables:
- `rag_collections` - Groups of documents (e.g., "analysis_reports", "error_patterns", "documentation")
- `rag_documents` - Source documents with metadata
- `embeddings` - Vector embeddings with pgvector

```
rag_collections
├── id (PK)
├── name (unique)
├── description
├── embedding_model
├── vector_dimension
└── created_at

rag_documents
├── id (PK)
├── collection_id (FK)
├── source_type (analysis_report, error_pattern, log, documentation)
├── source_id (reference to original)
├── title
├── content (full text)
├── metadata (JSONB)
├── is_active
└── created_at

embeddings
├── id (PK)
├── document_id (FK)
├── chunk_index
├── chunk_text
├── vector (pgvector - 768 dimensions for nomic-embed-text)
├── token_count
└── created_at
```

**1.3 Create Migration**

File: `alembic/versions/add_rag_tables.py`

- Enable pgvector extension: `CREATE EXTENSION IF NOT EXISTS vector`
- Create tables with schema prefix
- Add HNSW index for vector similarity search
- Follow existing trigger patterns for updated_at

### Phase 2: Embedding Service

**2.1 Create Embedding Service**

File: `app/services/embedding_service.py`

```python
class EmbeddingService:
    def __init__(self, db: Optional[Session] = None):
        self._db = db
        self._cache = cache_manager.get_cache("embeddings", ttl=3600)
        self._client = Client(host=settings.OLLAMA_HOST)
        self._model = settings.EMBEDDING_MODEL  # nomic-embed-text

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding vector for text using Ollama"""

    def embed_and_store(self, document_id: int, content: str, chunk_size: int = 500):
        """Chunk content and store embeddings"""

    def similarity_search(self, query: str, collection: str, limit: int = 5) -> List[Dict]:
        """Find similar documents using cosine similarity"""
```

Key methods:
- `embed_text()` - Uses Ollama's embedding API
- `chunk_text()` - Splits content into overlapping chunks
- `embed_and_store()` - Chunks + embeds + stores in DB
- `similarity_search()` - Vector similarity with pgvector

**2.2 Add Feature Flags**

File: `app/config.py`
```python
USE_RAG: bool = False
EMBEDDING_MODEL: str = "nomic-embed-text"
VECTOR_DIMENSION: int = 768
RAG_CHUNK_SIZE: int = 500
RAG_CHUNK_OVERLAP: int = 50
RAG_TOP_K: int = 5
```

### Phase 3: RAG Service

**3.1 Create RAG Service**

File: `app/services/rag_service.py`

```python
class RAGService:
    def __init__(self):
        self._embedding_service = get_embedding_service()
        self._cache = cache_manager.get_cache("rag", ttl=600)

    # Document Management
    def add_document(self, collection: str, content: str, metadata: Dict) -> int
    def update_document(self, document_id: int, content: str) -> None
    def delete_document(self, document_id: int) -> None

    # Search
    def search(self, query: str, collections: List[str], limit: int = 5) -> List[RAGResult]
    def search_similar_analyses(self, params: Dict) -> List[RAGResult]
    def search_error_patterns(self, error_type: str, domain: str) -> List[RAGResult]

    # Context Building
    def build_context(self, query: str, collections: List[str]) -> str
```

**3.2 Create RAG Result Model**

File: `app/schemas/rag.py`
```python
class RAGResult(BaseModel):
    document_id: int
    title: str
    content: str
    similarity_score: float
    metadata: Dict
    source_type: str
```

### Phase 4: Integration Points

**4.1 Index Analysis Reports**

Modify: `app/agents/analyze_agent.py`

After generating analysis files, index them for RAG:
```python
def _index_analysis_report(self, trace_id: str, content: str, metadata: Dict):
    if settings.USE_RAG:
        rag_service = get_rag_service()
        rag_service.add_document(
            collection="analysis_reports",
            content=content,
            metadata={"trace_id": trace_id, **metadata}
        )
```

**4.2 Enhance Verify Agent with RAG Context**

Modify: `app/agents/verify_agent.py`

In `_analyze_relevance_with_rag()`, add vector search:
```python
def _get_rag_context(self, query: str, domain: str) -> str:
    if not settings.USE_RAG:
        return ""

    rag_service = get_rag_service()
    results = rag_service.search(
        query=query,
        collections=["analysis_reports", "error_patterns"],
        limit=settings.RAG_TOP_K
    )

    context = "SIMILAR PAST ANALYSES:\n"
    for r in results:
        context += f"- [{r.similarity_score:.0%}] {r.title}: {r.content[:200]}...\n"
    return context
```

**4.3 Add RAG Step to Orchestrator**

Modify: `app/orchestrator.py`

Add new step after parameter extraction:
```python
# STEP 1.5: RAG Context Retrieval
if settings.USE_RAG:
    rag_context = await self._step_retrieve_rag_context(ctx)
    ctx.rag_context = rag_context
    yield "Retrieved RAG Context", {"documents_found": len(rag_context)}
```

### Phase 5: Knowledge Base Population

**5.1 Create Seed Script for Error Patterns**

File: `scripts/seed_error_patterns.py`

Populate the error patterns collection from:
- Existing context_rules.csv
- Common banking error patterns
- Historical analysis summaries

**5.2 Create Document Ingestion Script**

File: `scripts/ingest_documents.py`

For documentation search:
```python
def ingest_markdown_docs(docs_dir: str, collection: str = "documentation"):
    """Index markdown documentation files"""
```

### Phase 6: API Endpoints (Optional)

**6.1 RAG Admin Router**

File: `app/routers/rag.py`

```python
@router.post("/api/rag/search")
async def search_rag(query: str, collections: List[str])

@router.post("/api/rag/documents")
async def add_document(collection: str, content: str, metadata: Dict)

@router.get("/api/rag/collections")
async def list_collections()

@router.post("/api/rag/reindex/{collection}")
async def reindex_collection(collection: str)
```

## Files to Create

| File | Purpose |
|------|---------|
| `app/models/embedding.py` | SQLAlchemy models for RAG tables |
| `app/services/embedding_service.py` | Vector embedding generation and storage |
| `app/services/rag_service.py` | RAG search and context building |
| `app/schemas/rag.py` | Pydantic models for RAG results |
| `app/routers/rag.py` | RAG admin API endpoints |
| `alembic/versions/add_rag_tables.py` | Database migration |
| `scripts/seed_error_patterns.py` | Initial error pattern data |
| `scripts/ingest_documents.py` | Document ingestion utility |

## Files to Modify

| File | Changes |
|------|---------|
| `pyproject.toml` | Add pgvector dependency |
| `app/config.py` | Add RAG feature flags and settings |
| `app/models/__init__.py` | Export new models |
| `app/services/__init__.py` | Export new services |
| `app/agents/analyze_agent.py` | Index reports after generation |
| `app/agents/verify_agent.py` | Add RAG context to relevance analysis |
| `app/orchestrator.py` | Add RAG context retrieval step |
| `app/main.py` | Register RAG router |

## Database Schema

```sql
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;

-- Collections
CREATE TABLE {schema}.rag_collections (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    embedding_model VARCHAR(100) DEFAULT 'nomic-embed-text',
    vector_dimension INTEGER DEFAULT 768,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Documents
CREATE TABLE {schema}.rag_documents (
    id SERIAL PRIMARY KEY,
    collection_id INTEGER REFERENCES {schema}.rag_collections(id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL,
    source_id VARCHAR(255),
    title VARCHAR(500),
    content TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Embeddings with pgvector
CREATE TABLE {schema}.embeddings (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES {schema}.rag_documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    vector vector(768),
    token_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(document_id, chunk_index)
);

-- HNSW index for fast similarity search
CREATE INDEX idx_embeddings_vector ON {schema}.embeddings
    USING hnsw (vector vector_cosine_ops);

-- Additional indexes
CREATE INDEX idx_documents_collection ON {schema}.rag_documents(collection_id);
CREATE INDEX idx_documents_source ON {schema}.rag_documents(source_type, source_id);
CREATE INDEX idx_embeddings_document ON {schema}.embeddings(document_id);
```

## SSE Events

RAG context retrieval will emit a new SSE event:

```
event: Retrieved RAG Context
data: {
  "documents_found": 3,
  "collections_searched": ["analysis_reports", "error_patterns"],
  "top_matches": [
    {"title": "NPSB Timeout Analysis - 2024-01-15", "similarity": 0.89},
    {"title": "Payment Gateway Error Pattern", "similarity": 0.85}
  ]
}
```

This shows users what similar past analyses were found to enhance the current analysis.

## Usage Flow

1. **Indexing (Background)**
   - Analysis reports are indexed after generation
   - Error patterns seeded from CSV + manual additions
   - Documentation indexed via ingestion script

2. **Query Enhancement (Runtime)**
   ```
   User Query: "Show failed NPSB transactions"
        │
        ▼
   Parameter Extraction
        │
        ▼
   RAG Context Retrieval ◄── Similar past analyses
        │                    Error pattern matches
        ▼                    Relevant documentation
   Enhanced Analysis
        │
        ▼
   Verification with RAG Context
   ```

3. **Similarity Search Query**
   ```sql
   SELECT d.id, d.title, d.content, d.metadata,
          1 - (e.vector <=> query_vector) as similarity
   FROM embeddings e
   JOIN rag_documents d ON e.document_id = d.id
   JOIN rag_collections c ON d.collection_id = c.id
   WHERE c.name = ANY($1)  -- collections filter
     AND d.is_active = true
   ORDER BY e.vector <=> query_vector
   LIMIT $2;
   ```

## Testing Plan

1. Unit tests for embedding service
2. Integration tests for RAG search
3. Performance tests for vector queries
4. End-to-end test through orchestrator pipeline

## Rollout Strategy

1. Deploy with `USE_RAG=false` (default)
2. Run migration to create tables
3. Seed initial data (error patterns, docs)
4. Enable `USE_RAG=true` in staging
5. Monitor performance and accuracy
6. Enable in production
