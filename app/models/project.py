# app/models/project.py
"""
SQLAlchemy models for project configuration.
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


class Project(Base):
    """
    Project configuration table.

    Each project represents a different log analysis target (e.g., MMBL, UCB, NCC, ABBL).
    Projects can be file-based (local logs) or Loki-based (remote log queries).
    """
    __tablename__ = "projects"
    __table_args__ = (
        Index("idx_projects_code", "project_code"),
        Index("idx_projects_active", "is_active"),
        {"schema": app_settings.DATABASE_SCHEMA}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_code = Column(String(50), nullable=False, unique=True)
    project_name = Column(String(255), nullable=False)
    log_source_type = Column(String(50), nullable=False)  # 'file' or 'loki'
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    settings = relationship("ProjectSetting", back_populates="project", cascade="all, delete-orphan")
    environments = relationship("Environment", back_populates="project", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Project({self.project_code}, type={self.log_source_type})>"

    def is_file_based(self) -> bool:
        """Check if this project uses file-based log storage."""
        return self.log_source_type == "file"

    def is_loki_based(self) -> bool:
        """Check if this project uses Loki for log queries."""
        return self.log_source_type == "loki"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_code": self.project_code,
            "project_name": self.project_name,
            "log_source_type": self.log_source_type,
            "description": self.description,
            "is_active": self.is_active,
            "is_file_based": self.is_file_based(),
            "is_loki_based": self.is_loki_based(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ProjectSetting(Base):
    """
    Project-specific settings.

    Allows storing custom configuration per project (e.g., log paths, namespaces).
    """
    __tablename__ = "project_settings"
    __table_args__ = (
        UniqueConstraint("project_id", "setting_key", name="uq_project_setting"),
        Index("idx_project_settings_project", "project_id"),
        {"schema": app_settings.DATABASE_SCHEMA}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        Integer,
        ForeignKey(f"{app_settings.DATABASE_SCHEMA}.projects.id", ondelete="CASCADE"),
        nullable=False
    )
    setting_key = Column(String(255), nullable=False)
    setting_value = Column(Text, nullable=False)
    value_type = Column(String(50), nullable=False)  # 'string', 'int', 'float', 'bool', 'json'

    # Relationship
    project = relationship("Project", back_populates="settings")

    def __repr__(self) -> str:
        return f"<ProjectSetting({self.setting_key}={self.setting_value})>"

    def get_typed_value(self) -> Any:
        """Get the setting value converted to its proper type."""
        if self.value_type == "int":
            return int(self.setting_value)
        elif self.value_type == "float":
            return float(self.setting_value)
        elif self.value_type == "bool":
            return self.setting_value.lower() in ("true", "1", "yes")
        elif self.value_type == "json":
            return json.loads(self.setting_value)
        else:
            return self.setting_value

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "setting_key": self.setting_key,
            "setting_value": self.setting_value,
            "typed_value": self.get_typed_value(),
            "value_type": self.value_type,
        }


class Environment(Base):
    """
    Environment configuration per project.

    Each project can have multiple environments (e.g., prod, staging, dev).
    Environments define where to find logs (Loki namespace or file path).
    """
    __tablename__ = "environments"
    __table_args__ = (
        UniqueConstraint("project_id", "env_code", name="uq_project_env"),
        Index("idx_environments_project", "project_id"),
        Index("idx_environments_active", "is_active"),
        {"schema": app_settings.DATABASE_SCHEMA}
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(
        Integer,
        ForeignKey(f"{app_settings.DATABASE_SCHEMA}.projects.id", ondelete="CASCADE"),
        nullable=False
    )
    env_code = Column(String(50), nullable=False)  # e.g., 'prod', 'staging', 'dev'
    env_name = Column(String(100), nullable=True)  # e.g., 'Production', 'Staging'
    loki_namespace = Column(String(100), nullable=True)  # For Loki-based projects
    log_base_path = Column(String(500), nullable=True)  # For file-based projects
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationship
    project = relationship("Project", back_populates="environments")

    def __repr__(self) -> str:
        return f"<Environment({self.env_code} for project_id={self.project_id})>"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "project_id": self.project_id,
            "env_code": self.env_code,
            "env_name": self.env_name,
            "loki_namespace": self.loki_namespace,
            "log_base_path": self.log_base_path,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
