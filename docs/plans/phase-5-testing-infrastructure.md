# Phase 5: Testing Infrastructure Plan

## Executive Summary

This phase establishes comprehensive testing infrastructure for agent-loggy including **pytest** for unit/integration tests, **Promptfoo** for systematic prompt evaluation, **RAGAS** for RAG quality metrics, and **CI/CD pipelines** for automated quality gates. The target is **70% code coverage** with continuous monitoring of AI system quality.

**Timeline**: Week 6-7 (continuous throughout project)
**Dependencies**: Phase 1-4 (tests validate all phases)
**Blocking**: None (should run in parallel with development)

---

## Current State Analysis

### What Exists
| Component | Location | Status |
|-----------|----------|--------|
| Test Directory | `app/tests/` | Empty |
| Test Framework | None | Not configured |
| Prompt Testing | None | Manual only |
| RAG Metrics | None | No evaluation |
| CI/CD | None | No automation |
| Coverage | None | 0% |

### Problems with Current Approach
1. **No Tests**: Zero test coverage
2. **No Prompt Evaluation**: Cannot measure prompt quality changes
3. **No RAG Metrics**: Cannot detect retrieval degradation
4. **No CI/CD**: Manual verification only
5. **No Regression Detection**: Changes may break functionality unnoticed

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Testing Infrastructure                                │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                           Test Categories                                     │
│                                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌───────────┐ │
│  │ Unit Tests     │  │ Integration    │  │ Prompt Tests   │  │ RAG       │ │
│  │                │  │ Tests          │  │                │  │ Metrics   │ │
│  │ - Models       │  │ - API          │  │ - Promptfoo    │  │ - RAGAS   │ │
│  │ - Services     │  │ - Database     │  │ - LLM-as-Judge │  │ - Custom  │ │
│  │ - Utilities    │  │ - RAG Pipeline │  │ - Assertions   │  │           │ │
│  │                │  │ - Streaming    │  │                │  │           │ │
│  │ Target: 70%    │  │ Target: 50%    │  │ Target: All    │  │ Target:   │ │
│  │ coverage       │  │ coverage       │  │ prompts        │  │ Baseline  │ │
│  └────────────────┘  └────────────────┘  └────────────────┘  └───────────┘ │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                          CI/CD Pipeline                                       │
│                                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │ PR Created  │───▶│ Lint/Format │───▶│ Unit Tests  │───▶│ Integration │  │
│  │             │    │             │    │             │    │ Tests       │  │
│  └─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘  │
│                                                                   │         │
│                                                                   ▼         │
│                     ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│                     │ Deploy to   │◀───│ Prompt      │◀───│ Coverage    │  │
│                     │ Staging     │    │ Eval        │    │ Check       │  │
│                     └─────────────┘    └─────────────┘    └─────────────┘  │
│                                                                             │
│  Quality Gates:                                                             │
│  - Lint: 0 errors                                                          │
│  - Unit Tests: 100% pass                                                   │
│  - Coverage: >= 70%                                                        │
│  - Prompt Eval: >= 80% pass rate                                           │
│  - Integration: 100% pass                                                  │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                       RAG Quality Monitoring                                  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ RAGAS Metrics (RAG Triad)                                            │  │
│  │                                                                       │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐  │  │
│  │  │ Context         │  │ Groundedness    │  │ Answer Relevance    │  │  │
│  │  │ Relevance       │  │                 │  │                     │  │  │
│  │  │                 │  │ Is the answer   │  │ Does the answer     │  │  │
│  │  │ Is retrieved    │  │ supported by    │  │ address the         │  │  │
│  │  │ context useful? │  │ the context?    │  │ question?           │  │  │
│  │  │                 │  │                 │  │                     │  │  │
│  │  │ Target: >= 0.8  │  │ Target: >= 0.85 │  │ Target: >= 0.8      │  │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────────┘  │  │
│  │                                                                       │  │
│  │  Additional Metrics:                                                  │  │
│  │  - Faithfulness: >= 0.8                                              │  │
│  │  - Context Precision: >= 0.75                                        │  │
│  │  - Context Recall: >= 0.75                                           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
app/
└── tests/
    ├── __init__.py
    ├── conftest.py           # Shared fixtures
    ├── pytest.ini            # Pytest configuration
    │
    ├── unit/                 # Unit tests
    │   ├── __init__.py
    │   ├── test_models.py
    │   ├── test_config.py
    │   ├── test_chunkers.py
    │   ├── test_embeddings.py
    │   ├── test_feature_controller.py
    │   └── test_degradation_handlers.py
    │
    ├── integration/          # Integration tests
    │   ├── __init__.py
    │   ├── test_api.py
    │   ├── test_database.py
    │   ├── test_rag_pipeline.py
    │   ├── test_streaming.py
    │   └── test_orchestrator.py
    │
    ├── prompts/              # Prompt testing
    │   ├── promptfoo.yaml    # Promptfoo config
    │   ├── test_cases/
    │   │   ├── parameter_extraction.yaml
    │   │   ├── relevance_analysis.yaml
    │   │   └── trace_analysis.yaml
    │   └── assertions/
    │       └── custom_assertions.py
    │
    └── rag/                  # RAG evaluation
        ├── __init__.py
        ├── ragas_eval.py
        ├── datasets/
        │   ├── golden_qa.json
        │   └── retrieval_test.json
        └── metrics.py
```

---

## Pytest Configuration

### File: `app/tests/pytest.ini`

```ini
[pytest]
testpaths = app/tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Markers
markers =
    unit: Unit tests (fast, no external dependencies)
    integration: Integration tests (may use DB, Redis)
    slow: Slow tests (LLM calls, large datasets)
    rag: RAG-specific tests
    prompt: Prompt evaluation tests

# Coverage
addopts =
    --cov=app
    --cov-report=term-missing
    --cov-report=html:coverage_html
    --cov-fail-under=70
    -v

# Async
asyncio_mode = auto

# Timeout
timeout = 120
```

### File: `app/tests/conftest.py`

```python
"""
Shared pytest fixtures for agent-loggy tests.
"""

