# app/startup.py
"""
Application startup logic and health checks.
"""

import logging
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx
from fastapi import FastAPI

from app.config import settings
from app.db.session import init_database


logger = logging.getLogger(__name__)


async def is_ollama_running(host: str) -> bool:
    """Check if Ollama server is running and accessible."""
    try:
        r = httpx.get(f"{host}/", timeout=2.0)
        return r.status_code == 200
    except Exception:
        return False


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler for startup and shutdown events."""
    # Startup
    init_database()

    if not await is_ollama_running(settings.OLLAMA_HOST):
        logger.critical("Ollama not running; start with 'ollama serve'.")
        sys.exit(1)
    logger.info("Ollama is up and running")

    yield

    # Shutdown (add cleanup logic here if needed)
    logger.info("Application shutting down")
