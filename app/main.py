# main.py
# !/usr/bin/env python3
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import chat_router, analysis_router, files_router, cache_router
from app.startup import lifespan

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

# Initialize FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# Add CORS middleware for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router)
app.include_router(analysis_router)
app.include_router(files_router)
app.include_router(cache_router)


@app.get("/health", tags=["health"])
async def health_check():
    """
    Lightweight health check endpoint.
    Returns immediately without any blocking operations.
    Use this to verify the server is responsive even during heavy processing.
    """
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    import os

    # Set DEV_MODE=true for hot reload (single worker, development only)
    dev_mode = os.getenv("DEV_MODE", "false").lower() == "true"

    if dev_mode:
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
    else:
        # Auto-calculate optimal workers for I/O-bound workloads
        # Formula: (2 * CPU cores) + 1
        # Can be overridden with WORKERS env var
        cpu_count = os.cpu_count() or 4
        default_workers = (cpu_count * 2) + 1
        workers = int(os.getenv("WORKERS", default_workers))

        print(f"Starting with {workers} workers (CPU cores: {cpu_count})")
        uvicorn.run("app.main:app", host="0.0.0.0", port=8000, workers=workers)
