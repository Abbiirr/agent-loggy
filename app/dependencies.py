# app/dependencies.py
"""
Shared dependencies for FastAPI routes.
"""

from app.orchestrator import Orchestrator
from app.services.llm_providers import create_llm_provider


# Create LLM provider and Orchestrator once
llm_provider, model = create_llm_provider()
orchestrator = Orchestrator(llm_provider, model=model, log_base_dir="data")

# Store active sessions (in production, use Redis or proper session management)
active_sessions: dict = {}


def get_orchestrator() -> Orchestrator:
    """Dependency to get the orchestrator instance."""
    return orchestrator


def get_active_sessions() -> dict:
    """Dependency to get the active sessions store."""
    return active_sessions
