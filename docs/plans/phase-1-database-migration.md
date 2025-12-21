# Phase 1: Database Migration Plan

## Executive Summary

This phase establishes the database foundation for agent-loggy by creating ORM models for prompts, model configurations, embedding configurations, context rules, and audit logs. The existing SQL schema includes a `prompts` table with pgvector support, but it's unused. This migration will create Python ORM models, a session factory, and migrate hardcoded prompts from agent code to the database.

**Timeline**: Week 1-2
**Dependencies**: None (foundation phase)
**Blocking**: Phase 2, 3, 4, 5

---

## Current State Analysis

### What Exists
| Component | Location | Status |
|-----------|----------|--------|
| SQLAlchemy Base | `app/db/base.py` | Empty (only DeclarativeBase) |
| SQL Schema | `alembic/versions/setup_database.sql` | 6 tables defined, pgvector enabled |
| Alembic Config | `alembic/env.py` | Working, reads from app.config |
| Prompts Table | SQL schema | EXISTS but UNUSED |

### What's Missing
- ORM model classes for all tables
- Session factory and connection pooling
- Active code using the database
- Prompt versioning system
- Audit trail for configuration changes

### Hardcoded Prompts to Migrate

| Prompt Name | Source File | Lines | Size |
|-------------|-------------|-------|------|
| `parameter_extraction` | `app/agents/parameter_agent.py` | 166-193 | ~1,600 chars |
| `relevance_analysis` | `app/agents/verify_agent.py` | 425-478 | ~1,200 chars |
| `trace_analysis` | `app/agents/analyze_agent.py` | 235-286 | ~1,000 chars |
| `trace_entry_analysis` | `app/agents/analyze_agent.py` | 335-362 | ~800 chars |
| `quality_assessment` | `app/agents/analyze_agent.py` | 396-416 | ~500 chars |

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Parameter   │  │ Verify      │  │ Analyze             │  │
│  │ Agent       │  │ Agent       │  │ Agent               │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │             │
│         └────────────────┼─────────────────────┘             │
│                          ▼                                   │
│              ┌───────────────────────┐                       │
│              │   ConfigurationManager │ (Phase 2)            │
│              └───────────┬───────────┘                       │
└──────────────────────────┼───────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Repository Layer                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Prompt      │  │ ModelConfig │  │ ContextRule         │  │
│  │ Repository  │  │ Repository  │  │ Repository          │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
└─────────┼────────────────┼─────────────────────┼─────────────┘
          └────────────────┼─────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                     Database Layer                           │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                  SessionFactory                        │  │
│  │  - Connection pooling (pool_size=5, max_overflow=10)  │  │
│  │  - Context manager for transactions                   │  │
│  └───────────────────────────────────────────────────────┘  │
│                           │                                  │
│                           ▼                                  │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              PostgreSQL + pgvector                     │  │
│  │  ┌─────────┐ ┌─────────────┐ ┌───────────────────┐   │  │
│  │  │ prompts │ │model_configs│ │ context_rules     │   │  │
│  │  └─────────┘ └─────────────┘ └───────────────────┘   │  │
│  │  ┌─────────────────┐ ┌───────────────────────────┐   │  │
│  │  │embedding_configs│ │ config_changelog          │   │  │
│  │  └─────────────────┘ └───────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Database Schema (ORM Models)

### File: `app/db/models.py`

