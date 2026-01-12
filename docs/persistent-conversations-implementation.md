# Persistent Conversations Implementation

This document describes the complete implementation of the persistent conversations feature for agent-loggy, implemented across 5 phases.

## Overview

The persistent conversations feature enables multi-turn conversations with context preservation, allowing users to have ongoing discussions with the log analysis system while maintaining full conversation history and context.

### Key Features
- Database-backed conversation storage
- Multi-turn conversation support with context window management
- LLM-based conversation summarization for long conversations
- Token-aware context management
- Feature flag for gradual rollout
- RESTful API endpoints

### Test Summary
- **Total Tests**: 146
- **Status**: All Passing

---

## Phase 1: Database Layer

### Files Created/Modified

#### `app/models/conversation.py`
Three SQLAlchemy ORM models for conversation persistence:

**Conversation Model**
```python
class Conversation(Base):
    __tablename__ = "conversations"

    id: int                          # Primary key
    conversation_id: str             # UUID for external reference
    project_code: Optional[str]      # e.g., 'MMBL', 'NCC'
    env: Optional[str]               # e.g., 'prod', 'staging'
    domain: Optional[str]            # e.g., 'NPSB', 'BEFTN'
    title: Optional[str]             # Auto-generated or user-provided
    status: str                      # 'active' or 'archived'
    is_active: bool                  # Quick filter flag
    summary: Optional[str]           # LLM-generated summary
    summary_token_count: Optional[int]
    created_at: datetime
    updated_at: datetime

    # Relationships
    messages: List[Message]          # Ordered by created_at
    executions: List[PipelineExecution]  # Ordered by started_at DESC
```

**Message Model**
```python
class Message(Base):
    __tablename__ = "messages"

    id: int
    conversation_id: int             # FK to conversations
    role: str                        # 'user', 'assistant', 'system'
    content: str
    message_type: Optional[str]      # 'prompt', 'response', 'clarification'
    message_metadata: Optional[dict] # JSON metadata
    token_count: Optional[int]
    created_at: datetime

    # Methods
    def to_dict() -> dict
    def to_llm_format() -> dict      # Returns {role, content}
```

**PipelineExecution Model**
```python
class PipelineExecution(Base):
    __tablename__ = "pipeline_executions"

    id: int
    execution_id: str                # UUID
    conversation_id: int             # FK to conversations
    prompt: str
    status: str                      # 'pending', 'running', 'completed', 'failed'
    extracted_params: Optional[dict]
    trace_ids: Optional[List[str]]
    report_files: Optional[List[str]]
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]

    # Methods
    def is_complete() -> bool
    def is_streaming() -> bool
    def duration_seconds() -> Optional[float]
```

#### `alembic/versions/xxx_add_conversation_tables.py`
Database migration adding the three tables with:
- Indexes on `conversation_id`, `project_code`, `status`
- Foreign key constraints with CASCADE delete
- Timestamps with server defaults

### Tests: 23 tests
- `app/tests/test_conversation_models.py`
- Coverage: Model creation, relationships, cascade delete, serialization

---

## Phase 2: Service Layer

### Files Created

#### `app/services/conversation_service.py`
Core service for conversation CRUD operations:

```python
class ConversationService:
    def __init__(self, db: Optional[Session] = None)

    # Conversation CRUD
    def create_conversation(project_code=None, env=None, domain=None, title=None) -> Conversation
    def get_conversation(conversation_id: str) -> Optional[Conversation]
    def list_conversations(project_code=None, status="active", limit=20, offset=0) -> List[Conversation]
    def count_conversations(project_code=None, status=None) -> int
    def update_conversation(conversation_id: str, **kwargs) -> Optional[Conversation]
    def archive_conversation(conversation_id: str) -> bool
    def delete_conversation(conversation_id: str) -> bool

    # Message operations
    def add_message(conversation_id, role, content, message_type=None,
                   metadata=None, token_count=None) -> Optional[Message]
    def get_messages(conversation_id, limit=50, offset=0) -> List[Message]

    # Execution operations
    def create_execution(conversation_id, prompt) -> Optional[PipelineExecution]
    def update_execution(execution_id, **kwargs) -> Optional[PipelineExecution]
    def get_execution(execution_id) -> Optional[PipelineExecution]
    def get_executions(conversation_id, limit=10) -> List[PipelineExecution]

    # Utilities
    def generate_title(conversation_id) -> str

# Singleton accessor
def get_conversation_service() -> ConversationService
```

#### `app/services/memory_service.py`
Service for context window management and summarization:

