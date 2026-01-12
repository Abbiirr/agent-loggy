# app/models/conversation.py
"""
SQLAlchemy models for persistent conversation management.

Provides multi-session chat with message history, pipeline execution tracking,
and memory management for long conversations.
"""

from datetime import datetime
from typing import Optional, List, Any

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    ForeignKey, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base
from app.config import settings as app_settings

SCHEMA = app_settings.DATABASE_SCHEMA


class Conversation(Base):
    """
    Persistent conversation session.

    A conversation groups multiple messages and pipeline executions together,
    enabling multi-turn interactions with context retention.
    """
    __tablename__ = "conversations"
    __table_args__ = (
        Index("idx_conversations_conversation_id", "conversation_id"),
        Index("idx_conversations_project", "project_code"),
        Index("idx_conversations_status", "status"),
        Index("idx_conversations_active", "is_active"),
        Index("idx_conversations_created", "created_at"),
        Index("idx_conversations_updated", "updated_at"),
        {"schema": SCHEMA}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(100), unique=True, nullable=False)  # UUID for API
    project_code = Column(String(50), nullable=True)  # Optional link to project
    env = Column(String(50), nullable=True)
    domain = Column(String(100), nullable=True)
    title = Column(String(255), nullable=True)  # Auto-generated from first message
    summary = Column(Text, nullable=True)  # Compressed history for long conversations
    summary_token_count = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="active", nullable=False)  # active, archived, deleted
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at"
    )
    executions = relationship(
        "PipelineExecution",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="PipelineExecution.started_at.desc()"
    )

    def __repr__(self) -> str:
        return f"<Conversation(id={self.id}, conversation_id={self.conversation_id}, title={self.title})>"

    def get_message_count(self) -> int:
        """Get the number of messages in this conversation."""
        return len(self.messages) if self.messages else 0

    def get_last_message(self) -> Optional["Message"]:
        """Get the most recent message."""
        if self.messages:
            return self.messages[-1]
        return None

    def to_dict(self, include_messages: bool = False) -> dict:
        """Convert to dictionary representation."""
        result = {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "project_code": self.project_code,
            "env": self.env,
            "domain": self.domain,
            "title": self.title,
            "status": self.status,
            "is_active": self.is_active,
            "message_count": self.get_message_count(),
            "has_summary": self.summary is not None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_messages:
            result["messages"] = [m.to_dict() for m in self.messages]
            result["summary"] = self.summary
        return result


class Message(Base):
    """
    Individual message in a conversation.

    Messages can be from user, assistant, or system. Each message tracks
    its role, content, type, and optional message_metadata like token counts.
    """
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_messages_conversation", "conversation_id"),
        Index("idx_messages_role", "role"),
        Index("idx_messages_type", "message_type"),
        Index("idx_messages_created", "created_at"),
        {"schema": SCHEMA}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(
        Integer,
        ForeignKey(f"{SCHEMA}.conversations.id", ondelete="CASCADE"),
        nullable=False
    )
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    message_type = Column(String(50), nullable=True)  # prompt, analysis, verification, etc.
    message_metadata = Column(JSONB, nullable=True)  # tokens, cache_hit, step_name, etc.
    token_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    conversation = relationship("Conversation", back_populates="messages")

    def __repr__(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<Message(id={self.id}, role={self.role}, content={content_preview})>"

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "role": self.role,
            "content": self.content,
            "message_type": self.message_type,
            "message_metadata": self.message_metadata,
            "token_count": self.token_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_llm_format(self) -> dict:
        """Convert to format suitable for LLM context."""
        return {
            "role": self.role,
            "content": self.content,
        }


class PipelineExecution(Base):
    """
    Tracks individual analysis runs within a conversation.

    Each time a user sends a message that triggers the analysis pipeline,
    a new execution record is created to track the progress and results.
    """
    __tablename__ = "pipeline_executions"
    __table_args__ = (
        Index("idx_executions_execution_id", "execution_id"),
        Index("idx_executions_conversation", "conversation_id"),
        Index("idx_executions_status", "status"),
        Index("idx_executions_started", "started_at"),
        {"schema": SCHEMA}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(
        Integer,
        ForeignKey(f"{SCHEMA}.conversations.id", ondelete="CASCADE"),
        nullable=False
    )
    execution_id = Column(String(100), unique=True, nullable=False)  # UUID for API
    status = Column(String(20), default="pending", nullable=False)  # pending, streaming, complete, error
    prompt = Column(Text, nullable=False)
    extracted_params = Column(JSONB, nullable=True)
    plan = Column(JSONB, nullable=True)
    trace_ids = Column(JSONB, nullable=True)  # List of found trace IDs
    report_files = Column(JSONB, nullable=True)  # List of generated file paths
    cache_diagnostics = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    # Relationship
    conversation = relationship("Conversation", back_populates="executions")

    def __repr__(self) -> str:
        return f"<PipelineExecution(id={self.id}, execution_id={self.execution_id}, status={self.status})>"

    def is_complete(self) -> bool:
        """Check if execution has finished (successfully or with error)."""
        return self.status in ("complete", "error")

    def is_streaming(self) -> bool:
        """Check if execution is currently streaming."""
        return self.status == "streaming"

    def duration_seconds(self) -> Optional[float]:
        """Get execution duration in seconds, if completed."""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "conversation_id": self.conversation_id,
            "execution_id": self.execution_id,
            "status": self.status,
            "prompt": self.prompt,
            "extracted_params": self.extracted_params,
            "plan": self.plan,
            "trace_ids": self.trace_ids,
            "report_files": self.report_files,
            "cache_diagnostics": self.cache_diagnostics,
            "error_message": self.error_message,
            "duration_seconds": self.duration_seconds(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
