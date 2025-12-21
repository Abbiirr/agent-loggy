# Phase 2: Configuration Layer Plan

## Executive Summary

This phase transforms agent-loggy from static `.env` configuration to a dynamic, hot-reloadable configuration system. Using Dynaconf for environment layering and Redis for distributed caching, the system will support runtime configuration updates without application restarts. This enables A/B testing of prompts, gradual model rollouts, and instant configuration rollback.

**Timeline**: Week 2-3
**Dependencies**: Phase 1 (Database Migration)
**Blocking**: Phase 3, 4, 5

---

## Current State Analysis

### What Exists
| Component | Location | Status |
|-----------|----------|--------|
| Pydantic Settings | `app/config.py` | Basic, static loading |
| Environment File | `.env` | Single environment |
| Configuration | Hardcoded in agents | No runtime changes |

### Current Configuration (app/config.py)
```python
class Settings(BaseSettings):
    DATABASE_URL: str
    DATABASE_SCHEMA: str
    OLLAMA_HOST: str
    ANALYSIS_DIR: str
    MODEL: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()  # Loaded ONCE at import
```

### Problems with Current Approach
1. **No Environment Layering**: Single `.env` file for all environments
2. **No Hot-Reload**: Changes require application restart
3. **No Distributed Caching**: Each worker loads independently
4. **No Validation**: Missing defaults and type coercion
5. **No Secrets Management**: Database passwords in plain `.env`
6. **No Audit Trail**: No tracking of configuration changes

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Application Layer                              │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    ConfigurationManager                        │  │
│  │  - get_prompt(name, label='production')                       │  │
│  │  - get_model_config(name)                                     │  │
│  │  - get_embedding_config(name)                                 │  │
│  │  - refresh()  # Manual cache invalidation                     │  │
│  └───────────────────────────┬──────────────────────────────────┘  │
│                              │                                      │
│         ┌────────────────────┼────────────────────┐                │
│         ▼                    ▼                    ▼                │
│  ┌─────────────┐    ┌─────────────────┐   ┌────────────────┐      │
│  │   Dynaconf  │    │  Redis Cache    │   │  Database      │      │
│  │   (Static)  │    │  (Hot Config)   │   │  (Prompts)     │      │
│  └─────────────┘    └─────────────────┘   └────────────────┘      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Configuration Flow                              │
│                                                                      │
│  ┌────────────┐      ┌────────────┐      ┌────────────────┐        │
│  │ Agent      │─────▶│ Config     │─────▶│ Redis Cache    │        │
│  │ Request    │      │ Manager    │      │ (5min TTL)     │        │
│  └────────────┘      └────────────┘      └───────┬────────┘        │
│                                                   │                 │
│                           Cache Miss? ◄──────────┘                 │
│                              │                                      │
│                              ▼                                      │
│                      ┌────────────────┐                            │
│                      │  PostgreSQL    │                            │
│                      │  (prompts,     │                            │
│                      │   configs)     │                            │
│                      └───────┬────────┘                            │
│                              │                                      │
│                              ▼                                      │
│                      ┌────────────────┐                            │
│                      │ Cache + Return │                            │
│                      └────────────────┘                            │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                   Cache Invalidation Flow                           │
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐      │
│  │ Admin UI /   │───▶│ Config API   │───▶│ PostgreSQL       │      │
│  │ Migration    │    │ Endpoint     │    │ UPDATE           │      │
│  └──────────────┘    └──────────────┘    └────────┬─────────┘      │
│                                                    │                │
│                                                    ▼                │
│                                          ┌──────────────────┐      │
│                                          │ Redis PUBLISH    │      │
│                                          │ config:invalidate│      │
│                                          └────────┬─────────┘      │
│                                                   │                 │
│                    ┌──────────────────────────────┼──────────────┐ │
│                    ▼                              ▼              ▼ │
│             ┌────────────┐              ┌────────────┐  ┌────────┐│
│             │ Worker 1   │              │ Worker 2   │  │Worker N││
│             │ SUBSCRIBE  │              │ SUBSCRIBE  │  │SUBSCRIBE│
│             │ Clear Cache│              │ Clear Cache│  │Clear   ││
│             └────────────┘              └────────────┘  └────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

---

## Environment Layering Strategy

### File Structure

```
config/
├── settings.toml         # Base defaults (committed)
├── settings.local.toml   # Local dev overrides (gitignored)
├── settings.staging.toml # Staging environment
├── settings.prod.toml    # Production (secrets via env vars)
└── .secrets.toml         # Local secrets (gitignored)
```

### Environment Precedence (Lowest to Highest)

1. `settings.toml` - Base defaults
2. `settings.{ENV}.toml` - Environment-specific
3. `.secrets.toml` - Local secrets
4. Environment variables (highest priority)

---

## Dynaconf Configuration

### File: `config/settings.toml`

```toml
[default]
# Application
APP_NAME = "agent-loggy"
DEBUG = false
LOG_LEVEL = "INFO"

# Database
DATABASE_SCHEMA = "agent_loggy"

# LLM Settings
DEFAULT_MODEL = "ollama:qwen3:14b"
LLM_TIMEOUT_SECONDS = 120
MAX_RETRIES = 3

# Session Management
SESSION_TIMEOUT_MINUTES = 30
MAX_CONTEXT_MESSAGES = 20

# Limits
MAX_LOG_BYTES = 524288  # 512 KB

# Redis Cache
REDIS_CACHE_TTL_SECONDS = 300  # 5 minutes
REDIS_CONFIG_CHANNEL = "config:invalidate"

# RAG Settings (Phase 3)
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
EMBEDDING_MODEL = "text-embedding-3-small"
CHUNKING_STRATEGY = "late_chunking"
RERANKER_MODEL = "cohere-rerank-v3"
RERANKER_TOP_K = 10

# Feature Flags (Phase 4)
FEATURE_FLAGS_ENABLED = true
FEATURE_FLAGS_PROVIDER = "flagsmith"

[default.fresh_vars]
# Variables that should NEVER be cached (always re-read)
PROMPTS = true
MODEL_CONFIGS = true
FEATURE_FLAGS = true
```

