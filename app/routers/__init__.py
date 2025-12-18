# app/routers/__init__.py
"""
API routers for agent-loggy.
"""

from app.routers.chat import router as chat_router
from app.routers.analysis import router as analysis_router
from app.routers.files import router as files_router
from app.routers.cache_admin import router as cache_router

__all__ = ["chat_router", "analysis_router", "files_router", "cache_router"]