import os
import pytest
from typing import Generator
from unittest.mock import MagicMock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.db.base import Base
from app.config import settings


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    # Use test database URL or in-memory SQLite
    test_db_url = os.environ.get(
        "TEST_DATABASE_URL",
        "sqlite:///:memory:"
    )

    engine = create_engine(test_db_url)
    Base.metadata.create_all(engine)

    yield engine

    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def db_session(test_engine) -> Generator[Session, None, None]:
    """Create a fresh database session for each test."""
    TestSessionLocal = sessionmaker(bind=test_engine)
    session = TestSessionLocal()

    # Begin a nested transaction
    session.begin_nested()

    yield session

    # Rollback to clean state
    session.rollback()
    session.close()


@pytest.fixture
def db_with_data(db_session):
    """Database session with sample data."""
    from app.db.models import Prompt, ModelConfig, ContextRule

    # Add sample prompt
    prompt = Prompt(
        name="test_prompt",
        project="default",
        version=1,
        template="Test template with {variable}",
        labels=["production"]
    )
    db_session.add(prompt)

    # Add sample model config
    model_config = ModelConfig(
        name="default",
        version=1,
        model_provider="ollama",
        model_name="qwen3:14b",
        labels=["production"]
    )
    db_session.add(model_config)

    # Add sample context rule
    rule = ContextRule(
        context="bkash",
        version=1,
        important="payment,transfer,balance",
        ignore="heartbeat,health_check"
    )
    db_session.add(rule)

    db_session.commit()

    return db_session


# ============================================================================
# MOCK FIXTURES
# ============================================================================

@pytest.fixture
def mock_ollama():
    """Mock Ollama client."""
    mock = MagicMock()
    mock.generate.return_value = {
        "response": '{"time_frame": "2025-01-15", "domain": "bkash", "query_keys": ["payment"]}'
    }
    mock.chat.return_value = {
        "message": {"content": "Analysis complete"}
    }
    return mock


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = MagicMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.setex.return_value = True
    mock.delete.return_value = 1
    mock.keys.return_value = []
    return mock


@pytest.fixture
def mock_embedder():
    """Mock embedding service."""
    import numpy as np

    mock = MagicMock()
    mock.dimension = 1536
    mock.embed.return_value = [np.random.rand(1536).tolist()]
    mock.embed_query.return_value = np.random.rand(1536).tolist()
    return mock


@pytest.fixture
def mock_feature_controller():
    """Mock feature controller with all features enabled."""
    mock = MagicMock()
    mock.is_ai_enabled.return_value = True
    mock.is_enabled.return_value = True
    mock.get_feature_value.return_value = None
    return mock


# ============================================================================
# API FIXTURES
# ============================================================================

@pytest.fixture
def test_client():
    """FastAPI test client."""
    from fastapi.testclient import TestClient
    from app.main import app

    return TestClient(app)


@pytest.fixture
def async_client():
    """Async test client for streaming tests."""
    import httpx
    from app.main import app

    return httpx.AsyncClient(app=app, base_url="http://test")


# ============================================================================
# DATA FIXTURES
# ============================================================================

@pytest.fixture
def sample_log_entries():
    """Sample log entries for testing."""
    return [
        {
            "timestamp": "2025-01-15T10:00:00Z",
            "level": "INFO",
            "service": "payment-service",
            "message": "Processing bKash payment",
            "trace_id": "trace-123"
        },
        {
            "timestamp": "2025-01-15T10:00:01Z",
            "level": "ERROR",
            "service": "payment-service",
            "message": "Payment failed: timeout",
            "trace_id": "trace-123"
        },
        {
            "timestamp": "2025-01-15T10:00:02Z",
            "level": "INFO",
            "service": "notification-service",
            "message": "Sending failure notification",
            "trace_id": "trace-123"
        }
    ]


@pytest.fixture
def sample_chat_request():
    """Sample chat request."""
    return {
        "message": "Show me failed bKash payments from last week",
        "session_id": None
    }


@pytest.fixture
def sample_trace_data():
    """Sample trace data for analysis."""
    return {
        "trace_id": "trace-123",
        "timestamp": "2025-01-15T10:00:00Z",
        "total_entries": 50,
        "services": ["payment-service", "notification-service"],
        "operations": ["processPayment", "sendNotification"],
        "log_samples": [
            "Processing bKash payment for merchant XYZ",
            "Payment amount: 5000 BDT",
            "Error: Connection timeout"
        ]
    }


# ============================================================================
# RAG FIXTURES
# ============================================================================

@pytest.fixture
def rag_test_documents():
    """Sample documents for RAG testing."""
    return [
        {
            "content": "bKash payments are processed through the MFS gateway. Common errors include timeout, insufficient balance, and authentication failures.",
            "source_id": "doc1",
            "source_type": "doc"
        },
        {
            "content": "Transaction failures should be investigated by checking the trace logs for error codes. Error code 5001 indicates timeout.",
            "source_id": "doc2",
            "source_type": "doc"
        },
        {
            "content": "The payment service connects to multiple downstream services including fraud detection, balance check, and notification.",
            "source_id": "doc3",
            "source_type": "doc"
        }
    ]


@pytest.fixture
def golden_qa_dataset():
    """Golden Q&A dataset for RAG evaluation."""
    return [
        {
            "question": "What causes bKash payment timeouts?",
            "ground_truth": "bKash payment timeouts are typically caused by network issues, downstream service delays, or high load on the MFS gateway.",
            "relevant_contexts": ["doc1", "doc2"]
        },
        {
            "question": "What is error code 5001?",
            "ground_truth": "Error code 5001 indicates a timeout in the payment processing.",
            "relevant_contexts": ["doc2"]
        }
    ]
```

---

## Unit Tests

### File: `app/tests/unit/test_models.py`

```python
"""
Unit tests for ORM models.
"""

import pytest
from datetime import datetime

from app.db.models import Prompt, ModelConfig, ContextRule, ConfigChangelog


