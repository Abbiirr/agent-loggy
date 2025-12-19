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
from app.services.llm_providers import create_llm_provider


logger = logging.getLogger(__name__)

# Configure thread pool size for blocking operations (LLM calls, file I/O)
# Default: 40 threads to handle multiple concurrent LLM requests
THREAD_POOL_SIZE = int(os.getenv("THREAD_POOL_SIZE", "40"))


def check_llm_provider_available() -> tuple[bool, str]:
    """Check if the configured LLM provider is available.

    Returns:
        Tuple of (is_available, provider_name)
    """
    try:
        provider, model = create_llm_provider()
        return provider.is_available(), provider.provider_name
    except ValueError as e:
        logger.error(f"Failed to create LLM provider: {e}")
        return False, "unknown"


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

    # Check LLM provider availability
    is_available, provider_name = check_llm_provider_available()
    if not is_available:
        logger.warning(f"LLM provider '{provider_name}' is not available - some features may not work")
    else:
        logger.info(f"LLM provider '{provider_name}' is ready")

    yield

    # Shutdown
    logger.info("Application shutting down")
    executor.shutdown(wait=False)