```python
"""
ORM Models for agent-loggy configuration management.
"""

from datetime import datetime
from typing import Optional, List, Any
from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, Float,
    ForeignKey, UniqueConstraint, Index, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from pgvector.sqlalchemy import Vector

from app.db.base import Base


class Prompt(Base):
    """
    Versioned prompt templates used by agents.
    Supports labels for environment-based selection (production, staging, etc.)
    """
    __tablename__ = "prompts"
    __table_args__ = (
        UniqueConstraint('project', 'name', 'version', name='uq_prompt_project_name_version'),
        Index('idx_prompts_project_name', 'project', 'name'),
        Index('idx_prompts_labels', 'labels', postgresql_using='gin'),
        {"schema": "agent_loggy"}
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project: Mapped[str] = mapped_column(String(100), nullable=False, default="default")
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    type: Mapped[str] = mapped_column(String(50), nullable=False, default="chat")
    template: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    usage: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    parameters: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector(384), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    labels: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )
    created_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    def __repr__(self):
        return f"<Prompt(name='{self.name}', version={self.version})>"


class ModelConfig(Base):
    """
    Configuration for different LLM models used by agents.
    """
    __tablename__ = "model_configs"
    __table_args__ = (
        UniqueConstraint('name', 'version', name='uq_model_config_name_version'),
        Index('idx_model_configs_name', 'name'),
        {"schema": "agent_loggy"}
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    model_provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    parameters: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    labels: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )

    def __repr__(self):
        return f"<ModelConfig(name='{self.name}', provider='{self.model_provider}')>"


class EmbeddingConfig(Base):
    """
    Configuration for embedding models and chunking strategies.
    """
    __tablename__ = "embedding_configs"
    __table_args__ = (
        UniqueConstraint('name', 'version', name='uq_embedding_config_name_version'),
        Index('idx_embedding_configs_name', 'name'),
        {"schema": "agent_loggy"}
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    embedding_model: Mapped[str] = mapped_column(String(100), nullable=False)
    chunk_size: Mapped[int] = mapped_column(Integer, default=512)
    chunk_overlap: Mapped[int] = mapped_column(Integer, default=50)
    chunking_strategy: Mapped[str] = mapped_column(String(50), default="late_chunking")
    parameters: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )

    def __repr__(self):
        return f"<EmbeddingConfig(name='{self.name}', model='{self.embedding_model}')>"


class ContextRule(Base):
    """
    Domain-specific context rules for RAG filtering.
    Migrated from app/app_settings/context_rules.csv
    """
    __tablename__ = "context_rules"
    __table_args__ = (
        UniqueConstraint('context', 'version', name='uq_context_rule_context_version'),
        Index('idx_context_rules_context', 'context'),
        {"schema": "agent_loggy"}
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    context: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    important: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ignore: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    embedding: Mapped[Optional[Any]] = mapped_column(Vector(384), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )

    def __repr__(self):
        return f"<ContextRule(context='{self.context}', version={self.version})>"


class NegateKey(Base):
    """
    Keys/patterns to exclude from Loki log queries.
    Migrated from app/app_settings/negate_keys.csv
    """
    __tablename__ = "negate_keys"
    __table_args__ = (
        UniqueConstraint('label', 'operator', 'value', 'version', name='uq_negate_key'),
        Index('idx_negate_keys_label', 'label'),
        {"schema": "agent_loggy"}
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    operator: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp()
    )

    def __repr__(self):
        return f"<NegateKey(label='{self.label}', value='{self.value}')>"


class ConfigChangelog(Base):
    """
    Audit trail for all configuration changes.
    """
    __tablename__ = "config_changelog"
    __table_args__ = (
        Index('idx_changelog_config_type_id', 'config_type', 'config_id'),
        Index('idx_changelog_changed_at', 'changed_at'),
        {"schema": "agent_loggy"}
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    config_type: Mapped[str] = mapped_column(String(50), nullable=False)
    config_id: Mapped[int] = mapped_column(Integer, nullable=False)
    config_name: Mapped[str] = mapped_column(String(255), nullable=False)
    previous_version: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    new_version: Mapped[int] = mapped_column(Integer, nullable=False)
    change_type: Mapped[str] = mapped_column(String(20), nullable=False)
    change_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    previous_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    new_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    changed_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=func.current_timestamp())

    def __repr__(self):
        return f"<ConfigChangelog(type='{self.config_type}', name='{self.config_name}')>"
```

---

### File: `app/db/session.py`

