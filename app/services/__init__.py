# app/services/__init__.py
# Service layer for agent-loggy

# Cache infrastructure
from app.services.cache import TTLCache, CacheManager, cache_manager, cached

# Prompt service
from app.services.prompt_service import PromptService, get_prompt_service

# Config service
from app.services.config_service import ConfigService, get_config_service, get_setting

# Project service
from app.services.project_service import (
    ProjectService,
    get_project_service,
    is_file_based,
    is_loki_based,
    get_loki_namespace,
)

__all__ = [
    "TTLCache",
    "CacheManager",
    "cache_manager",
    "cached",
    "PromptService",
    "get_prompt_service",
    "ConfigService",
    "get_config_service",
    "get_setting",
    "ProjectService",
    "get_project_service",
    "is_file_based",
    "is_loki_based",
    "get_loki_namespace",
]