```python
class MemoryService:
    TOKENS_PER_WORD = 1.3  # Token estimation multiplier

    def __init__(
        self,
        conversation_service: Optional[ConversationService] = None,
        max_context_tokens: int = 4000,
        summarization_threshold: int = 20,
        recent_messages_to_keep: int = 10
    )

    # Token estimation
    def estimate_tokens(text: str) -> int
    def estimate_messages_tokens(messages: List[Dict]) -> int

    # Context window management
    def get_context_window(conversation_id: str, max_tokens=None) -> List[Dict]
    def get_messages_for_context(conversation_id: str, exclude_last=0) -> List[Dict]

    # Summarization
    def should_summarize(conversation_id: str) -> bool
    def summarize_old_messages(conversation_id: str) -> Optional[str]
    def _call_llm_for_summary(messages_text: str) -> str
    def _create_fallback_summary(messages: list) -> str

    # Formatting
    def format_history_for_prompt(history: List[Dict], current_query: str) -> str

# Singleton accessor
def get_memory_service() -> MemoryService
```

**Context Window Strategy:**
1. Include summary as system message if available
2. Add recent messages that fit within token budget
3. Prioritize most recent messages when trimming

**Summarization Prompt:**
```
Summarize the following conversation history for a log analysis assistant.
Preserve:
- Key parameters mentioned (dates, trace IDs, domains, project codes)
- Important findings and conclusions
- User preferences and corrections
- Error patterns and resolutions discussed

Conversation:
{messages}

Summary (be concise, focus on actionable context):
```

### Tests: 68 tests
- `app/tests/test_conversation_service.py` (40 tests)
- `app/tests/test_memory_service.py` (28 tests)

---

## Phase 3: Orchestrator Integration

### Files Modified

#### `app/orchestrator.py`

**Extended PipelineContext dataclass:**
```python
@dataclass
class PipelineContext:
    text: str
    project: str
    env: str
    domain: str
    # ... existing fields ...

    # New conversation context fields
    conversation_id: Optional[str] = None
    execution_id: Optional[str] = None
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
```

**Modified analyze_stream() signature:**
```python
async def analyze_stream(
    self,
    text: str,
    project: str,
    env: str,
    domain: str,
    cache_policy: Optional[CachePolicy] = None,
    # New parameters
    conversation_id: Optional[str] = None,
    execution_id: Optional[str] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]
```

**Updated _step1_extract_parameters():**
- Passes `conversation_history` to ParametersAgent.run()

#### `app/agents/parameter_agent.py`

**Modified run() signature:**
```python
def run(
    self,
    text: str,
    cache_policy: Optional[CachePolicy] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> tuple[Dict, CacheDiagnostics]
```

#### `app/agents/planning_agent.py`

**Modified run() signature:**
```python
def run(
    self,
    text: str,
    project: str,
    env: str,
    domain: str,
    extracted_params: Optional[Dict[str, Any]] = None,
    cache_policy: Optional[CachePolicy] = None,
    conversation_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]
```

### Tests: 15 tests
- `app/tests/test_orchestrator_conversation.py`
- Coverage: PipelineContext fields, parameter passing, history formatting

---

## Phase 4: API Layer

### Files Created

#### `app/schemas/conversation.py`
Pydantic schemas for API request/response validation:

```python
class ConversationCreate(BaseModel):
    project: Optional[str] = None
    env: Optional[str] = None
    domain: Optional[str] = None

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    domain: Optional[str] = None
    status: Optional[str] = None

class MessageCreate(BaseModel):
    content: str
    cache: Optional[CachePolicyModel] = None

class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    content: str
    message_type: Optional[str]
    message_metadata: Optional[Dict[str, Any]]
    token_count: Optional[int]
    created_at: datetime

class ExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    execution_id: str
    status: str
    prompt: str
    extracted_params: Optional[Dict[str, Any]]
    trace_ids: Optional[List[str]]
    report_files: Optional[List[str]]
    error_message: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime]

class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    conversation_id: str
    project_code: Optional[str]
    env: Optional[str]
    domain: Optional[str]
    title: Optional[str]
    status: str
    is_active: bool
    message_count: int = 0
    has_summary: bool = False
    created_at: datetime
    updated_at: datetime

class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse] = []
    summary: Optional[str] = None
    executions: List[ExecutionResponse] = []

class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int
    limit: int
    offset: int

class StreamMessageResponse(BaseModel):
    execution_id: str
    stream_url: str
```