class TestPromptModel:
    """Tests for Prompt model."""

    def test_create_prompt(self, db_session):
        """Test basic prompt creation."""
        prompt = Prompt(
            name="test_prompt",
            project="default",
            template="Hello {name}!",
            type="chat"
        )
        db_session.add(prompt)
        db_session.flush()

        assert prompt.id is not None
        assert prompt.version == 1
        assert prompt.is_active is True
        assert prompt.created_at is not None

    def test_prompt_versioning(self, db_session):
        """Test multiple versions of same prompt."""
        # Version 1
        v1 = Prompt(
            name="versioned",
            project="default",
            template="v1 template",
            version=1
        )
        db_session.add(v1)

        # Version 2
        v2 = Prompt(
            name="versioned",
            project="default",
            template="v2 template",
            version=2
        )
        db_session.add(v2)
        db_session.flush()

        assert v1.id != v2.id
        assert v1.version == 1
        assert v2.version == 2

    def test_prompt_unique_constraint(self, db_session):
        """Test unique constraint on project+name+version."""
        from sqlalchemy.exc import IntegrityError

        p1 = Prompt(
            name="unique_test",
            project="default",
            template="template1",
            version=1
        )
        db_session.add(p1)
        db_session.flush()

        p2 = Prompt(
            name="unique_test",
            project="default",
            template="template2",
            version=1  # Same version!
        )
        db_session.add(p2)

        with pytest.raises(IntegrityError):
            db_session.flush()

    def test_prompt_labels(self, db_session):
        """Test ARRAY labels field."""
        prompt = Prompt(
            name="labeled",
            project="default",
            template="test",
            labels=["production", "v1", "stable"]
        )
        db_session.add(prompt)
        db_session.flush()

        # Reload
        db_session.refresh(prompt)
        assert "production" in prompt.labels
        assert len(prompt.labels) == 3


class TestModelConfigModel:
    """Tests for ModelConfig model."""

    def test_create_model_config(self, db_session):
        """Test basic model config creation."""
        config = ModelConfig(
            name="default",
            model_provider="ollama",
            model_name="qwen3:14b",
            parameters={"temperature": 0.7}
        )
        db_session.add(config)
        db_session.flush()

        assert config.id is not None
        assert config.parameters["temperature"] == 0.7


class TestContextRuleModel:
    """Tests for ContextRule model."""

    def test_create_context_rule(self, db_session):
        """Test context rule creation."""
        rule = ContextRule(
            context="transactions",
            important="payment,transfer",
            ignore="heartbeat"
        )
        db_session.add(rule)
        db_session.flush()

        assert rule.id is not None
        assert rule.is_active is True


class TestConfigChangelog:
    """Tests for ConfigChangelog model."""

    def test_changelog_entry(self, db_session):
        """Test changelog entry creation."""
        changelog = ConfigChangelog(
            config_type="prompt",
            config_id=1,
            config_name="default:test_prompt",
            previous_version=1,
            new_version=2,
            change_type="update",
            change_summary="Updated template",
            changed_by="test_user"
        )
        db_session.add(changelog)
        db_session.flush()

        assert changelog.id is not None
        assert changelog.changed_at is not None
```

### File: `app/tests/unit/test_chunkers.py`

```python
"""
Unit tests for chunking strategies.
"""

import pytest

from app.rag.chunkers import (
    FixedSizeChunker,
    LogChunker,
    SemanticChunker,
    get_chunker
)