### File: `config/settings.local.toml`

```toml
[default]
DEBUG = true
LOG_LEVEL = "DEBUG"

# Local Ollama
OLLAMA_HOST = "http://localhost:11434"
DEFAULT_MODEL = "ollama:qwen3:14b"

# Local PostgreSQL
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/agent_loggy"

# Local Redis
REDIS_URL = "redis://localhost:6379/0"

# Analysis output
ANALYSIS_DIR = "./app/comprehensive_analysis"
```

### File: `config/settings.staging.toml`

```toml
[default]
DEBUG = false
LOG_LEVEL = "INFO"

# Staging overrides loaded from environment variables
# DATABASE_URL = @env STAGING_DATABASE_URL
# REDIS_URL = @env STAGING_REDIS_URL
```

### File: `config/settings.prod.toml`

```toml
[default]
DEBUG = false
LOG_LEVEL = "WARNING"

# Production settings
LLM_TIMEOUT_SECONDS = 180
MAX_RETRIES = 5
SESSION_TIMEOUT_MINUTES = 60

# All secrets from environment variables
# DATABASE_URL = @env PROD_DATABASE_URL
# REDIS_URL = @env PROD_REDIS_URL
# OLLAMA_HOST = @env PROD_OLLAMA_HOST
```

---

## Core Implementation

### File: `app/config.py` (Rewritten)

```python
"""
Dynamic configuration management using Dynaconf.

Supports:
- Environment layering (local, staging, production)
- Hot-reload via fresh_vars
- Redis cache integration
- Secrets from environment variables
"""

import os
from pathlib import Path
from typing import Any, Optional

from dynaconf import Dynaconf, Validator

# Determine environment
ENV_FOR_DYNACONF = os.getenv("ENV_FOR_DYNACONF", "local")

# Configuration root
CONFIG_ROOT = Path(__file__).parent.parent / "config"

# Initialize Dynaconf
settings = Dynaconf(
    envvar_prefix="AGENTLOGGY",
    settings_files=[
        str(CONFIG_ROOT / "settings.toml"),
        str(CONFIG_ROOT / f"settings.{ENV_FOR_DYNACONF}.toml"),
    ],
    secrets=str(CONFIG_ROOT / ".secrets.toml"),
    environments=True,
    load_dotenv=True,
    env_switcher="ENV_FOR_DYNACONF",

    # Fresh variables - NEVER cached
    fresh_vars=["PROMPTS", "MODEL_CONFIGS", "FEATURE_FLAGS"],

    # Validators
    validators=[
        Validator("DATABASE_URL", must_exist=True),
        Validator("OLLAMA_HOST", must_exist=True),
        Validator("DATABASE_SCHEMA", default="agent_loggy"),
        Validator("DEFAULT_MODEL", default="ollama:qwen3:14b"),
        Validator("LLM_TIMEOUT_SECONDS", is_type_of=int, default=120),
        Validator("SESSION_TIMEOUT_MINUTES", is_type_of=int, default=30, gte=5, lte=1440),
        Validator("MAX_CONTEXT_MESSAGES", is_type_of=int, default=20, gte=5, lte=100),
        Validator("MAX_LOG_BYTES", is_type_of=int, default=524288),
        Validator("REDIS_URL", default="redis://localhost:6379/0"),
        Validator("REDIS_CACHE_TTL_SECONDS", is_type_of=int, default=300),
        Validator("CHUNK_SIZE", is_type_of=int, default=512, gte=128, lte=4096),
        Validator("CHUNK_OVERLAP", is_type_of=int, default=50, gte=0, lte=256),
        Validator("LOG_LEVEL", default="INFO", is_in=["DEBUG", "INFO", "WARNING", "ERROR"]),
    ]
)

# Validate on load
settings.validators.validate()


def get_setting(key: str, default: Any = None) -> Any:
    """
    Get a configuration value with optional default.
    Fresh vars are always re-read from source.
    """
    return settings.get(key, default)


def is_debug() -> bool:
    """Check if debug mode is enabled."""
    return settings.get("DEBUG", False)


def get_environment() -> str:
    """Get current environment name."""
    return ENV_FOR_DYNACONF
```

---

### File: `app/config_manager.py`