```python
"""
Database session factory and connection management.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import settings


# Create engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,      # Verify connections before use
    pool_size=5,             # Base pool size
    max_overflow=10,         # Additional connections allowed
    pool_recycle=3600,       # Recycle connections after 1 hour
    echo=False               # Set True for SQL debugging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    Handles commit/rollback automatically.

    Usage:
        with get_db_session() as session:
            session.query(Prompt).all()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI endpoints.

    Usage:
        @app.get("/prompts")
        def get_prompts(db: Session = Depends(get_db)):
            return db.query(Prompt).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

---

### File: `app/db/base.py` (Updated)

```python
"""
SQLAlchemy declarative base and model imports.
All models must be imported here for Alembic autogenerate to work.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# Import all models here for Alembic autogenerate
from app.db.models import (
    Prompt,
    ModelConfig,
    EmbeddingConfig,
    ContextRule,
    NegateKey,
    ConfigChangelog
)

__all__ = [
    'Base',
    'Prompt',
    'ModelConfig',
    'EmbeddingConfig',
    'ContextRule',
    'NegateKey',
    'ConfigChangelog'
]
```

---

## Alembic Migration

### File: `alembic/versions/[timestamp]_add_orm_config_tables.py`

```python
"""Add ORM configuration tables

Revision ID: [auto-generated]
Revises: 1b671ff38c8c
Create Date: [auto-generated]
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector


