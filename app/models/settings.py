# app/models/settings.py
"""
SQLAlchemy models for application settings with history tracking.
"""

from datetime import datetime
from typing import Optional, Any
import json

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime,
    ForeignKey, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship

from app.db.base import Base
from app.config import settings as app_settings


class AppSetting(Base):
    """
    Application settings table with category-based organization.

    Settings are organized by category (e.g., 'ollama', 'loki', 'thresholds')
    and can store various value types (string, int, float, bool, json).
    """
    __tablename__ = "app_settings"
    __table_args__ = (
        UniqueConstraint("category", "setting_key", name="uq_category_key"),
        Index("idx_app_settings_category", "category"),
        Index("idx_app_settings_key", "setting_key"),
        Index("idx_app_settings_active", "is_active"),
        {"schema": app_settings.DATABASE_SCHEMA}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    category = Column(String(100), nullable=False)
    setting_key = Column(String(255), nullable=False)
    setting_value = Column(Text, nullable=False)
    value_type = Column(String(50), nullable=False)  # 'string', 'int', 'float', 'bool', 'json'
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship to history
    history = relationship("SettingsHistory", back_populates="setting", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<AppSetting({self.category}.{self.setting_key}={self.setting_value})>"

    def get_typed_value(self) -> Any:
        """
        Get the setting value converted to its proper type.

        Returns:
            The value converted to the appropriate Python type
        """
        if self.value_type == "int":
            return int(self.setting_value)
        elif self.value_type == "float":
            return float(self.setting_value)
        elif self.value_type == "bool":
            return self.setting_value.lower() in ("true", "1", "yes")
        elif self.value_type == "json":
            return json.loads(self.setting_value)
        else:  # string
            return self.setting_value

    @staticmethod
    def from_value(category: str, key: str, value: Any, description: str = None) -> "AppSetting":
        """
        Create an AppSetting from a Python value, auto-detecting the type.

        Args:
            category: Setting category
            key: Setting key
            value: Python value to store
            description: Optional description

        Returns:
            AppSetting instance
        """
        if isinstance(value, bool):
            value_type = "bool"
            setting_value = str(value).lower()
        elif isinstance(value, int):
            value_type = "int"
            setting_value = str(value)
        elif isinstance(value, float):
            value_type = "float"
            setting_value = str(value)
        elif isinstance(value, (list, dict)):
            value_type = "json"
            setting_value = json.dumps(value)
        else:
            value_type = "string"
            setting_value = str(value)

        return AppSetting(
            category=category,
            setting_key=key,
            setting_value=setting_value,
            value_type=value_type,
            description=description
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category,
            "setting_key": self.setting_key,
            "setting_value": self.setting_value,
            "typed_value": self.get_typed_value(),
            "value_type": self.value_type,
            "description": self.description,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class SettingsHistory(Base):
    """
    Audit log for settings changes.

    Tracks all modifications to settings including creates, updates, and deletes.
    """
    __tablename__ = "settings_history"
    __table_args__ = (
        Index("idx_settings_history_setting_id", "setting_id"),
        Index("idx_settings_history_changed_at", "changed_at"),
        {"schema": app_settings.DATABASE_SCHEMA}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    setting_id = Column(
        Integer,
        ForeignKey(f"{app_settings.DATABASE_SCHEMA}.app_settings.id", ondelete="CASCADE"),
        nullable=False
    )
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    changed_by = Column(String(100), nullable=True)
    changed_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship to setting
    setting = relationship("AppSetting", back_populates="history")

    def __repr__(self) -> str:
        return f"<SettingsHistory(setting_id={self.setting_id}, changed_at={self.changed_at})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "setting_id": self.setting_id,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "changed_by": self.changed_by,
            "changed_at": self.changed_at.isoformat() if self.changed_at else None,
        }