```python
"""
ConfigurationManager provides cached access to database-stored configurations.

Features:
- Redis caching with TTL
- Pub/sub cache invalidation
- Thread-safe singleton
- Fallback to database on cache miss
"""

import json
import logging
import threading
from typing import Any, Dict, List, Optional

import redis

from app.config import settings
from app.db.session import get_db_session
from app.db.models import Prompt, ModelConfig, EmbeddingConfig, ContextRule

logger = logging.getLogger(__name__)


class ConfigurationManager:
    """
    Singleton manager for cached configuration access.

    Usage:
        config_mgr = ConfigurationManager.get_instance()
        prompt = config_mgr.get_prompt("parameter_extraction")
        model = config_mgr.get_model_config("default")
    """

    _instance: Optional["ConfigurationManager"] = None
    _lock = threading.Lock()

    CACHE_PREFIX = "agentloggy:config:"
    PROMPT_CACHE_KEY = CACHE_PREFIX + "prompt:{project}:{name}:{label}"
    MODEL_CACHE_KEY = CACHE_PREFIX + "model:{name}:{label}"
    EMBEDDING_CACHE_KEY = CACHE_PREFIX + "embedding:{name}"
    CONTEXT_RULES_CACHE_KEY = CACHE_PREFIX + "context_rules"

    def __init__(self):
        """Initialize Redis connection and subscriber."""
        self._redis: Optional[redis.Redis] = None
        self._subscriber_thread: Optional[threading.Thread] = None
        self._running = False
        self._ttl = settings.get("REDIS_CACHE_TTL_SECONDS", 300)
        self._channel = settings.get("REDIS_CONFIG_CHANNEL", "config:invalidate")

        self._connect_redis()
        self._start_subscriber()

    @classmethod
    def get_instance(cls) -> "ConfigurationManager":
        """Get or create singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _connect_redis(self) -> None:
        """Establish Redis connection."""
        try:
            redis_url = settings.get("REDIS_URL", "redis://localhost:6379/0")
            self._redis = redis.from_url(redis_url, decode_responses=True)
            self._redis.ping()
            logger.info(f"Connected to Redis: {redis_url}")
        except redis.ConnectionError as e:
            logger.warning(f"Redis connection failed: {e}. Caching disabled.")
            self._redis = None

    def _start_subscriber(self) -> None:
        """Start background thread for cache invalidation events."""
        if self._redis is None:
            return

        self._running = True
        self._subscriber_thread = threading.Thread(
            target=self._subscribe_invalidation,
            daemon=True,
            name="config-invalidation-subscriber"
        )
        self._subscriber_thread.start()

    def _subscribe_invalidation(self) -> None:
        """Listen for cache invalidation messages."""
        try:
            pubsub = self._redis.pubsub()
            pubsub.subscribe(self._channel)

            for message in pubsub.listen():
                if not self._running:
                    break

                if message["type"] == "message":
                    self._handle_invalidation(message["data"])

        except Exception as e:
            logger.error(f"Subscriber error: {e}")

    def _handle_invalidation(self, data: str) -> None:
        """
        Handle cache invalidation message.

        Message format: {"type": "prompt|model|embedding|all", "key": "optional_key"}
        """
        try:
            payload = json.loads(data)
            invalidate_type = payload.get("type", "all")
            invalidate_key = payload.get("key")

            if invalidate_type == "all":
                self._clear_all_cache()
            elif invalidate_key:
                self._clear_cache_key(invalidate_key)
            else:
                # Clear by pattern
                pattern = f"{self.CACHE_PREFIX}{invalidate_type}:*"
                self._clear_cache_pattern(pattern)

            logger.info(f"Cache invalidated: type={invalidate_type}, key={invalidate_key}")

        except json.JSONDecodeError:
            logger.warning(f"Invalid invalidation message: {data}")

    def _clear_all_cache(self) -> None:
        """Clear all configuration cache."""
        if self._redis:
            pattern = f"{self.CACHE_PREFIX}*"
            keys = self._redis.keys(pattern)
            if keys:
                self._redis.delete(*keys)

    def _clear_cache_key(self, key: str) -> None:
        """Clear specific cache key."""
        if self._redis:
            self._redis.delete(key)

    def _clear_cache_pattern(self, pattern: str) -> None:
        """Clear cache by pattern."""
        if self._redis:
            keys = self._redis.keys(pattern)
            if keys:
                self._redis.delete(*keys)

    # =========================================================================
    # PROMPT ACCESS
    # =========================================================================

    def get_prompt(
        self,
        name: str,
        project: str = "default",
        label: str = "production",
        version: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get a prompt by name, optionally filtered by label or version.

        Args:
            name: Prompt name (e.g., "parameter_extraction")
            project: Project namespace (default: "default")
            label: Environment label (e.g., "production", "staging")
            version: Specific version (if None, gets latest active)

        Returns:
            Dict with prompt data or None if not found
        """
        cache_key = self.PROMPT_CACHE_KEY.format(
            project=project, name=name, label=label
        )

        # Try cache first
        if self._redis:
            cached = self._redis.get(cache_key)
            if cached:
                logger.debug(f"Cache hit: {cache_key}")
                return json.loads(cached)

        # Fetch from database
        with get_db_session() as session:
            query = session.query(Prompt).filter(
                Prompt.project == project,
                Prompt.name == name,
                Prompt.is_active == True
            )

            if version:
                query = query.filter(Prompt.version == version)
            else:
                # Filter by label if provided
                query = query.filter(Prompt.labels.contains([label]))
                # Get highest version
                query = query.order_by(Prompt.version.desc())

            prompt = query.first()

            if prompt:
                result = {
                    "id": prompt.id,
                    "name": prompt.name,
                    "project": prompt.project,
                    "version": prompt.version,
                    "type": prompt.type,
                    "template": prompt.template,
                    "description": prompt.description,
                    "model": prompt.model,
                    "parameters": prompt.parameters,
                    "labels": prompt.labels
                }

                # Cache result
                if self._redis:
                    self._redis.setex(
                        cache_key,
                        self._ttl,
                        json.dumps(result)
                    )

                return result

        logger.warning(f"Prompt not found: {project}:{name} (label={label})")
        return None

    def get_prompt_template(
        self,
        name: str,
        project: str = "default",
        label: str = "production"
    ) -> Optional[str]:
        """Get just the template string for a prompt."""
        prompt = self.get_prompt(name, project, label)
        return prompt["template"] if prompt else None

    # =========================================================================
    # MODEL CONFIG ACCESS
    # =========================================================================

    def get_model_config(
        self,
        name: str = "default",
        label: str = "production"
    ) -> Optional[Dict[str, Any]]:
        """
        Get model configuration by name.

        Args:
            name: Config name (default: "default")
            label: Environment label

        Returns:
            Dict with model config or None
        """
        cache_key = self.MODEL_CACHE_KEY.format(name=name, label=label)

        # Try cache first
        if self._redis:
            cached = self._redis.get(cache_key)
            if cached:
                return json.loads(cached)

        # Fetch from database
        with get_db_session() as session:
            config = session.query(ModelConfig).filter(
                ModelConfig.name == name,
                ModelConfig.is_active == True,
                ModelConfig.labels.contains([label])
            ).order_by(ModelConfig.version.desc()).first()

            if config:
                result = {
                    "id": config.id,
                    "name": config.name,
                    "version": config.version,
                    "provider": config.model_provider,
                    "model": config.model_name,
                    "parameters": config.parameters or {}
                }

                if self._redis:
                    self._redis.setex(cache_key, self._ttl, json.dumps(result))

                return result

        return None

    # =========================================================================
    # EMBEDDING CONFIG ACCESS
    # =========================================================================

    def get_embedding_config(self, name: str = "default") -> Optional[Dict[str, Any]]:
        """Get embedding/chunking configuration."""
        cache_key = self.EMBEDDING_CACHE_KEY.format(name=name)

        if self._redis:
            cached = self._redis.get(cache_key)
            if cached:
                return json.loads(cached)

        with get_db_session() as session:
            config = session.query(EmbeddingConfig).filter(
                EmbeddingConfig.name == name,
                EmbeddingConfig.is_active == True
            ).order_by(EmbeddingConfig.version.desc()).first()

            if config:
                result = {
                    "id": config.id,
                    "name": config.name,
                    "version": config.version,
                    "embedding_model": config.embedding_model,
                    "chunk_size": config.chunk_size,
                    "chunk_overlap": config.chunk_overlap,
                    "chunking_strategy": config.chunking_strategy,
                    "parameters": config.parameters or {}
                }

                if self._redis:
                    self._redis.setex(cache_key, self._ttl, json.dumps(result))

                return result

        return None

    # =========================================================================
    # CONTEXT RULES ACCESS
    # =========================================================================

    def get_context_rules(self, context: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get context rules, optionally filtered by context name.

        Args:
            context: Filter by context name (e.g., "bkash", "transaction")

        Returns:
            List of context rule dictionaries
        """
        cache_key = self.CONTEXT_RULES_CACHE_KEY
        if context:
            cache_key = f"{cache_key}:{context}"

        if self._redis:
            cached = self._redis.get(cache_key)
            if cached:
                return json.loads(cached)

        with get_db_session() as session:
            query = session.query(ContextRule).filter(
                ContextRule.is_active == True
            )

            if context:
                query = query.filter(ContextRule.context == context)

            rules = query.order_by(ContextRule.context).all()

            result = [
                {
                    "id": rule.id,
                    "context": rule.context,
                    "version": rule.version,
                    "important": rule.important,
                    "ignore": rule.ignore,
                    "description": rule.description
                }
                for rule in rules
            ]

            if self._redis:
                self._redis.setex(cache_key, self._ttl, json.dumps(result))

            return result

    # =========================================================================
    # CACHE MANAGEMENT
    # =========================================================================

    def refresh(self, config_type: str = "all") -> None:
        """
        Manually refresh cache.

        Args:
            config_type: "prompt", "model", "embedding", "context_rules", or "all"
        """
        if config_type == "all":
            self._clear_all_cache()
        else:
            pattern = f"{self.CACHE_PREFIX}{config_type}:*"
            self._clear_cache_pattern(pattern)

        logger.info(f"Cache refreshed: {config_type}")

    def publish_invalidation(
        self,
        config_type: str,
        key: Optional[str] = None
    ) -> None:
        """
        Publish cache invalidation to all workers.

        Args:
            config_type: Type of config ("prompt", "model", etc.)
            key: Specific cache key to invalidate
        """
        if self._redis:
            message = json.dumps({"type": config_type, "key": key})
            self._redis.publish(self._channel, message)

    def shutdown(self) -> None:
        """Clean shutdown of subscriber thread."""
        self._running = False
        if self._redis:
            self._redis.close()


# Convenience function for global access
def get_config_manager() -> ConfigurationManager:
    """Get the singleton ConfigurationManager instance."""
    return ConfigurationManager.get_instance()
```

