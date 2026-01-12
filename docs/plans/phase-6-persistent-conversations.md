# Phase 6: Multi-Session Persistent Chat Implementation

## Overview

This phase implements persistent conversation management, enabling:
- Multi-turn conversations with context retention
- Conversation history and replay
- Memory management for long conversations
- Session continuation across server restarts

**Current State:** Sessions stored in in-memory dict (`app/dependencies.py:15`), deleted after stream completion.

**Target State:** Database-backed conversations with full history, memory summarization, and API for conversation management.

---

## Phase 1: Database Layer (Foundation)

### 1.1 Models (`app/models/conversation.py`)

Following existing patterns from `prompt.py` and `project.py`:

```python
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import enum

from app.db.base import Base
from app.config import settings

SCHEMA = settings.DATABASE_SCHEMA


class ConversationStatus(enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class MessageRole(enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Conversation(Base):
    """Persistent conversation session."""
    __tablename__ = "conversations"
    __table_args__ = (
        Index("idx_conversations_project", "project_code"),
        Index("idx_conversations_status", "status"),
        Index("idx_conversations_created", "created_at"),
        Index("idx_conversations_updated", "updated_at"),
        {"schema": SCHEMA}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(100), unique=True, nullable=False)  # UUID for API
    project_code = Column(String(50), nullable=True)  # FK to projects optional
    env = Column(String(50), nullable=True)
    domain = Column(String(100), nullable=True)
    title = Column(String(255), nullable=True)  # Auto-generated from first message
    summary = Column(Text, nullable=True)  # Compressed history for long conversations
    summary_token_count = Column(Integer, default=0)
    status = Column(String(20), default="active", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    messages = relationship("Message", back_populates="conversation",
                           cascade="all, delete-orphan", order_by="Message.created_at")
    executions = relationship("PipelineExecution", back_populates="conversation",
                             cascade="all, delete-orphan", order_by="PipelineExecution.started_at.desc()")

    def __repr__(self):
        return f"<Conversation(id={self.id}, conversation_id={self.conversation_id}, title={self.title})>"

    def to_dict(self):
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "project_code": self.project_code,
            "env": self.env,
            "domain": self.domain,
            "title": self.title,
            "status": self.status,
            "message_count": len(self.messages) if self.messages else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Message(Base):
    """Individual message in a conversation."""
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_messages_conversation", "conversation_id"),
        Index("idx_messages_created", "created_at"),
        Index("idx_messages_role", "role"),
        {"schema": SCHEMA}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey(f"{SCHEMA}.conversations.id",
                            ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    message_type = Column(String(50), nullable=True)  # prompt, analysis, verification, etc.
    metadata = Column(JSONB, nullable=True)  # tokens, cache_hit, step_name, etc.
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, role={self.role}, type={self.message_type})>"

    def to_dict(self):
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "message_type": self.message_type,
            "metadata": self.metadata,
            "token_count": self.token_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PipelineExecution(Base):
    """Tracks individual analysis runs within a conversation."""
    __tablename__ = "pipeline_executions"
    __table_args__ = (
        Index("idx_executions_conversation", "conversation_id"),
        Index("idx_executions_status", "status"),
        Index("idx_executions_started", "started_at"),
        {"schema": SCHEMA}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(Integer, ForeignKey(f"{SCHEMA}.conversations.id",
                            ondelete="CASCADE"), nullable=False)
    execution_id = Column(String(100), unique=True, nullable=False)  # UUID for API
    status = Column(String(20), default="pending", nullable=False)  # pending, streaming, complete, error
    prompt = Column(Text, nullable=False)
    extracted_params = Column(JSONB, nullable=True)
    plan = Column(JSONB, nullable=True)
    trace_ids = Column(JSONB, nullable=True)  # List of found trace IDs
    report_files = Column(JSONB, nullable=True)  # List of generated files
    cache_diagnostics = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationship
    conversation = relationship("Conversation", back_populates="executions")

    def __repr__(self):
        return f"<PipelineExecution(id={self.id}, status={self.status})>"

    def to_dict(self):
        return {
            "id": self.id,
            "execution_id": self.execution_id,
            "status": self.status,
            "extracted_params": self.extracted_params,
            "trace_ids": self.trace_ids,
            "report_files": self.report_files,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
```

### 1.2 Migration (`alembic/versions/add_conversations.py`)

