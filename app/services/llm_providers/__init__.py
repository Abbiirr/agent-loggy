"""LLM Provider abstraction layer.

Enables switching between LLM providers (Ollama, OpenRouter, etc.) via configuration.

Usage:
    from app.services.llm_providers import create_llm_provider, LLMProvider

    provider, model = create_llm_provider()
    response = provider.chat(model=model, messages=[...])

Configuration:
    Set LLM_PROVIDER env var to switch providers:
    - LLM_PROVIDER=ollama (default)
    - LLM_PROVIDER=openrouter
"""
from .base import LLMProvider
from .factory import create_llm_provider
from .ollama_provider import OllamaProvider
from .openrouter_provider import OpenRouterProvider

__all__ = [
    "LLMProvider",
    "create_llm_provider",
    "OllamaProvider",
    "OpenRouterProvider",
]