---

### File: `app/repositories/config_repository.py`

```python
"""
Repository for configuration CRUD operations with changelog tracking.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar

from sqlalchemy.orm import Session

from app.db.models import (
    Prompt, ModelConfig, EmbeddingConfig, ContextRule, ConfigChangelog
)
from app.config_manager import get_config_manager

T = TypeVar("T")


class ConfigRepository:
    """
    Base repository for configuration entities.
    Automatically logs changes and invalidates cache.
    """

    def __init__(self, session: Session):
        self.session = session
        self.config_manager = get_config_manager()

    def _log_change(
        self,
        config_type: str,
        config_id: int,
        config_name: str,
        change_type: str,
        previous_version: Optional[int],
        new_version: int,
        previous_data: Optional[Dict] = None,
        new_data: Optional[Dict] = None,
        changed_by: Optional[str] = None,
        change_summary: Optional[str] = None
    ) -> None:
        """Log configuration change to changelog table."""
        changelog = ConfigChangelog(
            config_type=config_type,
            config_id=config_id,
            config_name=config_name,
            previous_version=previous_version,
            new_version=new_version,
            change_type=change_type,
            change_summary=change_summary,
            previous_data=previous_data,
            new_data=new_data,
            changed_by=changed_by
        )
        self.session.add(changelog)

    def _invalidate_cache(self, config_type: str, key: Optional[str] = None) -> None:
        """Invalidate cache for this config type."""
        self.config_manager.publish_invalidation(config_type, key)


class PromptRepository(ConfigRepository):
    """Repository for Prompt CRUD operations."""

    def get_by_name(
        self,
        name: str,
        project: str = "default",
        label: Optional[str] = None,
        version: Optional[int] = None
    ) -> Optional[Prompt]:
        """Get prompt by name with optional filters."""
        query = self.session.query(Prompt).filter(
            Prompt.project == project,
            Prompt.name == name,
            Prompt.is_active == True
        )

        if version:
            query = query.filter(Prompt.version == version)
        elif label:
            query = query.filter(Prompt.labels.contains([label]))

        return query.order_by(Prompt.version.desc()).first()

    def list_all(
        self,
        project: str = "default",
        active_only: bool = True
    ) -> List[Prompt]:
        """List all prompts for a project."""
        query = self.session.query(Prompt).filter(Prompt.project == project)

        if active_only:
            query = query.filter(Prompt.is_active == True)

        return query.order_by(Prompt.name, Prompt.version.desc()).all()

    def create(
        self,
        name: str,
        template: str,
        project: str = "default",
        prompt_type: str = "chat",
        description: Optional[str] = None,
        model: Optional[str] = None,
        parameters: Optional[Dict] = None,
        labels: Optional[List[str]] = None,
        created_by: Optional[str] = None
    ) -> Prompt:
        """Create a new prompt (version 1)."""
        prompt = Prompt(
            project=project,
            name=name,
            version=1,
            type=prompt_type,
            template=template,
            description=description,
            model=model,
            parameters=parameters,
            labels=labels or ["staging"],
            is_active=True,
            created_by=created_by
        )

        self.session.add(prompt)
        self.session.flush()  # Get ID

        self._log_change(
            config_type="prompt",
            config_id=prompt.id,
            config_name=f"{project}:{name}",
            change_type="create",
            previous_version=None,
            new_version=1,
            new_data={"template": template[:200], "labels": labels},
            changed_by=created_by,
            change_summary="Initial creation"
        )

        self._invalidate_cache("prompt")

        return prompt

    def create_version(
        self,
        name: str,
        template: str,
        project: str = "default",
        description: Optional[str] = None,
        labels: Optional[List[str]] = None,
        created_by: Optional[str] = None
    ) -> Prompt:
        """Create a new version of an existing prompt."""
        # Get current highest version
        current = self.session.query(Prompt).filter(
            Prompt.project == project,
            Prompt.name == name
        ).order_by(Prompt.version.desc()).first()

        if not current:
            return self.create(name, template, project, labels=labels, created_by=created_by)

        new_version = current.version + 1

        prompt = Prompt(
            project=project,
            name=name,
            version=new_version,
            type=current.type,
            template=template,
            description=description or current.description,
            model=current.model,
            parameters=current.parameters,
            labels=labels or ["staging"],
            is_active=True,
            created_by=created_by
        )

        self.session.add(prompt)
        self.session.flush()

        self._log_change(
            config_type="prompt",
            config_id=prompt.id,
            config_name=f"{project}:{name}",
            change_type="version",
            previous_version=current.version,
            new_version=new_version,
            previous_data={"template": current.template[:200]},
            new_data={"template": template[:200]},
            changed_by=created_by,
            change_summary=f"New version {new_version}"
        )

        self._invalidate_cache("prompt")

        return prompt

    def promote_to_label(
        self,
        name: str,
        version: int,
        label: str,
        project: str = "default",
        changed_by: Optional[str] = None
    ) -> Optional[Prompt]:
        """Add a label to a specific prompt version (e.g., promote to production)."""
        prompt = self.session.query(Prompt).filter(
            Prompt.project == project,
            Prompt.name == name,
            Prompt.version == version
        ).first()

        if not prompt:
            return None

        # Remove label from other versions
        other_prompts = self.session.query(Prompt).filter(
            Prompt.project == project,
            Prompt.name == name,
            Prompt.version != version,
            Prompt.labels.contains([label])
        ).all()

        for other in other_prompts:
            other.labels = [l for l in (other.labels or []) if l != label]

        # Add label to this version
        current_labels = prompt.labels or []
        if label not in current_labels:
            prompt.labels = current_labels + [label]

        self._log_change(
            config_type="prompt",
            config_id=prompt.id,
            config_name=f"{project}:{name}",
            change_type="promote",
            previous_version=version,
            new_version=version,
            new_data={"label": label, "version": version},
            changed_by=changed_by,
            change_summary=f"Promoted v{version} to {label}"
        )

        self._invalidate_cache("prompt")

        return prompt

    def deactivate(
        self,
        name: str,
        project: str = "default",
        version: Optional[int] = None,
        changed_by: Optional[str] = None
    ) -> int:
        """Deactivate prompt(s). Returns count of deactivated."""
        query = self.session.query(Prompt).filter(
            Prompt.project == project,
            Prompt.name == name,
            Prompt.is_active == True
        )

        if version:
            query = query.filter(Prompt.version == version)

        prompts = query.all()

        for prompt in prompts:
            prompt.is_active = False

            self._log_change(
                config_type="prompt",
                config_id=prompt.id,
                config_name=f"{project}:{name}",
                change_type="deactivate",
                previous_version=prompt.version,
                new_version=prompt.version,
                changed_by=changed_by,
                change_summary=f"Deactivated v{prompt.version}"
            )

        self._invalidate_cache("prompt")

        return len(prompts)


class ModelConfigRepository(ConfigRepository):
    """Repository for ModelConfig CRUD operations."""

    def get_by_name(
        self,
        name: str = "default",
        label: Optional[str] = None
    ) -> Optional[ModelConfig]:
        """Get model config by name."""
        query = self.session.query(ModelConfig).filter(
            ModelConfig.name == name,
            ModelConfig.is_active == True
        )

        if label:
            query = query.filter(ModelConfig.labels.contains([label]))

        return query.order_by(ModelConfig.version.desc()).first()

    def create(
        self,
        name: str,
        provider: str,
        model_name: str,
        parameters: Optional[Dict] = None,
        labels: Optional[List[str]] = None,
        changed_by: Optional[str] = None
    ) -> ModelConfig:
        """Create a new model configuration."""
        config = ModelConfig(
            name=name,
            version=1,
            model_provider=provider,
            model_name=model_name,
            parameters=parameters,
            labels=labels or ["staging"],
            is_active=True
        )

        self.session.add(config)
        self.session.flush()

        self._log_change(
            config_type="model",
            config_id=config.id,
            config_name=name,
            change_type="create",
            previous_version=None,
            new_version=1,
            new_data={"provider": provider, "model": model_name},
            changed_by=changed_by
        )

        self._invalidate_cache("model")

        return config


class EmbeddingConfigRepository(ConfigRepository):
    """Repository for EmbeddingConfig CRUD operations."""

    def get_by_name(self, name: str = "default") -> Optional[EmbeddingConfig]:
        """Get embedding config by name."""
        return self.session.query(EmbeddingConfig).filter(
            EmbeddingConfig.name == name,
            EmbeddingConfig.is_active == True
        ).order_by(EmbeddingConfig.version.desc()).first()

    def create(
        self,
        name: str,
        embedding_model: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        chunking_strategy: str = "late_chunking",
        parameters: Optional[Dict] = None,
        changed_by: Optional[str] = None
    ) -> EmbeddingConfig:
        """Create a new embedding configuration."""
        config = EmbeddingConfig(
            name=name,
            version=1,
            embedding_model=embedding_model,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            chunking_strategy=chunking_strategy,
            parameters=parameters,
            is_active=True
        )

        self.session.add(config)
        self.session.flush()

        self._log_change(
            config_type="embedding",
            config_id=config.id,
            config_name=name,
            change_type="create",
            previous_version=None,
            new_version=1,
            new_data={
                "model": embedding_model,
                "chunk_size": chunk_size,
                "strategy": chunking_strategy
            },
            changed_by=changed_by
        )

        self._invalidate_cache("embedding")

        return config
```

