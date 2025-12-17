# app/dependencies.py
"""
Shared dependencies for FastAPI routes.
"""

from ollama import Client

from app.orchestrator import Orchestrator
from app.config import settings


# Create Ollama client and Orchestrator once
client = Client(host=settings.OLLAMA_HOST)
orchestrator = Orchestrator(client, model=settings.MODEL, log_base_dir="data")

# Store active sessions (in production, use Redis or proper session management)
active_sessions: dict = {}


def get_orchestrator() -> Orchestrator:
    """Dependency to get the orchestrator instance."""
    return orchestrator


def get_active_sessions() -> dict:
    """Dependency to get the active sessions store."""
    return active_sessions