revision = '[auto-generated]'
down_revision = '1b671ff38c8c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create prompts table
    op.create_table(
        'prompts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project', sa.String(100), nullable=False, server_default='default'),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('type', sa.String(50), nullable=False, server_default='chat'),
        sa.Column('template', sa.Text(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('usage', sa.Text(), nullable=True),
        sa.Column('model', sa.String(100), nullable=True),
        sa.Column('parameters', postgresql.JSONB(), nullable=True),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('labels', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project', 'name', 'version', name='uq_prompt_project_name_version'),
        schema='agent_loggy'
    )
    op.create_index('idx_prompts_project_name', 'prompts', ['project', 'name'], schema='agent_loggy')
    op.create_index('idx_prompts_labels', 'prompts', ['labels'], schema='agent_loggy', postgresql_using='gin')

    # Create model_configs table
    op.create_table(
        'model_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('model_provider', sa.String(50), nullable=False),
        sa.Column('model_name', sa.String(100), nullable=False),
        sa.Column('parameters', postgresql.JSONB(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('labels', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'version', name='uq_model_config_name_version'),
        schema='agent_loggy'
    )
    op.create_index('idx_model_configs_name', 'model_configs', ['name'], schema='agent_loggy')

    # Create embedding_configs table
    op.create_table(
        'embedding_configs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('embedding_model', sa.String(100), nullable=False),
        sa.Column('chunk_size', sa.Integer(), server_default='512'),
        sa.Column('chunk_overlap', sa.Integer(), server_default='50'),
        sa.Column('chunking_strategy', sa.String(50), server_default='late_chunking'),
        sa.Column('parameters', postgresql.JSONB(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'version', name='uq_embedding_config_name_version'),
        schema='agent_loggy'
    )

    # Create context_rules table
    op.create_table(
        'context_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('context', sa.String(100), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('important', sa.Text(), nullable=True),
        sa.Column('ignore', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('embedding', Vector(384), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('context', 'version', name='uq_context_rule_context_version'),
        schema='agent_loggy'
    )

    # Create negate_keys table
    op.create_table(
        'negate_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(100), nullable=False),
        sa.Column('operator', sa.String(20), nullable=False),
        sa.Column('value', sa.String(255), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), server_default='true'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('label', 'operator', 'value', 'version', name='uq_negate_key'),
        schema='agent_loggy'
    )

    # Create config_changelog table
    op.create_table(
        'config_changelog',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('config_type', sa.String(50), nullable=False),
        sa.Column('config_id', sa.Integer(), nullable=False),
        sa.Column('config_name', sa.String(255), nullable=False),
        sa.Column('previous_version', sa.Integer(), nullable=True),
        sa.Column('new_version', sa.Integer(), nullable=False),
        sa.Column('change_type', sa.String(20), nullable=False),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column('previous_data', postgresql.JSONB(), nullable=True),
        sa.Column('new_data', postgresql.JSONB(), nullable=True),
        sa.Column('changed_by', sa.String(100), nullable=True),
        sa.Column('changed_at', sa.DateTime(), server_default=sa.func.current_timestamp()),
        sa.PrimaryKeyConstraint('id'),
        schema='agent_loggy'
    )
    op.create_index('idx_changelog_config_type_id', 'config_changelog',
                    ['config_type', 'config_id'], schema='agent_loggy')
    op.create_index('idx_changelog_changed_at', 'config_changelog',
                    ['changed_at'], schema='agent_loggy')


def downgrade() -> None:
    op.drop_table('config_changelog', schema='agent_loggy')
    op.drop_table('negate_keys', schema='agent_loggy')
    op.drop_table('context_rules', schema='agent_loggy')
    op.drop_table('embedding_configs', schema='agent_loggy')
    op.drop_table('model_configs', schema='agent_loggy')
    op.drop_table('prompts', schema='agent_loggy')
```

---

## Data Migration Script

### File: `scripts/migrate_prompts.py`

```python
"""
Migrate hardcoded prompts from agent code to database.
Run after applying ORM migration.
"""

import sys
sys.path.insert(0, '.')

from app.db.session import get_db_session
from app.db.models import Prompt, ContextRule, NegateKey, ConfigChangelog
import csv

# ============================================================
# PROMPTS TO MIGRATE
# ============================================================

PROMPTS = [
    {
        "name": "parameter_extraction",
        "type": "system",
        "description": "Extracts time_frame, domain, and query_keys from user text",
        "usage": "ParametersAgent._build_system_prompt()",
        "template": '''You are a strict parameter extractor.
Return ONLY valid JSON with this exact schema:
{"time_frame": "YYYY-MM-DD or null", "domain": "domain_name", "query_keys": ["key1","key2","key3"]}

RULES:
1) query_keys is a flat array of simple field names (lowercase snake_case). No objects/arrays.
2) domain is the main data category from this allow-list only.
3) If no time mentioned -> time_frame = null.
4) time_frame MUST be a single ISO date (YYYY-MM-DD) or null.
5) If user gives a month or a relative period ("July 2025", "last week", "this month"), convert to one concrete start date (YYYY-MM-DD). For a month use day 1; for ranges use the start date.
6) If you cannot confidently produce a single date, set time_frame to null.
7) Use ONLY the allowed query keys; never output excluded ones.

ALLOWED query_keys: {allowed_query_keys}
EXCLUDED query_keys: {excluded_query_keys}

ALLOWED domains: {allowed_domains}
EXCLUDED domains: {excluded_domains}

EXAMPLES:
User: "Show me merchant transactions over 500 last week"
Output: {"time_frame": "2025-07-14", "domain": "transactions", "query_keys": ["merchant","amount"]}

User: "Find customers who bought electronics in January 2025"
Output: {"time_frame": "2025-01-01", "domain": "customers", "query_keys": ["category"]}

User: "List all product reviews with ratings"
Output: {"time_frame": null, "domain": "reviews", "query_keys": ["product_id","rating","review_text"]}

User: "Get bKash payments from this month"
Output: {"time_frame": "2025-10-01", "domain": "payments", "query_keys": ["bkash","mfs"]}

Return ONLY the JSON. No extra text.'''
    },
    {
        "name": "relevance_analysis",
        "type": "user",
        "description": "Analyzes trace relevance to user query with RAG context",
        "usage": "RelevanceAnalyzerAgent._analyze_relevance_with_rag()",
        "template": '''You are an expert system analyst determining if a request trace is relevant to a user's query.
You have access to context rules that help identify what's important vs what should be ignored.

ORIGINAL USER QUERY: {original_text}

EXTRACTED PARAMETERS:
- Domain: {domain}
- Query Keys: {query_keys}
- Time Frame: {time_frame}
- Additional Parameters: {additional_params}

{rag_context}

TRACE INFORMATION:
- Trace ID: {trace_id}
- Timestamp: {timestamp}
- Total Log Entries: {total_entries}
- Services Involved: {services}
- Key Operations: {operations}

SAMPLE LOG MESSAGES:
{log_samples}

TIMELINE SUMMARY:
{timeline_summary}

ANALYSIS REQUIRED:
Determine if this trace is relevant to the user's query by analyzing:
1. Does the trace contain operations related to the query domain?
2. Do the log messages contain the query keys?
3. Does the timestamp match the requested time frame?
4. Are there any operations or data that directly address the user's question?
5. Consider the IMPORTANT PATTERNS defined in the context rules
6. Even if not directly matching, could this trace provide useful context?

Provide analysis in JSON format:
{
    "relevance_score": <0-100>,
    "confidence_score": <0-100>,
    "matching_elements": ["<specific elements that match the query>"],
    "non_matching_elements": ["<elements that don't match>"],
    "key_findings": ["<important discoveries about relevance>"],
    "domain_match": <true/false>,
    "time_match": <true/false>,
    "keyword_matches": ["<specific keyword matches found>"],
    "important_pattern_matches": ["<matches from RAG important patterns>"],
    "recommendation": "<INCLUDE|EXCLUDE|REVIEW - with brief explanation>",
    "reasoning": "<detailed explanation of relevance determination>"
}'''
    },
    {
        "name": "trace_analysis",
        "type": "user",
        "description": "Deep forensic analysis of a single trace",
        "usage": "AnalyzeAgent._analyze_single_trace()",
        "template": '''You are a senior banking systems analyst performing forensic analysis on a transaction trace.

ORIGINAL CUSTOMER DISPUTE/QUERY:
{dispute_text}

TRACE ID: {trace_id}
SOURCE FILES: {source_files}

SAMPLE LOG MESSAGES (first 10):
{log_samples}

TIMELINE (first 15 events):
{timeline}

Analyze this trace and provide a JSON response with:
{
    "relevance_score": <0-100 how relevant to the dispute>,
    "request_summary": "<what this request was trying to do>",
    "transaction_outcome": "<successful|failed|partial|unknown>",
    "key_finding": "<most important discovery>",
    "primary_issue": "<main issue category if any>",
    "confidence_level": "<HIGH|MEDIUM|LOW>",
    "evidence_found": ["<list of key evidence points>"],
    "root_cause_analysis": "<if failed, what caused it>",
    "recommendation": "<next steps or resolution>"
}'''
    },
    {
        "name": "quality_assessment",
        "type": "user",
        "description": "Rates overall search and analysis quality",
        "usage": "AnalyzeAgent._assess_overall_quality()",
        "template": '''Rate the quality of this log analysis search.

ORIGINAL QUERY: {original_query}
PARAMETERS USED: {parameters}
TRACES FOUND: {trace_count}
INDIVIDUAL ANALYSES: {analyses}

Provide a JSON assessment:
{
    "completeness_score": <0-100>,
    "relevance_score": <0-100>,
    "coverage_score": <0-100>,
    "overall_confidence": <average of above>,
    "key_gaps": ["<what's missing>"],
    "recommendations": ["<suggestions for better results>"]
}'''
    }
]


def migrate_prompts():
    """Insert all prompts into database with version 1."""
    with get_db_session() as session:
        for prompt_data in PROMPTS:
            prompt = Prompt(
                project="default",
                name=prompt_data["name"],
                version=1,
                type=prompt_data["type"],
                template=prompt_data["template"],
                description=prompt_data["description"],
                usage=prompt_data["usage"],
                is_active=True,
                labels=["production", "v1"],
                created_by="migration_script"
            )
            session.add(prompt)

            # Log to changelog
            changelog = ConfigChangelog(
                config_type="prompt",
                config_id=0,  # Will be updated after flush
                config_name=f"default:{prompt_data['name']}",
                new_version=1,
                change_type="create",
                change_summary=f"Initial migration from hardcoded prompt",
                changed_by="migration_script"
            )
            session.add(changelog)

        print(f"Migrated {len(PROMPTS)} prompts to database")


def migrate_context_rules():
    """Migrate context_rules.csv to database."""
    csv_path = "app/app_settings/context_rules.csv"

    with get_db_session() as session:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                rule = ContextRule(
                    context=row['context'].strip(),
                    version=1,
                    important=row['important'].strip() if row.get('important') else None,
                    ignore=row['ignore'].strip() if row.get('ignore') else None,
                    description=row.get('description', '').strip() or None,
                    is_active=True
                )
                session.add(rule)
                count += 1

        print(f"Migrated {count} context rules to database")


def migrate_negate_keys():
    """Migrate negate_keys.csv to database."""
    csv_path = "app/app_settings/negate_keys.csv"

    with get_db_session() as session:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header
            count = 0
            for row in reader:
                if len(row) >= 3:
                    negate_key = NegateKey(
                        label=row[0].strip() if row[0] else "default",
                        operator=row[1].strip() if row[1] else "!=",
                        value=row[2].strip(),
                        version=1,
                        is_active=True
                    )
                    session.add(negate_key)
                    count += 1

        print(f"Migrated {count} negate keys to database")


if __name__ == "__main__":
    print("Starting data migration...")
    migrate_prompts()
    migrate_context_rules()
    migrate_negate_keys()
    print("Migration complete!")
```

---

## File-by-File Implementation Steps

| Step | File | Action | Description |
|------|------|--------|-------------|
| 1 | `requirements.txt` | MODIFY | Add `pgvector>=0.2.0` |
| 2 | `app/db/models.py` | CREATE | All ORM models |
| 3 | `app/db/session.py` | CREATE | Session factory |
| 4 | `app/db/base.py` | MODIFY | Import all models |
| 5 | `app/db/__init__.py` | MODIFY | Export models and session |
| 6 | `alembic/versions/xxx_add_orm_config_tables.py` | CREATE | Run `alembic revision --autogenerate` |
| 7 | `scripts/migrate_prompts.py` | CREATE | Data migration script |
| 8 | Run `alembic upgrade head` | COMMAND | Apply migration |
| 9 | Run `python scripts/migrate_prompts.py` | COMMAND | Migrate data |

---

## Dependencies to Add

```txt
# requirements.txt additions
pgvector>=0.2.0
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_db_models.py

import pytest
from app.db.models import Prompt, ModelConfig, ContextRule
from app.db.session import get_db_session


class TestPromptModel:
    def test_create_prompt(self, db_session):
        prompt = Prompt(
            name="test_prompt",
            template="Test template",
            project="default"
        )
        db_session.add(prompt)
        db_session.flush()

        assert prompt.id is not None
        assert prompt.version == 1
        assert prompt.is_active is True

    def test_prompt_versioning(self, db_session):
        # Create v1
        v1 = Prompt(name="versioned", template="v1", project="default", version=1)
        db_session.add(v1)

        # Create v2
        v2 = Prompt(name="versioned", template="v2", project="default", version=2)
        db_session.add(v2)
        db_session.flush()

        assert v1.id != v2.id

    def test_unique_constraint(self, db_session):
        p1 = Prompt(name="unique", template="t1", project="default", version=1)
        p2 = Prompt(name="unique", template="t2", project="default", version=1)

        db_session.add(p1)
        db_session.flush()

        with pytest.raises(Exception):  # IntegrityError
            db_session.add(p2)
            db_session.flush()
```

---

## Critical Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `app/db/base.py` | All | SQLAlchemy base + model imports |
| `app/db/models.py` | All | NEW - ORM model definitions |
| `app/db/session.py` | All | NEW - Session factory |
| `app/agents/parameter_agent.py` | 166-193 | Hardcoded prompt to extract |
| `app/agents/verify_agent.py` | 425-478 | Hardcoded prompt to extract |
| `app/agents/analyze_agent.py` | 235-286, 335-362, 396-416 | Hardcoded prompts to extract |
| `alembic/env.py` | 27 | Must import Base with models |