---

### File: `app/api/config_routes.py`

```python
"""
FastAPI routes for configuration management.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.config_repository import (
    PromptRepository, ModelConfigRepository, EmbeddingConfigRepository
)
from app.config_manager import get_config_manager

router = APIRouter(prefix="/api/config", tags=["configuration"])


# ============================================================================
# REQUEST/RESPONSE SCHEMAS
# ============================================================================

class PromptCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    template: str = Field(..., min_length=1)
    project: str = Field(default="default", max_length=100)
    type: str = Field(default="chat", max_length=50)
    description: Optional[str] = None
    model: Optional[str] = None
    parameters: Optional[dict] = None
    labels: Optional[List[str]] = Field(default=["staging"])


class PromptResponse(BaseModel):
    id: int
    name: str
    project: str
    version: int
    type: str
    template: str
    description: Optional[str]
    model: Optional[str]
    parameters: Optional[dict]
    labels: Optional[List[str]]
    is_active: bool

    class Config:
        from_attributes = True


class PromptPromoteRequest(BaseModel):
    version: int
    label: str = Field(default="production")


class ModelConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    provider: str = Field(..., min_length=1, max_length=50)
    model_name: str = Field(..., min_length=1, max_length=100)
    parameters: Optional[dict] = None
    labels: Optional[List[str]] = Field(default=["staging"])


class CacheRefreshRequest(BaseModel):
    config_type: str = Field(default="all")


# ============================================================================
# PROMPT ENDPOINTS
# ============================================================================

@router.get("/prompts", response_model=List[PromptResponse])
def list_prompts(
    project: str = Query(default="default"),
    active_only: bool = Query(default=True),
    db: Session = Depends(get_db)
):
    """List all prompts for a project."""
    repo = PromptRepository(db)
    return repo.list_all(project=project, active_only=active_only)


@router.get("/prompts/{name}", response_model=PromptResponse)
def get_prompt(
    name: str,
    project: str = Query(default="default"),
    label: Optional[str] = Query(default="production"),
    version: Optional[int] = Query(default=None),
    db: Session = Depends(get_db)
):
    """Get a specific prompt by name."""
    repo = PromptRepository(db)
    prompt = repo.get_by_name(name, project=project, label=label, version=version)

    if not prompt:
        raise HTTPException(status_code=404, detail=f"Prompt '{name}' not found")

    return prompt


@router.post("/prompts", response_model=PromptResponse, status_code=201)
def create_prompt(
    data: PromptCreate,
    db: Session = Depends(get_db)
):
    """Create a new prompt."""
    repo = PromptRepository(db)

    # Check if exists
    existing = repo.get_by_name(data.name, project=data.project)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Prompt '{data.name}' already exists. Use POST /prompts/{data.name}/versions to create a new version."
        )

    prompt = repo.create(
        name=data.name,
        template=data.template,
        project=data.project,
        prompt_type=data.type,
        description=data.description,
        model=data.model,
        parameters=data.parameters,
        labels=data.labels
    )

    db.commit()
    return prompt


@router.post("/prompts/{name}/versions", response_model=PromptResponse, status_code=201)
def create_prompt_version(
    name: str,
    data: PromptCreate,
    db: Session = Depends(get_db)
):
    """Create a new version of an existing prompt."""
    repo = PromptRepository(db)

    prompt = repo.create_version(
        name=name,
        template=data.template,
        project=data.project,
        description=data.description,
        labels=data.labels
    )

    db.commit()
    return prompt


@router.post("/prompts/{name}/promote", response_model=PromptResponse)
def promote_prompt(
    name: str,
    data: PromptPromoteRequest,
    project: str = Query(default="default"),
    db: Session = Depends(get_db)
):
    """Promote a prompt version to a label (e.g., staging -> production)."""
    repo = PromptRepository(db)

    prompt = repo.promote_to_label(
        name=name,
        version=data.version,
        label=data.label,
        project=project
    )

    if not prompt:
        raise HTTPException(
            status_code=404,
            detail=f"Prompt '{name}' version {data.version} not found"
        )

    db.commit()
    return prompt


@router.delete("/prompts/{name}")
def deactivate_prompt(
    name: str,
    project: str = Query(default="default"),
    version: Optional[int] = Query(default=None),
    db: Session = Depends(get_db)
):
    """Deactivate a prompt (soft delete)."""
    repo = PromptRepository(db)
    count = repo.deactivate(name=name, project=project, version=version)

    if count == 0:
        raise HTTPException(status_code=404, detail=f"Prompt '{name}' not found")

    db.commit()
    return {"deactivated": count}


# ============================================================================
# CACHE MANAGEMENT
# ============================================================================

@router.post("/cache/refresh")
def refresh_cache(data: CacheRefreshRequest):
    """Manually refresh configuration cache."""
    config_manager = get_config_manager()
    config_manager.refresh(data.config_type)
    return {"status": "refreshed", "type": data.config_type}


@router.get("/cache/stats")
def get_cache_stats():
    """Get cache statistics (Redis info)."""
    config_manager = get_config_manager()

    if config_manager._redis:
        info = config_manager._redis.info(section="memory")
        keys = config_manager._redis.keys(f"{config_manager.CACHE_PREFIX}*")
        return {
            "connected": True,
            "used_memory": info.get("used_memory_human"),
            "cached_keys": len(keys)
        }

    return {"connected": False, "cached_keys": 0}
```