```python
"""add conversations and messages tables

Revision ID: add_conversations
Revises: add_context_rules (or latest)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = 'add_conversations'
down_revision = 'add_context_rules'  # Update to actual latest
branch_labels = None
depends_on = None

def get_schema():
    try:
        from app.config import settings
        return settings.DATABASE_SCHEMA
    except:
        return "public"

SCHEMA = get_schema()

def upgrade() -> None:
    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('conversation_id', sa.String(100), unique=True, nullable=False),
        sa.Column('project_code', sa.String(50), nullable=True),
        sa.Column('env', sa.String(50), nullable=True),
        sa.Column('domain', sa.String(100), nullable=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('summary_token_count', sa.Integer(), default=0),
        sa.Column('status', sa.String(20), default='active', nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                 server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                 server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA
    )

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(50), nullable=True),
        sa.Column('metadata', JSONB, nullable=True),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                 server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['conversation_id'], [f'{SCHEMA}.conversations.id'],
                               ondelete='CASCADE'),
        schema=SCHEMA
    )

    # Create pipeline_executions table
    op.create_table(
        'pipeline_executions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('execution_id', sa.String(100), unique=True, nullable=False),
        sa.Column('status', sa.String(20), default='pending', nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('extracted_params', JSONB, nullable=True),
        sa.Column('plan', JSONB, nullable=True),
        sa.Column('trace_ids', JSONB, nullable=True),
        sa.Column('report_files', JSONB, nullable=True),
        sa.Column('cache_diagnostics', JSONB, nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False,
                 server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['conversation_id'], [f'{SCHEMA}.conversations.id'],
                               ondelete='CASCADE'),
        schema=SCHEMA
    )

    # Create indexes
    op.create_index('idx_conversations_project', 'conversations', ['project_code'], schema=SCHEMA)
    op.create_index('idx_conversations_status', 'conversations', ['status'], schema=SCHEMA)
    op.create_index('idx_conversations_created', 'conversations', ['created_at'], schema=SCHEMA)
    op.create_index('idx_conversations_updated', 'conversations', ['updated_at'], schema=SCHEMA)

    op.create_index('idx_messages_conversation', 'messages', ['conversation_id'], schema=SCHEMA)
    op.create_index('idx_messages_created', 'messages', ['created_at'], schema=SCHEMA)
    op.create_index('idx_messages_role', 'messages', ['role'], schema=SCHEMA)

    op.create_index('idx_executions_conversation', 'pipeline_executions', ['conversation_id'], schema=SCHEMA)
    op.create_index('idx_executions_status', 'pipeline_executions', ['status'], schema=SCHEMA)
    op.create_index('idx_executions_started', 'pipeline_executions', ['started_at'], schema=SCHEMA)

    # Create updated_at trigger for conversations
    op.execute(f"""
        CREATE TRIGGER trg_conversations_updated_at
        BEFORE UPDATE ON {SCHEMA}.conversations
        FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.update_updated_at_column();
    """)

def downgrade() -> None:
    op.drop_trigger('trg_conversations_updated_at', table_name='conversations', schema=SCHEMA)
    op.drop_table('pipeline_executions', schema=SCHEMA)
    op.drop_table('messages', schema=SCHEMA)
    op.drop_table('conversations', schema=SCHEMA)
```

---

## Phase 2: Service Layer

### 2.1 Conversation Service (`app/services/conversation_service.py`)

```python
class ConversationService:
    """CRUD operations for conversations."""

    def __init__(self, db: Optional[Session] = None):
        self._db = db
        self._cache = cache_manager.get_cache("conversations")

    # Core CRUD
    def create_conversation(self, project_code: str = None, env: str = None,
                           domain: str = None) -> Conversation
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]
    def list_conversations(self, project_code: str = None, status: str = "active",
                          limit: int = 20, offset: int = 0) -> List[Conversation]
    def update_conversation(self, conversation_id: str, **kwargs) -> Conversation
    def archive_conversation(self, conversation_id: str) -> bool
    def delete_conversation(self, conversation_id: str) -> bool

    # Message operations
    def add_message(self, conversation_id: str, role: str, content: str,
                   message_type: str = None, metadata: dict = None) -> Message
    def get_messages(self, conversation_id: str, limit: int = 50) -> List[Message]

    # Execution tracking
    def create_execution(self, conversation_id: str, prompt: str) -> PipelineExecution
    def update_execution(self, execution_id: str, **kwargs) -> PipelineExecution
    def get_execution(self, execution_id: str) -> Optional[PipelineExecution]

    # Title generation
    def generate_title(self, conversation_id: str) -> str
        """Uses first user message to generate a short title via LLM."""
```