class TestFixedSizeChunker:
    """Tests for FixedSizeChunker."""

    def test_basic_chunking(self):
        """Test basic fixed-size chunking."""
        chunker = FixedSizeChunker(chunk_size=100, chunk_overlap=20)
        text = "word " * 200  # ~200 tokens

        chunks = chunker.chunk(text, "test_doc")

        assert len(chunks) > 1
        assert all(c.source_id == "test_doc" for c in chunks)
        assert all(c.total_chunks == len(chunks) for c in chunks)

    def test_chunk_indices(self):
        """Test chunk indices are sequential."""
        chunker = FixedSizeChunker(chunk_size=50, chunk_overlap=10)
        text = "word " * 100

        chunks = chunker.chunk(text, "test_doc")

        indices = [c.index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_source_hash_consistent(self):
        """Test source hash is consistent."""
        chunker = FixedSizeChunker(chunk_size=50)
        text = "test content"

        chunks1 = chunker.chunk(text, "doc1")
        chunks2 = chunker.chunk(text, "doc1")

        assert chunks1[0].source_hash == chunks2[0].source_hash

    def test_empty_text(self):
        """Test handling of empty text."""
        chunker = FixedSizeChunker(chunk_size=100)
        chunks = chunker.chunk("", "empty_doc")

        assert len(chunks) == 0 or chunks[0].content == ""


class TestLogChunker:
    """Tests for LogChunker."""

    def test_log_entry_preservation(self):
        """Test that log entries are kept intact."""
        chunker = LogChunker(chunk_size=500, max_entries_per_chunk=50)

        logs = """2025-01-15 10:00:00 INFO Starting service
2025-01-15 10:00:01 DEBUG Connection established
2025-01-15 10:00:02 ERROR Failed to authenticate"""

        chunks = chunker.chunk(logs, "test.log")

        # All entries should be in chunks
        full_content = " ".join(c.content for c in chunks)
        assert "Starting service" in full_content
        assert "Connection established" in full_content
        assert "Failed to authenticate" in full_content

    def test_max_entries_per_chunk(self):
        """Test max entries per chunk limit."""
        chunker = LogChunker(chunk_size=10000, max_entries_per_chunk=2)

        logs = """2025-01-15 10:00:00 Entry 1
2025-01-15 10:00:01 Entry 2
2025-01-15 10:00:02 Entry 3
2025-01-15 10:00:03 Entry 4"""

        chunks = chunker.chunk(logs, "test.log")

        # Should split due to max entries, not size
        assert len(chunks) >= 2


class TestChunkerFactory:
    """Tests for chunker factory function."""

    def test_get_fixed_chunker(self):
        """Test getting fixed chunker."""
        chunker = get_chunker("fixed", chunk_size=100)
        assert isinstance(chunker, FixedSizeChunker)

    def test_get_log_chunker(self):
        """Test getting log chunker."""
        chunker = get_chunker("log", chunk_size=500)
        assert isinstance(chunker, LogChunker)

    def test_unknown_strategy_defaults_to_fixed(self):
        """Test unknown strategy returns fixed chunker."""
        chunker = get_chunker("unknown")
        assert isinstance(chunker, FixedSizeChunker)
```

### File: `app/tests/unit/test_feature_controller.py`

```python
"""
Unit tests for feature controller.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.features.ai_feature_controller import (
    AIFeatureController,
    FeatureContext,
    FeatureState
)
from app.features.degradation_handlers import (
    RAGDegradationHandler,
    AnalysisDegradationHandler
)


class TestAIFeatureController:
    """Tests for AIFeatureController."""

    @pytest.fixture
    def controller_with_mock(self):
        """Create controller with mocked Flagsmith."""
        with patch('app.features.ai_feature_controller.Flagsmith') as mock_fs:
            mock_client = MagicMock()
            mock_flags = MagicMock()
            mock_flags.is_feature_enabled.return_value = True
            mock_flags.get_feature_value.return_value = None
            mock_client.get_environment_flags.return_value = mock_flags
            mock_client.get_identity_flags.return_value = mock_flags
            mock_fs.return_value = mock_client

            # Reset singleton
            AIFeatureController._instance = None
            controller = AIFeatureController.get_instance()

            yield controller, mock_flags

            AIFeatureController._instance = None

    def test_singleton_pattern(self, controller_with_mock):
        """Test singleton returns same instance."""
        controller1, _ = controller_with_mock
        controller2 = AIFeatureController.get_instance()

        assert controller1 is controller2

    def test_master_switch_enabled(self, controller_with_mock):
        """Test master switch returns True when enabled."""
        controller, mock_flags = controller_with_mock
        mock_flags.is_feature_enabled.return_value = True

        assert controller.is_ai_enabled() is True

    def test_master_switch_disabled(self, controller_with_mock):
        """Test master switch returns False when disabled."""
        controller, mock_flags = controller_with_mock
        mock_flags.is_feature_enabled.return_value = False

        assert controller.is_ai_enabled() is False

    def test_feature_blocked_by_master_switch(self, controller_with_mock):
        """Test individual feature blocked when master switch is off."""
        controller, mock_flags = controller_with_mock

        def side_effect(flag_name):
            if flag_name == "ai_master_switch":
                return False
            return True

        mock_flags.is_feature_enabled.side_effect = side_effect

        assert controller.is_enabled("rag") is False

    def test_feature_enabled_when_master_on(self, controller_with_mock):
        """Test feature enabled when master switch is on."""
        controller, mock_flags = controller_with_mock
        mock_flags.is_feature_enabled.return_value = True

        assert controller.is_enabled("rag") is True

    def test_user_context_passed_to_flagsmith(self, controller_with_mock):
        """Test user context is passed for identity flags."""
        controller, mock_flags = controller_with_mock

        context = FeatureContext(
            user_id="user123",
            traits={"plan": "premium"}
        )

        controller.is_enabled("rag", context)

        # Verify identity flags were requested
        controller.client.get_identity_flags.assert_called()

    def test_get_all_feature_states(self, controller_with_mock):
        """Test getting all feature states."""
        controller, mock_flags = controller_with_mock
        mock_flags.is_feature_enabled.return_value = True

        states = controller.get_all_feature_states()

        assert "ai_master_switch" in states
        assert "rag" in states
        assert states["rag"]["enabled"] is True


class TestDegradationHandlers:
    """Tests for degradation handlers."""

    def test_rag_degradation_handler(self):
        """Test RAG degradation returns proper response."""
        handler = RAGDegradationHandler()
        result = handler.handle(query="test query")

        assert result["status"] == "degraded"
        assert result["results"] == []
        assert "message" in result

    def test_analysis_degradation_handler(self):
        """Test analysis degradation computes basic stats."""
        handler = AnalysisDegradationHandler()

        log_entries = [
            {"message": "error occurred", "level": "ERROR"},
            {"message": "warning issued", "level": "WARN"},
            {"message": "info message", "level": "INFO"}
        ]

        result = handler.handle(
            trace_id="trace123",
            log_entries=log_entries
        )

        assert result["status"] == "degraded"
        assert result["statistics"]["total_entries"] == 3
        assert result["statistics"]["error_count"] == 1
        assert result["statistics"]["warning_count"] == 1

    def test_analysis_degradation_empty_logs(self):
        """Test analysis degradation with no logs."""
        handler = AnalysisDegradationHandler()

        result = handler.handle(trace_id="trace123", log_entries=[])

        assert result["statistics"]["total_entries"] == 0
```

---

## Integration Tests

### File: `app/tests/integration/test_api.py`

```python
"""
Integration tests for API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestChatAPI:
    """Tests for chat API endpoints."""

    def test_chat_endpoint_success(self, test_client, mock_ollama):
        """Test successful chat request."""
        with patch('app.orchestrator.Client', return_value=mock_ollama):
            response = test_client.post("/api/chat", json={
                "message": "Show me bKash payments from yesterday"
            })

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data

    def test_chat_endpoint_empty_message(self, test_client):
        """Test chat with empty message."""
        response = test_client.post("/api/chat", json={
            "message": ""
        })

        assert response.status_code == 422  # Validation error

    def test_chat_endpoint_with_session(self, test_client, mock_ollama):
        """Test chat with existing session."""
        # First request creates session
        with patch('app.orchestrator.Client', return_value=mock_ollama):
            response1 = test_client.post("/api/chat", json={
                "message": "First message"
            })
            session_id = response1.json()["session_id"]

            # Second request uses session
            response2 = test_client.post("/api/chat", json={
                "message": "Second message",
                "session_id": session_id
            })

        assert response2.status_code == 200


class TestConfigAPI:
    """Tests for configuration API endpoints."""

    def test_list_prompts(self, test_client, db_with_data):
        """Test listing prompts."""
        response = test_client.get("/api/config/prompts")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_prompt(self, test_client, db_with_data):
        """Test getting specific prompt."""
        response = test_client.get("/api/config/prompts/test_prompt")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_prompt"

    def test_get_nonexistent_prompt(self, test_client, db_with_data):
        """Test getting nonexistent prompt returns 404."""
        response = test_client.get("/api/config/prompts/nonexistent")

        assert response.status_code == 404

    def test_create_prompt(self, test_client, db_session):
        """Test creating a new prompt."""
        response = test_client.post("/api/config/prompts", json={
            "name": "new_prompt",
            "template": "New template content",
            "labels": ["staging"]
        })

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "new_prompt"
        assert data["version"] == 1


class TestFeatureAPI:
    """Tests for feature flag API endpoints."""

    def test_get_feature_status(self, test_client):
        """Test getting all feature statuses."""
        response = test_client.get("/api/features/status")

        assert response.status_code == 200
        data = response.json()
        assert "features" in data

    def test_check_specific_feature(self, test_client):
        """Test checking specific feature."""
        response = test_client.get("/api/features/check/rag")

        assert response.status_code == 200
        data = response.json()
        assert data["feature"] == "rag"
        assert "enabled" in data

    def test_refresh_flags(self, test_client):
        """Test refreshing feature flags."""
        response = test_client.post("/api/features/refresh")

        assert response.status_code == 200
        assert response.json()["status"] == "refreshed"
```

### File: `app/tests/integration/test_rag_pipeline.py`

```python
"""
Integration tests for RAG pipeline.
"""

import pytest
from unittest.mock import patch

from app.rag.indexer import RAGIndexer
from app.rag.retrieval import HybridRetriever, RAGPipeline


class TestRAGIndexing:
    """Tests for RAG indexing."""

    def test_index_document(self, db_session, mock_embedder):
        """Test indexing a document."""
        with patch('app.rag.indexer.get_embedder', return_value=mock_embedder):
            indexer = RAGIndexer(db_session)

            chunks = indexer.index_document(
                content="Test document content for RAG indexing.",
                source_id="test_doc.txt",
                source_type="doc"
            )

        assert len(chunks) >= 1
        assert chunks[0].source_id == "test_doc.txt"
        assert chunks[0].embedding is not None

    def test_reindex_same_content_skipped(self, db_session, mock_embedder):
        """Test that same content is not re-indexed."""
        with patch('app.rag.indexer.get_embedder', return_value=mock_embedder):
            indexer = RAGIndexer(db_session)

            content = "Same content"
            indexer.index_document(content, "doc1", "doc")

            # Reset mock call count
            mock_embedder.embed.reset_mock()

            # Index same content
            indexer.index_document(content, "doc1", "doc")

            # Should not call embed again
            mock_embedder.embed.assert_not_called()

    def test_force_reindex(self, db_session, mock_embedder):
        """Test force reindex."""
        with patch('app.rag.indexer.get_embedder', return_value=mock_embedder):
            indexer = RAGIndexer(db_session)

            content = "Content to reindex"
            indexer.index_document(content, "doc1", "doc")

            mock_embedder.embed.reset_mock()

            # Force reindex
            indexer.index_document(content, "doc1", "doc", force_reindex=True)

            # Should call embed again
            mock_embedder.embed.assert_called()


class TestRAGRetrieval:
    """Tests for RAG retrieval."""

    @pytest.fixture
    def indexed_documents(self, db_session, mock_embedder, rag_test_documents):
        """Index test documents for retrieval tests."""
        with patch('app.rag.indexer.get_embedder', return_value=mock_embedder):
            indexer = RAGIndexer(db_session)

            for doc in rag_test_documents:
                indexer.index_document(
                    content=doc["content"],
                    source_id=doc["source_id"],
                    source_type=doc["source_type"]
                )

        return db_session

    def test_vector_search(self, indexed_documents, mock_embedder):
        """Test vector similarity search."""
        with patch('app.rag.retrieval.get_embedder', return_value=mock_embedder):
            retriever = HybridRetriever(indexed_documents, mock_embedder)

            results = retriever._vector_search("bkash payment error", top_k=5)

        assert len(results) > 0

    def test_hybrid_search(self, indexed_documents, mock_embedder):
        """Test hybrid search combining vector and BM25."""
        with patch('app.rag.retrieval.get_embedder', return_value=mock_embedder):
            retriever = HybridRetriever(indexed_documents, mock_embedder)

            results = retriever.search("payment timeout error", top_k=5)

        assert len(results) > 0
        assert all(hasattr(r, 'score') for r in results)

    def test_source_type_filter(self, indexed_documents, mock_embedder):
        """Test filtering by source type."""
        with patch('app.rag.retrieval.get_embedder', return_value=mock_embedder):
            retriever = HybridRetriever(indexed_documents, mock_embedder)

            results = retriever.search(
                "payment",
                top_k=10,
                source_types=["doc"]
            )

        assert all(r.source_type == "doc" for r in results)
```

---

## Promptfoo Configuration

### File: `app/tests/prompts/promptfoo.yaml`

```yaml
# Promptfoo configuration for prompt evaluation

description: Agent-loggy prompt evaluation

prompts:
  - id: parameter_extraction
    label: Parameter Extraction v1
    file: prompts/parameter_extraction.txt

  - id: relevance_analysis
    label: Relevance Analysis v1
    file: prompts/relevance_analysis.txt

providers:
  - id: ollama:qwen3:14b
    config:
      temperature: 0
      num_predict: 500

defaultTest:
  options:
    provider: ollama:qwen3:14b
    timeout: 60000

tests:
  # Parameter Extraction Tests
  - description: "Extract bKash payment parameters"
    vars:
      user_input: "Show me failed bKash payments from last week"
      allowed_query_keys: "payment,bkash,mfs,amount,merchant"
      excluded_query_keys: "internal_id,debug_info"
      allowed_domains: "payments,transactions,mfs"
      excluded_domains: "internal,debug"
    assert:
      - type: is-json
      - type: javascript
        value: "output.domain === 'payments' || output.domain === 'mfs'"
      - type: contains-json
        value:
          query_keys: ["bkash"]
      - type: llm-rubric
        value: "The output correctly identifies bKash-related parameters"

  - description: "Handle ambiguous time frame"
    vars:
      user_input: "Get all transactions"
      allowed_query_keys: "transaction,amount,merchant"
      excluded_query_keys: ""
      allowed_domains: "transactions"
      excluded_domains: ""
    assert:
      - type: is-json
      - type: javascript
        value: "output.time_frame === null"

  - description: "Extract multiple query keys"
    vars:
      user_input: "Find merchant transactions over 500 from January"
      allowed_query_keys: "transaction,amount,merchant,date"
      excluded_query_keys: ""
      allowed_domains: "transactions"
      excluded_domains: ""
    assert:
      - type: is-json
      - type: javascript
        value: "output.query_keys.includes('merchant') && output.query_keys.includes('amount')"
      - type: javascript
        value: "output.time_frame && output.time_frame.startsWith('2025-01')"

  # Relevance Analysis Tests
  - description: "Identify relevant trace"
    vars:
      trace_id: "trace-123"
      domain: "payments"
      query_keys: ["bkash", "payment"]
      log_samples: |
        Processing bKash payment
        Amount: 5000 BDT
        Status: COMPLETED
    assert:
      - type: is-json
      - type: javascript
        value: "output.relevance_score >= 70"
      - type: javascript
        value: "output.domain_match === true"

  - description: "Identify irrelevant trace"
    vars:
      trace_id: "trace-456"
      domain: "payments"
      query_keys: ["bkash", "payment"]
      log_samples: |
        Health check ping
        System status: OK
        Heartbeat received
    assert:
      - type: is-json
      - type: javascript
        value: "output.relevance_score <= 30"
      - type: javascript
        value: "output.recommendation.includes('EXCLUDE')"

# Evaluation thresholds
evaluateOptions:
  maxConcurrency: 2

# Output configuration
outputPath: ./promptfoo_results.json
```

### File: `app/tests/prompts/test_cases/parameter_extraction.yaml`

```yaml
# Additional test cases for parameter extraction prompt

tests:
  - description: "Edge case: Future date"
    vars:
      user_input: "Show me payments scheduled for next month"
    assert:
      - type: is-json
      - type: javascript
        value: "output.time_frame === null || new Date(output.time_frame) > new Date()"

  - description: "Edge case: Specific date format"
    vars:
      user_input: "Get transactions from 2025-01-15"
    assert:
      - type: is-json
      - type: javascript
        value: "output.time_frame === '2025-01-15'"

  - description: "Edge case: Excluded domain in input"
    vars:
      user_input: "Show internal debug logs"
      excluded_domains: "internal,debug"
    assert:
      - type: is-json
      - type: not-contains
        value: "internal"

  - description: "Stress test: Long input"
    vars:
      user_input: |
        I need to investigate a complex issue with our payment system.
        The customer reported that their bKash payment failed multiple times
        over the past week. They were trying to pay a merchant for electronics.
        The transaction amounts were around 15000 BDT each time.
        Can you help me find the relevant logs?
    assert:
      - type: is-json
      - type: javascript
        value: "output.domain === 'payments' || output.domain === 'mfs'"
      - type: javascript
        value: "output.query_keys.length >= 2"

  - description: "Consistency check: Same input, same output"
    repeat: 3
    vars:
      user_input: "Show bKash payments"
    assert:
      - type: is-json
      - type: similar
        value: '{"domain": "payments", "query_keys": ["bkash"]}'
        threshold: 0.9
```

---

## RAGAS Evaluation

### File: `app/tests/rag/ragas_eval.py`

```python
"""
RAGAS evaluation for RAG pipeline quality.

Implements the RAG Triad metrics:
- Context Relevance: Are retrieved contexts relevant?
- Groundedness: Is the answer supported by context?
- Answer Relevance: Does the answer address the question?
"""

import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from pathlib import Path

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
    context_relevancy,
)
from datasets import Dataset