#### `app/routers/conversations.py`
REST API endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/conversations` | Create new conversation |
| GET | `/api/conversations` | List conversations (with filters) |
| GET | `/api/conversations/{id}` | Get conversation details |
| PATCH | `/api/conversations/{id}` | Update conversation |
| DELETE | `/api/conversations/{id}` | Archive conversation |
| POST | `/api/conversations/{id}/messages` | Add message & start analysis |
| GET | `/api/conversations/{id}/messages` | Get messages |

**Query Parameters for List:**
- `project`: Filter by project code
- `status`: Filter by status ('active', 'archived')
- `limit`: Max results (1-100, default 20)
- `offset`: Pagination offset

### Files Modified

#### `app/routers/__init__.py`
Added export: `conversations_router`

#### `app/main.py`
Added: `app.include_router(conversations_router)`

### Tests: 24 tests
- `app/tests/test_conversations_api.py`
- Coverage: CRUD operations, pagination, error handling, schema validation

---

## Phase 5: Memory & Polish

### Files Modified

#### `app/services/memory_service.py`

**Implemented LLM-based summarization:**
```python
def _call_llm_for_summary(self, messages_text: str) -> str:
    """
    Call LLM to generate summary using configured provider.
    """
    from app.services.llm_providers import create_llm_provider

    try:
        provider, model = create_llm_provider()

        prompt = SUMMARIZATION_PROMPT.format(messages=messages_text)
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant that summarizes conversations concisely."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]

        response = provider.chat(model=model, messages=messages)

        if isinstance(response, dict):
            content = response.get("message", {}).get("content", "")
            if content:
                return content.strip()

        return self._create_fallback_summary_from_text(messages_text)

    except Exception as e:
        logger.error(f"LLM summarization failed: {e}")
        raise  # Let caller handle with fallback

def _create_fallback_summary_from_text(self, messages_text: str) -> str:
    """Simple fallback when LLM unavailable."""
    lines = messages_text.split("\n")
    if len(lines) > 5:
        return f"Conversation summary ({len(lines)} messages): " + lines[0][:100]
    return messages_text[:200]
```

#### `app/config.py`

**Added feature flag:**
```python
class Settings(BaseSettings):
    # ... existing settings ...

    # Persistent Conversations Feature Flag
    USE_PERSISTENT_CONVERSATIONS: bool = False
```

#### `app/routers/conversations.py`

**Added feature flag dependency:**
```python
def require_persistent_conversations():
    """
    Dependency to check if persistent conversations feature is enabled.
    """
    if not settings.USE_PERSISTENT_CONVERSATIONS:
        raise HTTPException(
            status_code=501,
            detail="Persistent conversations feature is not enabled. "
                   "Set USE_PERSISTENT_CONVERSATIONS=true to enable."
        )

# Applied to all endpoints:
@router.post("", ..., dependencies=[Depends(require_persistent_conversations)])
@router.get("", ..., dependencies=[Depends(require_persistent_conversations)])
# ... etc for all 7 endpoints
```

### Files Created

#### `app/tests/test_conversation_flow.py`
End-to-end flow tests (16 tests):

```python
class TestConversationLifecycle:
    test_create_add_messages_archive_flow
    test_auto_title_generation

class TestMultiTurnConversation:
    test_context_preserved_across_turns
    test_context_formatted_for_agent

class TestMemorySummarization:
    test_summarization_triggered_above_threshold
    test_summary_included_in_context
    test_llm_summarization_called
    test_fallback_summary_on_llm_failure

class TestConversationWithExecution:
    test_execution_created_for_message
    test_execution_status_updates

class TestOrchestratorConversationIntegration:
    test_orchestrator_receives_conversation_context
    test_pipeline_context_includes_conversation

class TestTokenManagement:
    test_context_respects_token_limit
    test_recent_messages_prioritized

class TestConversationPersistence:
    test_conversation_persists_after_session_close
    test_messages_ordered_chronologically
```

### Tests: 16 new tests + 2 feature flag tests
- `app/tests/test_conversation_flow.py` (16 tests)
- `app/tests/test_conversations_api.py::TestFeatureFlag` (2 tests)

---

## Configuration

### Environment Variables

```bash
# Enable persistent conversations (required)
USE_PERSISTENT_CONVERSATIONS=true

# Database (required)
DATABASE_URL=postgresql://user:pass@host:5432/db
DATABASE_SCHEMA=your_schema

# LLM Provider (for summarization)
LLM_PROVIDER=ollama  # or 'openrouter'
OLLAMA_HOST=http://localhost:11434
MODEL=llama3
```

### Database Migration

```bash
# Generate migration (if needed)
uv run alembic revision --autogenerate -m "add_conversation_tables"

# Apply migration
uv run alembic upgrade head
```

---

## API Usage Examples

### Create Conversation
```bash
curl -X POST http://localhost:8000/api/conversations \
  -H "Content-Type: application/json" \
  -d '{"project": "MMBL", "env": "prod", "domain": "NPSB"}'
```

Response:
```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "project_code": "MMBL",
  "env": "prod",
  "domain": "NPSB",
  "status": "active",
  "is_active": true,
  "message_count": 0,
  "has_summary": false,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### Add Message
```bash
curl -X POST http://localhost:8000/api/conversations/{id}/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "Show NPSB timeout errors from yesterday"}'
```