### 2.2 Memory Service (`app/services/memory_service.py`)

```python
class MemoryService:
    """Manages conversation context window and summarization."""

    def __init__(self, llm_provider: LLMProvider, model: str):
        self.llm = llm_provider
        self.model = model
        self.max_context_tokens = 4000  # Configurable
        self.summarization_threshold = 20  # messages

    def get_context_window(self, conversation_id: str,
                          max_tokens: int = 4000) -> List[Dict[str, str]]:
        """
        Returns messages that fit in token budget.
        Strategy: summary + recent N messages
        """

    def summarize_old_messages(self, conversation_id: str) -> str:
        """
        Compresses older messages into summary.
        Called when message count exceeds threshold.
        Stores result in Conversation.summary
        """

    def format_history_for_prompt(self, history: List[Dict],
                                  current_query: str) -> str:
        """
        Formats conversation history for agent prompts.
        Includes: [summary if exists] + [recent messages] + [current query]
        """

    def estimate_tokens(self, text: str) -> int:
        """Rough token count estimation (words * 1.3)."""
```

---

## Phase 3: Orchestrator Integration

### 3.1 Extend PipelineContext (`app/orchestrator.py`)

```python
@dataclass
class PipelineContext:
    # ... existing fields ...

    # New conversation fields
    conversation_id: Optional[str] = None
    execution_id: Optional[str] = None
    conversation_history: List[Dict[str, str]] = field(default_factory=list)

    # Callback for message persistence
    on_step_complete: Optional[Callable[[str, Any], None]] = None
```

### 3.2 Modify analyze_stream()

```python
async def analyze_stream(self, text: str, project: str, env: str, domain: str,
                        cache_policy: Optional[CachePolicy] = None,
                        conversation_id: Optional[str] = None,  # NEW
                        conversation_history: List[Dict] = None  # NEW
                        ) -> AsyncGenerator[Tuple[str, Any], None]:
    """
    Main analysis pipeline with optional conversation context.

    If conversation_id provided:
    1. Load conversation history via MemoryService
    2. Include history in agent prompts
    3. Save each step result as Message
    4. Update PipelineExecution on completion
    """
```

### 3.3 Agent Prompt Modifications

Each agent receives conversation history in system prompt:

```python
# In ParametersAgent, PlanningAgent, AnalyzeAgent
def _build_system_prompt(self, conversation_history: List[Dict] = None) -> str:
    base_prompt = self._get_base_prompt()

    if conversation_history:
        history_section = self._format_history(conversation_history)
        return f"{base_prompt}\n\n## Previous Conversation:\n{history_section}"

    return base_prompt
```

---

## Phase 4: API Endpoints

### 4.1 Pydantic Schemas (`app/schemas/conversation.py`)

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class ConversationCreate(BaseModel):
    project: Optional[str] = None
    env: Optional[str] = None
    domain: Optional[str] = None

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None

class MessageCreate(BaseModel):
    content: str
    cache: Optional[CachePolicyModel] = None

class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    message_type: Optional[str]
    created_at: datetime

class ConversationResponse(BaseModel):
    conversation_id: str
    title: Optional[str]
    project_code: Optional[str]
    status: str
    message_count: int
    created_at: datetime
    updated_at: datetime

class ConversationDetailResponse(ConversationResponse):
    messages: List[MessageResponse]
    summary: Optional[str]

class ConversationListResponse(BaseModel):
    conversations: List[ConversationResponse]
    total: int
    limit: int
    offset: int
```

### 4.2 Conversations Router (`app/routers/conversations.py`)

```python
router = APIRouter(prefix="/api/conversations", tags=["conversations"])

# Conversation CRUD
@router.post("", response_model=ConversationResponse)
async def create_conversation(req: ConversationCreate) -> ConversationResponse:
    """Create a new conversation."""

@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    project: Optional[str] = None,
    status: str = "active",
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0)
) -> ConversationListResponse:
    """List conversations with pagination."""

@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(conversation_id: str) -> ConversationDetailResponse:
    """Get conversation with all messages."""

@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    req: ConversationUpdate
) -> ConversationResponse:
    """Update conversation title or status."""

@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str) -> dict:
    """Archive/delete a conversation."""

# Message operations
@router.post("/{conversation_id}/messages")
async def send_message(
    conversation_id: str,
    req: MessageCreate,
    orchestrator: Orchestrator = Depends(get_orchestrator)
) -> EventSourceResponse:
    """
    Send message and stream analysis response.
    This is the main chat endpoint with context.
    """

