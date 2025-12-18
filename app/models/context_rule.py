# app/models/context_rule.py
"""
SQLAlchemy models for RAG context rules.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Index
)

from app.db.base import Base
from app.config import settings as app_settings


class ContextRule(Base):
    """
    Context rules for RAG-based relevance analysis.

    Rules define what patterns are important vs. ignorable for specific contexts
    (e.g., MFS, bKash, transactions).
    """
    __tablename__ = "context_rules"
    __table_args__ = (
        Index("idx_context_rules_context", "context"),
        Index("idx_context_rules_active", "is_active"),
        {"schema": app_settings.DATABASE_SCHEMA}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    context = Column(String(100), nullable=False)  # e.g., 'mfs', 'bkash', 'transactions'
    important = Column(Text, nullable=True)  # Comma-separated important patterns
    ignore = Column(Text, nullable=True)  # Comma-separated patterns to ignore
    description = Column(Text, nullable=True)  # Description of the rule
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<ContextRule(id={self.id}, context={self.context})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "context": self.context,
            "important": self.important,
            "ignore": self.ignore,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
