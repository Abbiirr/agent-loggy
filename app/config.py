# app/core/config.py

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    # ─── Your existing settings ──────────────────────────────
    DATABASE_URL: str
    DATABASE_SCHEMA: str
    OLLAMA_HOST: str
    ANALYSIS_DIR : str
    MODEL: str

    # ─── LLM Provider Configuration ───────────────────────────
    LLM_PROVIDER: str = "ollama"  # "ollama" | "openrouter"
    OPENROUTER_API_KEY: Optional[str] = None
    OPENROUTER_MODEL: Optional[str] = None  # If set, used instead of MODEL for OpenRouter

    # ─── Feature flags for gradual DB migration ──────────────
    USE_DB_PROMPTS: bool = False
    USE_DB_SETTINGS: bool = False
    USE_DB_PROJECTS: bool = False

    # --- LLM cache / gateway ---
    LLM_CACHE_ENABLED: bool = False
    LLM_CACHE_NAMESPACE: str = "default"
    LLM_CACHE_L1_MAX_ENTRIES: int = 10_000
    LLM_CACHE_L1_TTL_SECONDS: int = 60

    # Enable shared (cross-worker/pod) cache with Redis (requires `redis` package)
    LLM_CACHE_L2_ENABLED: bool = False
    LLM_CACHE_REDIS_URL: Optional[str] = None
    # If true and `LLM_CACHE_REDIS_URL` is set, L2 will be enabled automatically when Redis is reachable.
    LLM_CACHE_L2_AUTO_ENABLE: bool = True

    # Explicit invalidation knobs (bumped when prompts/gateway behavior changes)
    LLM_GATEWAY_VERSION: str = "v1"
    PROMPT_VERSION: str = "v1"

    # ─── Loki cache settings ─────────────────────────────────
    LOKI_CACHE_ENABLED: bool = True
    LOKI_CACHE_REDIS_ENABLED: bool = False  # Enable Redis persistence for Loki cache
    LOKI_CACHE_REDIS_URL: Optional[str] = None  # Falls back to LLM_CACHE_REDIS_URL if not set
    LOKI_CACHE_TTL_SECONDS: int = 14400  # 4 hours for general queries
    LOKI_CACHE_TRACE_TTL_SECONDS: int = 21600  # 6 hours for trace-specific queries

    # ─── Knowledge Base / RAG Configuration ─────────────────
    KB_EMBEDDING_MODEL: str = "nomic-embed-text"  # Ollama embedding model
    KB_EMBEDDING_DIMENSIONS: int = 768
    KB_EMBEDDING_BATCH_SIZE: int = 32
    KB_EMBEDDING_CACHE_ENABLED: bool = True
    KB_EMBEDDING_CACHE_TTL_SECONDS: int = 86400  # 24 hours
    KB_CODEBASE_PATH: str = "codebase"  # Path to source code to index
    KB_RETRIEVAL_TOP_K: int = 10  # Default number of results to retrieve
    KB_RETRIEVAL_MIN_SIMILARITY: float = 0.5  # Minimum cosine similarity threshold

    # ─── Tell Pydantic-Settings how to load .env ─────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# one global Settings instance
settings = Settings()
