# app/startup.py
"""
Application startup logic and health checks.
"""

import asyncio
import logging
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx
from fastapi import FastAPI

from app.config import settings
from app.db.session import init_database


logger = logging.getLogger(__name__)

# Configure thread pool size for blocking operations (LLM calls, file I/O)
# Default: 40 threads to handle multiple concurrent LLM requests
THREAD_POOL_SIZE = int(os.getenv("THREAD_POOL_SIZE", "40"))


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
    # Configure larger thread pool for blocking operations (LLM calls, file I/O)
    # This allows multiple concurrent requests to run blocking operations
    # without exhausting the default pool and blocking Swagger/health endpoints
    executor = ThreadPoolExecutor(max_workers=THREAD_POOL_SIZE)
    loop = asyncio.get_running_loop()
    loop.set_default_executor(executor)
    logger.info(f"Configured thread pool with {THREAD_POOL_SIZE} workers")

    # Startup
    init_database()

    if not await is_ollama_running(settings.OLLAMA_HOST):
        logger.critical("Ollama not running; start with 'ollama serve'.")
        sys.exit(1)
    logger.info("Ollama is up and running")

    yield

    # Shutdown
    logger.info("Application shutting down")
    executor.shutdown(wait=False)