---

## Agent Integration

### File: `app/agents/base_agent.py` (Updated)

```python
"""
Base agent class with configuration manager integration.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from app.config import settings
from app.config_manager import get_config_manager


class BaseAgent(ABC):
    """
    Base class for all agents with configuration support.

    Agents can load prompts from database via ConfigurationManager.
    """

    def __init__(self, prompt_name: Optional[str] = None):
        self.config_manager = get_config_manager()
        self._prompt_name = prompt_name
        self._cached_prompt: Optional[str] = None

    def get_prompt(
        self,
        name: Optional[str] = None,
        label: str = "production",
        **format_kwargs
    ) -> str:
        """
        Get prompt template from database, with variable substitution.

        Args:
            name: Prompt name (defaults to self._prompt_name)
            label: Environment label
            **format_kwargs: Variables to substitute in template

        Returns:
            Formatted prompt string
        """
        prompt_name = name or self._prompt_name

        if not prompt_name:
            raise ValueError("No prompt name specified")

        template = self.config_manager.get_prompt_template(
            name=prompt_name,
            label=label
        )

        if not template:
            # Fallback to hardcoded (for backwards compatibility during migration)
            template = self._get_fallback_prompt(prompt_name)

            if not template:
                raise ValueError(f"Prompt '{prompt_name}' not found")

        # Substitute variables
        if format_kwargs:
            try:
                return template.format(**format_kwargs)
            except KeyError as e:
                # Log missing key but return template as-is
                return template

        return template

    def _get_fallback_prompt(self, name: str) -> Optional[str]:
        """
        Override in subclasses to provide hardcoded fallback prompts.
        This enables gradual migration from hardcoded to database prompts.
        """
        return None

    def get_model_config(self) -> Dict[str, Any]:
        """Get current model configuration."""
        config = self.config_manager.get_model_config()

        if not config:
            # Fallback to settings
            return {
                "provider": "ollama",
                "model": settings.get("DEFAULT_MODEL", "qwen3:14b"),
                "parameters": {}
            }

        return config

    @abstractmethod
    def run(self, *args, **kwargs) -> Any:
        """Execute the agent's main task."""
        pass
```

