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

    # ─── Feature flags for gradual DB migration ──────────────
    USE_DB_PROMPTS: bool = False
    USE_DB_SETTINGS: bool = False
    USE_DB_PROJECTS: bool = False

    # ─── Tell Pydantic-Settings how to load .env ─────────────
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# one global Settings instance
settings = Settings()