from app.rag.retrieval import RAGPipeline
from app.db.session import get_db_session

logger = logging.getLogger(__name__)


@dataclass
class RAGASResult:
    """Container for RAGAS evaluation results."""
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    context_recall: float
    context_relevancy: float
    overall_score: float
    detailed_results: List[Dict[str, Any]]


class RAGEvaluator:
    """
    Evaluates RAG pipeline using RAGAS metrics.

    Usage:
        evaluator = RAGEvaluator()
        results = evaluator.evaluate_from_file("golden_qa.json")
        print(f"Overall score: {results.overall_score}")
    """

    # Target thresholds for quality gates
    THRESHOLDS = {
        "faithfulness": 0.8,
        "answer_relevancy": 0.8,
        "context_precision": 0.75,
        "context_recall": 0.75,
        "context_relevancy": 0.8,
    }

    def __init__(self, rag_pipeline: Optional[RAGPipeline] = None):
        """
        Initialize evaluator.

        Args:
            rag_pipeline: Optional RAG pipeline instance
        """
        if rag_pipeline:
            self.pipeline = rag_pipeline
        else:
            with get_db_session() as session:
                self.pipeline = RAGPipeline(session)

    def evaluate_from_file(self, dataset_path: str) -> RAGASResult:
        """
        Evaluate RAG using a golden Q&A dataset file.

        Args:
            dataset_path: Path to JSON file with questions and ground truths

        Returns:
            RAGASResult with all metrics
        """
        with open(dataset_path, 'r') as f:
            qa_data = json.load(f)

        return self.evaluate(qa_data)

    def evaluate(self, qa_data: List[Dict]) -> RAGASResult:
        """
        Evaluate RAG pipeline on Q&A data.

        Args:
            qa_data: List of dicts with 'question' and 'ground_truth' keys

        Returns:
            RAGASResult with all metrics
        """
        # Prepare evaluation dataset
        questions = []
        ground_truths = []
        answers = []
        contexts = []

        for item in qa_data:
            question = item["question"]
            ground_truth = item["ground_truth"]

            # Get RAG response
            rag_results = self.pipeline.search(question)
            context_texts = [r.content for r in rag_results]

            # Generate answer (simplified - in production would use full LLM)
            answer = self._generate_answer(question, context_texts)

            questions.append(question)
            ground_truths.append([ground_truth])  # RAGAS expects list
            answers.append(answer)
            contexts.append(context_texts)

        # Create HuggingFace dataset
        dataset = Dataset.from_dict({
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        })

        # Run RAGAS evaluation
        result = evaluate(
            dataset,
            metrics=[
                faithfulness,
                answer_relevancy,
                context_precision,
                context_recall,
                context_relevancy,
            ]
        )

        # Convert to RAGASResult
        return RAGASResult(
            faithfulness=result["faithfulness"],
            answer_relevancy=result["answer_relevancy"],
            context_precision=result["context_precision"],
            context_recall=result["context_recall"],
            context_relevancy=result["context_relevancy"],
            overall_score=self._compute_overall(result),
            detailed_results=result.to_pandas().to_dict(orient="records")
        )

    def _generate_answer(self, question: str, contexts: List[str]) -> str:
        """
        Generate answer using retrieved contexts.

        In production, this would use the full LLM pipeline.
        """
        # Simplified answer generation
        context_str = "\n".join(contexts[:3])
        return f"Based on the context: {context_str[:500]}..."

    def _compute_overall(self, result: Dict) -> float:
        """Compute weighted overall score."""
        weights = {
            "faithfulness": 0.25,
            "answer_relevancy": 0.25,
            "context_precision": 0.2,
            "context_recall": 0.15,
            "context_relevancy": 0.15,
        }

        score = sum(
            result[metric] * weight
            for metric, weight in weights.items()
        )

        return round(score, 3)

    def check_quality_gates(self, result: RAGASResult) -> Dict[str, bool]:
        """
        Check if results meet quality thresholds.

        Returns:
            Dict mapping metric name to pass/fail
        """
        return {
            "faithfulness": result.faithfulness >= self.THRESHOLDS["faithfulness"],
            "answer_relevancy": result.answer_relevancy >= self.THRESHOLDS["answer_relevancy"],
            "context_precision": result.context_precision >= self.THRESHOLDS["context_precision"],
            "context_recall": result.context_recall >= self.THRESHOLDS["context_recall"],
            "context_relevancy": result.context_relevancy >= self.THRESHOLDS["context_relevancy"],
        }

    def passes_all_gates(self, result: RAGASResult) -> bool:
        """Check if all quality gates pass."""
        gates = self.check_quality_gates(result)
        return all(gates.values())