### Example: Updated Parameter Agent

```python
# app/agents/parameter_agent.py (excerpt)

from app.agents.base_agent import BaseAgent


class ParametersAgent(BaseAgent):
    """Agent for extracting parameters from user text."""

    def __init__(self):
        super().__init__(prompt_name="parameter_extraction")

    def _build_system_prompt(
        self,
        allowed_query_keys: str,
        excluded_query_keys: str,
        allowed_domains: str,
        excluded_domains: str
    ) -> str:
        """Build system prompt with context."""
        return self.get_prompt(
            allowed_query_keys=allowed_query_keys,
            excluded_query_keys=excluded_query_keys,
            allowed_domains=allowed_domains,
            excluded_domains=excluded_domains
        )

    def _get_fallback_prompt(self, name: str) -> Optional[str]:
        """Fallback to hardcoded prompt during migration."""
        if name == "parameter_extraction":
            return '''You are a strict parameter extractor...'''  # Original hardcoded prompt
        return None
```

---

## docker-compose.yml Updates

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENV_FOR_DYNACONF=local
      - AGENTLOGGY_DATABASE_URL=postgresql://postgres:postgres@db:5432/agent_loggy
      - AGENTLOGGY_REDIS_URL=redis://redis:6379/0
      - AGENTLOGGY_OLLAMA_HOST=http://ollama:11434
    depends_on:
      - db
      - redis
      - ollama
    volumes:
      - ./config:/app/config:ro

  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: agent_loggy
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --appendonly yes
    volumes:
      - redisdata:/data

  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_models:/root/.ollama

volumes:
  pgdata:
  redisdata:
  ollama_models:
```

---

## File-by-File Implementation Steps

| Step | File | Action | Description |
|------|------|--------|-------------|
| 1 | `requirements.txt` | MODIFY | Add `dynaconf>=3.2.0`, `redis>=5.0.0` |
| 2 | `config/` | CREATE | Directory for configuration files |
| 3 | `config/settings.toml` | CREATE | Base defaults |
| 4 | `config/settings.local.toml` | CREATE | Local development overrides |
| 5 | `config/settings.staging.toml` | CREATE | Staging environment |
| 6 | `config/settings.prod.toml` | CREATE | Production environment |
| 7 | `config/.secrets.toml` | CREATE | Local secrets (gitignored) |
| 8 | `.gitignore` | MODIFY | Add `config/.secrets.toml`, `config/settings.local.toml` |
| 9 | `app/config.py` | REWRITE | Replace Pydantic with Dynaconf |
| 10 | `app/config_manager.py` | CREATE | Redis-backed configuration manager |
| 11 | `app/repositories/config_repository.py` | CREATE | Config CRUD with changelog |
| 12 | `app/api/config_routes.py` | CREATE | REST API for config management |
| 13 | `app/main.py` | MODIFY | Register config routes |
| 14 | `app/agents/base_agent.py` | CREATE | Base class with config integration |
| 15 | `app/agents/parameter_agent.py` | MODIFY | Extend BaseAgent |
| 16 | `app/agents/verify_agent.py` | MODIFY | Extend BaseAgent |
| 17 | `app/agents/analyze_agent.py` | MODIFY | Extend BaseAgent |
| 18 | `docker-compose.yml` | MODIFY | Add Redis service |

---

## Dependencies to Add

```txt
# requirements.txt additions
dynaconf>=3.2.0
redis>=5.0.0
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_config_manager.py

