# app/models/prompt.py
"""
SQLAlchemy models for versioned prompts with history tracking.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.config import settings


class PromptVersioned(Base):
    """
    Versioned prompts table with support for multiple versions per prompt name.

    Each prompt can have multiple versions, with only one active at a time.
    Supports rollback to previous versions.
    """
    __tablename__ = "prompts_versioned"
    __table_args__ = (
        UniqueConstraint("prompt_name", "version", name="uq_prompt_name_version"),
        Index("idx_prompts_versioned_name", "prompt_name"),
        Index("idx_prompts_versioned_active", "prompt_name", "is_active"),
        {"schema": settings.DATABASE_SCHEMA}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_name = Column(String(255), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    prompt_content = Column(Text, nullable=False)
    variables = Column(JSONB, default=dict)  # Template variables like {domain}, {query}
    agent_name = Column(String(100), nullable=True)  # e.g., 'parameter_agent', 'analyze_agent'
    prompt_type = Column(String(50), nullable=True)  # 'system', 'user'
    is_active = Column(Boolean, default=True, nullable=False)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    deactivated_at = Column(DateTime, nullable=True)

    # Relationship to history
    history = relationship("PromptHistory", back_populates="prompt", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<PromptVersioned(name={self.prompt_name}, version={self.version}, active={self.is_active})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "prompt_name": self.prompt_name,
            "version": self.version,
            "prompt_content": self.prompt_content,
            "variables": self.variables,
            "agent_name": self.agent_name,
            "prompt_type": self.prompt_type,
            "is_active": self.is_active,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "deactivated_at": self.deactivated_at.isoformat() if self.deactivated_at else None,
        }


class PromptHistory(Base):
    """
    Audit log for prompt changes.

    Tracks all modifications to prompts including creates, updates, and rollbacks.
    """
    __tablename__ = "prompt_history"
    __table_args__ = (
        Index("idx_prompt_history_prompt_id", "prompt_id"),
        Index("idx_prompt_history_changed_at", "changed_at"),
        {"schema": settings.DATABASE_SCHEMA}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_id = Column(
        Integer,
        ForeignKey(f"{settings.DATABASE_SCHEMA}.prompts_versioned.id", ondelete="CASCADE"),
        nullable=False
    )
    action = Column(String(20), nullable=False)  # 'created', 'updated', 'deactivated', 'activated', 'rolled_back'
    old_content = Column(Text, nullable=True)
    new_content = Column(Text, nullable=True)
    changed_by = Column(String(100), nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to prompt
    prompt = relationship("PromptVersioned", back_populates="history")

    def __repr__(self) -> str:
        return f"<PromptHistory(prompt_id={self.prompt_id}, action={self.action})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "prompt_id": self.prompt_id,
            "action": self.action,
            "old_content": self.old_content,
            "new_content": self.new_content,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
        }