def run_ragas_evaluation(dataset_path: str = "app/tests/rag/datasets/golden_qa.json"):
    """
    CLI function to run RAGAS evaluation.

    Usage:
        python -m app.tests.rag.ragas_eval
    """
    evaluator = RAGEvaluator()
    result = evaluator.evaluate_from_file(dataset_path)

    print("\n=== RAGAS Evaluation Results ===")
    print(f"Faithfulness:       {result.faithfulness:.3f} (threshold: {evaluator.THRESHOLDS['faithfulness']})")
    print(f"Answer Relevancy:   {result.answer_relevancy:.3f} (threshold: {evaluator.THRESHOLDS['answer_relevancy']})")
    print(f"Context Precision:  {result.context_precision:.3f} (threshold: {evaluator.THRESHOLDS['context_precision']})")
    print(f"Context Recall:     {result.context_recall:.3f} (threshold: {evaluator.THRESHOLDS['context_recall']})")
    print(f"Context Relevancy:  {result.context_relevancy:.3f} (threshold: {evaluator.THRESHOLDS['context_relevancy']})")
    print(f"\nOverall Score:      {result.overall_score:.3f}")

    gates = evaluator.check_quality_gates(result)
    print("\n=== Quality Gates ===")
    for metric, passed in gates.items():
        status = "PASS" if passed else "FAIL"
        print(f"  {metric}: {status}")

    if evaluator.passes_all_gates(result):
        print("\n All quality gates PASSED")
        return 0
    else:
        print("\n Some quality gates FAILED")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(run_ragas_evaluation())