import pytest
from unittest.mock import MagicMock, patch
from app.config_manager import ConfigurationManager


class TestConfigurationManager:

    @pytest.fixture
    def mock_redis(self):
        with patch('app.config_manager.redis') as mock:
            mock_client = MagicMock()
            mock.from_url.return_value = mock_client
            yield mock_client

    def test_get_prompt_cache_hit(self, mock_redis):
        """Test that cached prompts are returned without DB query."""
        mock_redis.get.return_value = '{"template": "cached"}'

        mgr = ConfigurationManager.get_instance()
        mgr._redis = mock_redis

        result = mgr.get_prompt("test_prompt")

        assert result["template"] == "cached"
        mock_redis.get.assert_called_once()

    def test_get_prompt_cache_miss(self, mock_redis, db_session):
        """Test that cache miss triggers DB query and caches result."""
        mock_redis.get.return_value = None

        # Create test prompt in DB
        from app.db.models import Prompt
        prompt = Prompt(
            name="test_prompt",
            project="default",
            template="db template",
            labels=["production"]
        )
        db_session.add(prompt)
        db_session.commit()

        mgr = ConfigurationManager.get_instance()
        mgr._redis = mock_redis

        result = mgr.get_prompt("test_prompt")

        assert result["template"] == "db template"
        mock_redis.setex.assert_called_once()

    def test_cache_invalidation(self, mock_redis):
        """Test that invalidation clears correct cache keys."""
        mgr = ConfigurationManager.get_instance()
        mgr._redis = mock_redis
        mock_redis.keys.return_value = ["key1", "key2"]

        mgr.refresh("prompt")

        mock_redis.keys.assert_called()
        mock_redis.delete.assert_called()
```

### Integration Tests

```python
# tests/integration/test_config_api.py

import pytest
from fastapi.testclient import TestClient
from app.main import app


class TestConfigAPI:

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_create_prompt(self, client, db_session):
        """Test creating a new prompt via API."""
        response = client.post("/api/config/prompts", json={
            "name": "test_prompt",
            "template": "Test template content",
            "labels": ["staging"]
        })

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "test_prompt"
        assert data["version"] == 1

    def test_promote_prompt(self, client, db_session):
        """Test promoting prompt from staging to production."""
        # Create prompt
        client.post("/api/config/prompts", json={
            "name": "promote_test",
            "template": "Test",
            "labels": ["staging"]
        })

        # Promote to production
        response = client.post("/api/config/prompts/promote_test/promote", json={
            "version": 1,
            "label": "production"
        })

        assert response.status_code == 200
        assert "production" in response.json()["labels"]

    def test_cache_refresh(self, client):
        """Test manual cache refresh endpoint."""
        response = client.post("/api/config/cache/refresh", json={
            "config_type": "all"
        })

        assert response.status_code == 200
        assert response.json()["status"] == "refreshed"
```

---

## Critical Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `app/config.py` | All | Dynaconf setup (replaces Pydantic) |
| `app/config_manager.py` | All | NEW - Redis-backed config manager |
| `app/repositories/config_repository.py` | All | NEW - Config CRUD operations |
| `app/api/config_routes.py` | All | NEW - REST API for configs |
| `app/agents/base_agent.py` | All | NEW - Base agent with config support |
| `config/settings.toml` | All | NEW - Base configuration defaults |
| `docker-compose.yml` | 20-30 | Add Redis service |

---

## Rollout Strategy

### Phase 2a: Infrastructure (No Code Changes)
1. Deploy Redis container
2. Create `config/` directory structure
3. Add Dynaconf and redis to requirements.txt
4. Update docker-compose.yml

### Phase 2b: Configuration Layer
1. Rewrite `app/config.py` with Dynaconf
2. Create `app/config_manager.py`
3. Verify existing functionality unchanged

### Phase 2c: API and Repository
1. Create `app/repositories/config_repository.py`
2. Create `app/api/config_routes.py`
3. Register routes in `app/main.py`

### Phase 2d: Agent Integration
1. Create `app/agents/base_agent.py`
2. Update agents to extend BaseAgent
3. Test prompt loading from database

### Phase 2e: Feature Flag Preparation
1. Add feature flag for database prompts vs hardcoded
2. Enable gradual rollout
3. Monitor for issues

---

## Acceptance Criteria

| Criterion | Verification Procedure |
|-----------|------------------------|
| Dynaconf loads settings | `python -c "from app.config import settings; print(settings.DATABASE_URL)"` |
| Environment layering works | Set `ENV_FOR_DYNACONF=staging`, verify staging values loaded |
| Redis caching works | Create prompt via API, check Redis key exists |
| Cache invalidation works | Update prompt, verify cache cleared across workers |
| Hot-reload works | Change `fresh_var`, verify immediate effect |
| API CRUD works | POST/GET/DELETE prompts via API |
| Changelog tracked | Query `config_changelog` table after updates |
| Agent loads from DB | Parameter agent retrieves prompt from database |
| Fallback works | Delete DB prompt, verify hardcoded fallback used |
