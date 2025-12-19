"""Factory function for creating LLM providers based on configuration."""
from __future__ import annotations

import logging
from typing import Tuple

from app.config import settings
from .base import LLMProvider
from .ollama_provider import OllamaProvider
from .openrouter_provider import OpenRouterProvider

logger = logging.getLogger(__name__)


def create_llm_provider() -> Tuple[LLMProvider, str]:
    """Create an LLM provider based on configuration.

    Reads LLM_PROVIDER from settings and instantiates the appropriate provider.

    Returns:
        Tuple of (provider instance, model name to use)

    Raises:
        ValueError: If provider is not configured correctly
    """
    provider_name = settings.LLM_PROVIDER.lower()

    if provider_name == "ollama":
        logger.info(f"Creating Ollama provider at {settings.OLLAMA_HOST}")
        provider = OllamaProvider(host=settings.OLLAMA_HOST)
        model = settings.MODEL
        return provider, model

    elif provider_name == "openrouter":
        if not settings.OPENROUTER_API_KEY:
            raise ValueError(
                "OpenRouter provider requires OPENROUTER_API_KEY environment variable"
            )
        # Use OPENROUTER_MODEL if set, otherwise fall back to MODEL
        model = settings.OPENROUTER_MODEL or settings.MODEL
        logger.info(f"Creating OpenRouter provider with model: {model}")
        provider = OpenRouterProvider(api_key=settings.OPENROUTER_API_KEY)
        return provider, model

    else:
        raise ValueError(
            f"Unknown LLM provider: {provider_name}. "
            f"Supported providers: ollama, openrouter"
        )