```

---

## CI/CD Pipeline

### File: `.github/workflows/test.yml`

```yaml
name: Test Suite

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: "3.11"

jobs:
  lint:
    name: Lint & Format
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install linters
        run: |
          pip install ruff black isort mypy

      - name: Run ruff
        run: ruff check app/

      - name: Check black formatting
        run: black --check app/

      - name: Check import sorting
        run: isort --check-only app/

      - name: Run mypy
        run: mypy app/ --ignore-missing-imports

  unit-tests:
    name: Unit Tests
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio

      - name: Run unit tests
        run: |
          pytest app/tests/unit/ \
            --cov=app \
            --cov-report=xml \
            --cov-fail-under=70 \
            -v

      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with:
          files: ./coverage.xml
          fail_ci_if_error: true

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest
    needs: unit-tests
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_DB: test_agent_loggy
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio httpx

      - name: Run integration tests
        env:
          TEST_DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_agent_loggy
          REDIS_URL: redis://localhost:6379/0
        run: |
          pytest app/tests/integration/ -v --tb=short

  prompt-evaluation:
    name: Prompt Evaluation
    runs-on: ubuntu-latest
    needs: unit-tests
    if: github.event_name == 'pull_request'
    steps:
      - uses: actions/checkout@v4

      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Install promptfoo
        run: npm install -g promptfoo

      - name: Run prompt evaluation
        env:
          OLLAMA_HOST: ${{ secrets.OLLAMA_HOST }}
        run: |
          cd app/tests/prompts
          promptfoo eval --config promptfoo.yaml --output results.json

      - name: Check pass rate
        run: |
          PASS_RATE=$(cat app/tests/prompts/results.json | jq '.results.stats.passRate')
          echo "Pass rate: $PASS_RATE"
          if (( $(echo "$PASS_RATE < 0.8" | bc -l) )); then
            echo "Prompt evaluation pass rate below 80%"
            exit 1
          fi

      - name: Upload results
        uses: actions/upload-artifact@v4
        with:
          name: promptfoo-results
          path: app/tests/prompts/results.json

  rag-evaluation:
    name: RAG Quality Evaluation
    runs-on: ubuntu-latest
    needs: integration-tests
    if: github.event_name == 'pull_request'
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_DB: test_agent_loggy
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install ragas datasets

      - name: Run RAGAS evaluation
        env:
          TEST_DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_agent_loggy
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          python -m app.tests.rag.ragas_eval

      - name: Upload RAGAS results
        uses: actions/upload-artifact@v4
        with:
          name: ragas-results
          path: app/tests/rag/ragas_results.json

  all-tests-passed:
    name: All Tests Passed
    runs-on: ubuntu-latest
    needs: [lint, unit-tests, integration-tests]
    steps:
      - name: All tests passed
        run: echo "All required tests passed!"