Response:
```json
{
  "execution_id": "exec-123",
  "stream_url": "/api/conversations/{id}/stream/exec-123"
}
```

### List Conversations
```bash
curl "http://localhost:8000/api/conversations?project=MMBL&status=active&limit=10"
```

### Get Conversation Detail
```bash
curl http://localhost:8000/api/conversations/{id}
```

---

## File Summary

### Created Files
| File | Phase | Purpose |
|------|-------|---------|
| `app/models/conversation.py` | 1 | ORM models |
| `alembic/versions/xxx_add_conversation_tables.py` | 1 | Migration |
| `app/services/conversation_service.py` | 2 | CRUD service |
| `app/services/memory_service.py` | 2 | Context management |
| `app/schemas/conversation.py` | 4 | Pydantic schemas |
| `app/routers/conversations.py` | 4 | API endpoints |
| `app/tests/test_conversation_models.py` | 1 | Model tests |
| `app/tests/test_conversation_service.py` | 2 | Service tests |
| `app/tests/test_memory_service.py` | 2 | Memory tests |
| `app/tests/test_orchestrator_conversation.py` | 3 | Orchestrator tests |
| `app/tests/test_conversations_api.py` | 4 | API tests |
| `app/tests/test_conversation_flow.py` | 5 | E2E tests |

### Modified Files
| File | Phase | Changes |
|------|-------|---------|
| `app/orchestrator.py` | 3 | PipelineContext fields, analyze_stream params |
| `app/agents/parameter_agent.py` | 3 | conversation_history param |
| `app/agents/planning_agent.py` | 3 | conversation_history param |
| `app/routers/__init__.py` | 4 | Export conversations_router |
| `app/main.py` | 4 | Include conversations router |
| `app/config.py` | 5 | USE_PERSISTENT_CONVERSATIONS flag |
| `CLAUDE.md` | 5 | Documentation updates |
| `AGENTS.md` | 5 | Documentation updates |

---

## Test Coverage by Phase

| Phase | Test File | Tests | Status |
|-------|-----------|-------|--------|
| 1 | test_conversation_models.py | 23 | PASS |
| 2 | test_conversation_service.py | 40 | PASS |
| 2 | test_memory_service.py | 28 | PASS |
| 3 | test_orchestrator_conversation.py | 15 | PASS |
| 4 | test_conversations_api.py | 22 | PASS |
| 5 | test_conversation_flow.py | 16 | PASS |
| 5 | test_conversations_api.py (feature flag) | 2 | PASS |
| **Total** | | **146** | **ALL PASS** |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         API Layer (Phase 4)                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  /api/conversations/*  (routers/conversations.py)           ││
│  │    - Feature flag check (USE_PERSISTENT_CONVERSATIONS)      ││
│  │    - Pydantic validation (schemas/conversation.py)          ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Service Layer (Phase 2)                     │
│  ┌──────────────────────┐    ┌──────────────────────┐          │
│  │ ConversationService  │    │   MemoryService      │          │
│  │ - CRUD operations    │◄───│ - Token estimation   │          │
│  │ - Message management │    │ - Context window     │          │
│  │ - Execution tracking │    │ - LLM summarization  │          │
│  └──────────────────────┘    └──────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Orchestrator (Phase 3)                         │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  PipelineContext                                            ││
│  │    + conversation_id                                        ││
│  │    + execution_id                                           ││
│  │    + conversation_history                                   ││
│  └─────────────────────────────────────────────────────────────┘│
│                          │                                       │
│           ┌──────────────┴──────────────┐                       │
│           ▼                             ▼                       │
│  ┌─────────────────┐          ┌─────────────────┐              │
│  │ParametersAgent  │          │ PlanningAgent   │              │
│  │ +history param  │          │ +history param  │              │
│  └─────────────────┘          └─────────────────┘              │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Database Layer (Phase 1)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────────┐      │
│  │Conversation │──│  Message    │  │ PipelineExecution  │      │
│  │             │  │             │  │                    │      │
│  │ id          │  │ id          │  │ id                 │      │
│  │ conv_id     │◄─│ conv_id(FK) │  │ exec_id            │      │
│  │ project     │  │ role        │  │ conv_id(FK)        │      │
│  │ env         │  │ content     │  │ status             │      │
│  │ domain      │  │ metadata    │  │ trace_ids          │      │
│  │ summary     │  │ token_count │  │ report_files       │      │
│  └─────────────┘  └─────────────┘  └────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Future Enhancements

1. **Streaming Integration**: Connect SSE stream endpoint to orchestrator with conversation context
2. **Auto-Summarization**: Trigger summarization automatically after N messages
3. **Conversation Search**: Full-text search across conversation content
4. **Export/Import**: Export conversations for backup/sharing
5. **Conversation Branching**: Fork conversations for alternative explorations