@router.get("/{conversation_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    conversation_id: str,
    limit: int = Query(default=50, le=200)
) -> List[MessageResponse]:
    """Get messages with pagination."""
```

### 4.3 Streaming with Context

```python
@router.post("/{conversation_id}/messages")
async def send_message(conversation_id: str, req: MessageCreate, ...):
    async def event_generator():
        # 1. Load conversation and history
        conv = conversation_service.get_conversation(conversation_id)
        history = memory_service.get_context_window(conversation_id)

        # 2. Save user message
        conversation_service.add_message(
            conversation_id, "user", req.content, "prompt"
        )

        # 3. Create execution record
        execution = conversation_service.create_execution(
            conversation_id, req.content
        )

        # 4. Stream with context
        assistant_content = []
        async for step, payload in orchestrator.analyze_stream(
            req.content, conv.project_code, conv.env, conv.domain,
            cache_policy=cache_policy,
            conversation_id=conversation_id,
            conversation_history=history
        ):
            # Collect assistant responses
            if step in ("Compiled Summary", "Verification Results"):
                assistant_content.append(json.dumps(payload))

            yield f"event: {step}\ndata: {json.dumps(payload)}\n\n"

        # 5. Save assistant response
        conversation_service.add_message(
            conversation_id, "assistant",
            "\n".join(assistant_content),
            "analysis"
        )

        # 6. Update execution
        conversation_service.update_execution(
            execution.execution_id,
            status="complete",
            completed_at=datetime.utcnow()
        )

    return EventSourceResponse(event_generator())
```

---

## Phase 5: Memory Strategies

| Strategy | Trigger | Implementation |
|----------|---------|----------------|
| **Sliding Window** | <20 messages | Last N messages directly in context |
| **Summarization** | >20 messages | LLM summarizes older messages, stores in `summary` |
| **Hybrid** | Always | `summary` + last 10 messages |

### Summarization Prompt

```python
SUMMARIZATION_PROMPT = """
Summarize the following conversation history for a log analysis assistant.
Preserve:
- Key parameters mentioned (dates, trace IDs, domains)
- Important findings and conclusions
- User preferences and corrections

Conversation:
{messages}

Summary (be concise, focus on actionable context):
"""
```

---

## Phase 6: Feature Flag & Configuration

### 6.1 Config Settings (`app/config.py`)

```python
# Conversation settings
CONVERSATION_ENABLED: bool = True
CONVERSATION_MAX_MESSAGES: int = 100
CONVERSATION_SUMMARIZATION_THRESHOLD: int = 20
CONVERSATION_CONTEXT_TOKENS: int = 4000
CONVERSATION_TITLE_AUTO_GENERATE: bool = True
```

### 6.2 Feature Flag

```python
USE_PERSISTENT_CONVERSATIONS: bool = False  # Gradual rollout
```

When `False`, falls back to in-memory sessions (current behavior).

---

## File Structure Changes

```
app/
├── models/
│   ├── __init__.py           # ADD: Conversation, Message, PipelineExecution
│   └── conversation.py       # NEW
├── services/
│   ├── __init__.py           # ADD: conversation_service, memory_service
│   ├── conversation_service.py  # NEW
│   └── memory_service.py        # NEW
├── routers/
│   ├── __init__.py           # ADD: conversations_router
│   └── conversations.py      # NEW
├── schemas/
│   ├── __init__.py           # ADD: Conversation schemas
│   └── conversation.py       # NEW
├── orchestrator.py           # MODIFY: Add conversation_id, history params
├── dependencies.py           # MODIFY: Add conversation service dependency
└── config.py                 # MODIFY: Add conversation settings
```

---

## Implementation Order

**IMPORTANT: Test-First Development**

Each phase must include:
1. Write tests before/alongside implementation
2. Run tests to verify behavior
3. All tests must pass before moving to next phase

---

### Phase 1: Database Foundation (COMPLETE)
- [x] Create `app/models/conversation.py` with all three models
- [x] Add to `app/models/__init__.py`
- [x] Create migration `alembic/versions/add_conversations.py`
- [x] Run migration: `uv run alembic upgrade head`
- [x] **Write tests**: `app/tests/test_conversation_models.py` (23 tests)
- [x] **Run tests**: `uv run pytest app/tests/test_conversation_models.py -v`

### Phase 2: Service Layer (COMPLETE)
- [x] Create `app/services/conversation_service.py`
- [x] Create `app/services/memory_service.py`
- [x] **Write tests**: `app/tests/test_conversation_service.py` (40 tests)
- [x] **Write tests**: `app/tests/test_memory_service.py` (28 tests)
- [x] **Run tests**: `uv run pytest app/tests/test_conversation_service.py app/tests/test_memory_service.py -v`

### Phase 3: Orchestrator Integration (COMPLETE)
- [x] Extend `PipelineContext` with conversation fields (`conversation_id`, `execution_id`, `conversation_history`)
- [x] Modify `analyze_stream()` to accept conversation params
- [x] Update `ParametersAgent.run()` to accept and use `conversation_history`
- [x] Update `PlanningAgent.run()` to accept and use `conversation_history`
- [x] **Write tests**: `app/tests/test_orchestrator_conversation.py` (15 tests)
- [x] **Run tests**: `uv run pytest app/tests/test_orchestrator_conversation.py -v`

### Phase 4: API Layer (COMPLETE)
- [x] Create `app/schemas/conversation.py` (Pydantic schemas with ConfigDict)
- [x] Create `app/routers/conversations.py` with CRUD endpoints
- [x] Register router in `app/main.py` and `app/routers/__init__.py`
- [x] Implement `POST /{id}/messages` endpoint (returns stream URL)
- [x] **Write tests**: `app/tests/test_conversations_api.py` (22 tests)
- [x] **Run tests**: `uv run pytest app/tests/test_conversations_api.py -v`

### Phase 5: Memory & Polish
- [ ] Implement summarization for long conversations
- [ ] Add token counting and context management
- [ ] Add feature flag for gradual rollout
- [ ] **Write tests**: End-to-end conversation flow tests
- [ ] **Run tests**: Full test suite passes
- [ ] Documentation updates

---

## Testing Verification

### Unit Tests
```bash
# Phase 1: Model tests (23 tests)
uv run pytest app/tests/test_conversation_models.py -v