```

---

## File-by-File Implementation Steps

| Step | File | Action | Description |
|------|------|--------|-------------|
| 1 | `requirements.txt` | MODIFY | Add test dependencies |
| 2 | `app/tests/__init__.py` | CREATE | Package init |
| 3 | `app/tests/pytest.ini` | CREATE | Pytest configuration |
| 4 | `app/tests/conftest.py` | CREATE | Shared fixtures |
| 5 | `app/tests/unit/__init__.py` | CREATE | Unit test package |
| 6 | `app/tests/unit/test_models.py` | CREATE | Model tests |
| 7 | `app/tests/unit/test_chunkers.py` | CREATE | Chunker tests |
| 8 | `app/tests/unit/test_feature_controller.py` | CREATE | Feature tests |
| 9 | `app/tests/integration/__init__.py` | CREATE | Integration package |
| 10 | `app/tests/integration/test_api.py` | CREATE | API tests |
| 11 | `app/tests/integration/test_rag_pipeline.py` | CREATE | RAG tests |
| 12 | `app/tests/prompts/promptfoo.yaml` | CREATE | Promptfoo config |
| 13 | `app/tests/rag/ragas_eval.py` | CREATE | RAGAS evaluation |
| 14 | `app/tests/rag/datasets/golden_qa.json` | CREATE | Test dataset |
| 15 | `.github/workflows/test.yml` | CREATE | CI/CD pipeline |
| 16 | `pyproject.toml` | MODIFY | Add test config |

---

## Dependencies to Add

```txt
# requirements.txt additions for Phase 5

# Testing
pytest>=8.0.0
pytest-cov>=4.1.0
pytest-asyncio>=0.23.0
pytest-timeout>=2.2.0
httpx>=0.25.0

# Mocking
pytest-mock>=3.12.0

# RAG Evaluation
ragas>=0.1.0
datasets>=2.16.0

# Linting
ruff>=0.1.0
black>=23.0.0
isort>=5.12.0
mypy>=1.7.0

# Promptfoo (Node.js - install via npm)
# npm install -g promptfoo
```

---

## Test Data

### File: `app/tests/rag/datasets/golden_qa.json`

```json
[
  {
    "question": "What causes bKash payment timeouts?",
    "ground_truth": "bKash payment timeouts are typically caused by network connectivity issues between the payment service and the MFS gateway, downstream service delays, or high load on the MFS gateway during peak hours.",
    "relevant_contexts": ["doc1", "doc2"]
  },
  {
    "question": "What is error code 5001?",
    "ground_truth": "Error code 5001 indicates a timeout occurred during payment processing, typically at the MFS gateway communication layer.",
    "relevant_contexts": ["doc2"]
  },
  {
    "question": "How do I investigate a failed transaction?",
    "ground_truth": "To investigate a failed transaction, check the trace logs for the transaction's trace ID, look for error codes and timestamps, identify which service in the chain failed, and review the specific error messages.",
    "relevant_contexts": ["doc1", "doc2", "doc3"]
  },
  {
    "question": "What services are involved in payment processing?",
    "ground_truth": "Payment processing involves multiple services including the payment service, fraud detection, balance check service, MFS gateway for mobile wallets, and notification service for status updates.",
    "relevant_contexts": ["doc3"]
  },
  {
    "question": "How to identify a bKash authentication failure?",
    "ground_truth": "bKash authentication failures are identified by error codes in the 4xxx range, typically showing 'AUTH_FAILED' or 'OTP_EXPIRED' in the log messages along with the failed authentication attempt timestamp.",
    "relevant_contexts": ["doc1"]
  }
]
```

---

## Acceptance Criteria

| Criterion | Verification Procedure |
|-----------|------------------------|
| Pytest runs | `pytest app/tests/unit/ -v` passes |
| Coverage >= 70% | `pytest --cov=app --cov-fail-under=70` passes |
| Integration tests pass | `pytest app/tests/integration/ -v` passes |
| Promptfoo runs | `npx promptfoo eval` completes |
| Prompt pass rate >= 80% | Check promptfoo results JSON |
| RAGAS evaluation runs | `python -m app.tests.rag.ragas_eval` completes |
| Quality gates pass | All RAGAS metrics meet thresholds |
| CI pipeline works | GitHub Actions workflow succeeds |
| Coverage reports generated | HTML coverage in `coverage_html/` |

---

## Critical Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `app/tests/conftest.py` | All | NEW - Shared fixtures |
| `app/tests/pytest.ini` | All | NEW - Pytest configuration |
| `app/tests/unit/test_*.py` | All | NEW - Unit test files |
| `app/tests/integration/test_*.py` | All | NEW - Integration tests |
| `app/tests/prompts/promptfoo.yaml` | All | NEW - Prompt evaluation config |
| `app/tests/rag/ragas_eval.py` | All | NEW - RAGAS evaluation |
| `.github/workflows/test.yml` | All | NEW - CI/CD pipeline |

---

## Quality Metrics Dashboard

After implementation, track these metrics:

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Code Coverage | >= 70% | TBD | - |
| Unit Test Count | >= 50 | TBD | - |
| Integration Test Count | >= 20 | TBD | - |
| Prompt Pass Rate | >= 80% | TBD | - |
| RAGAS Faithfulness | >= 0.8 | TBD | - |
| RAGAS Answer Relevancy | >= 0.8 | TBD | - |
| RAGAS Context Precision | >= 0.75 | TBD | - |
| CI Pipeline Success Rate | >= 95% | TBD | - |