# Phase 2: Service tests
uv run pytest app/tests/test_conversation_service.py -v
uv run pytest app/tests/test_memory_service.py -v

# Phase 4: API tests
uv run pytest app/tests/test_conversations_api.py -v

# Run all conversation tests
uv run pytest app/tests/test_conversation*.py -v
```

### Integration Tests
```bash
# Create conversation
curl -X POST http://localhost:8000/api/conversations \
  -H "Content-Type: application/json" \
  -d '{"project": "MMBL", "env": "prod"}'

# Send message with streaming
curl -N -X POST http://localhost:8000/api/conversations/{id}/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "Show failed transactions from yesterday"}'

# Get conversation history
curl http://localhost:8000/api/conversations/{id}

# Continue conversation
curl -N -X POST http://localhost:8000/api/conversations/{id}/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "Now filter for NPSB only"}'
```

### Database Verification
```sql
-- Check tables created
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'agent_loggy' AND table_name IN ('conversations', 'messages', 'pipeline_executions');

-- Check conversation with messages
SELECT c.conversation_id, c.title, COUNT(m.id) as message_count
FROM agent_loggy.conversations c
LEFT JOIN agent_loggy.messages m ON c.id = m.conversation_id
GROUP BY c.id;
```

---

## Migration from In-Memory Sessions

### Phase A: Parallel Operation
1. Keep `active_sessions` dict for streaming state
2. Add conversation persistence alongside
3. Feature flag controls which path is used

### Phase B: Full Migration
1. Remove `active_sessions` dict
2. Use `PipelineExecution.status` for streaming state
3. All state in database

### Phase C: Cleanup
1. Remove legacy session code
2. Update documentation
3. Remove feature flag

---

## Critical Files to Modify

| File | Change |
|------|--------|
| `app/models/__init__.py` | Add conversation imports |
| `app/models/conversation.py` | NEW - All models |
| `app/services/conversation_service.py` | NEW - CRUD operations |
| `app/services/memory_service.py` | NEW - Context management |
| `app/schemas/conversation.py` | NEW - Pydantic models |
| `app/routers/conversations.py` | NEW - API endpoints |
| `app/routers/__init__.py` | Add router export |
| `app/main.py` | Include router |
| `app/orchestrator.py` | Add conversation params |
| `app/config.py` | Add settings |
| `app/dependencies.py` | Add service dependency |
| `alembic/versions/add_conversations.py` | NEW - Migration |

---

## Rollback Plan

If issues arise:
1. Set `USE_PERSISTENT_CONVERSATIONS=false` to disable
2. In-memory sessions continue working
3. Fix issues, re-enable when ready
4. Downgrade migration if needed: `uv run alembic downgrade add_context_rules`
