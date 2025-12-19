"""Ollama LLM Provider - wraps the Ollama client."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx
from ollama import Client

logger = logging.getLogger(__name__)


class OllamaProvider:
    """LLM provider wrapping the Ollama client."""

    def __init__(self, host: str):
        """Initialize the Ollama provider.

        Args:
            host: Ollama server URL (e.g., 'http://localhost:11434')
        """
        self._host = host
        self._client = Client(host=host)
        logger.info(f"Initialized OllamaProvider with host: {host}")

    @property
    def provider_name(self) -> str:
        return "ollama"

    def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send chat completion via Ollama.

        Args:
            model: Model name (e.g., 'llama3', 'qwen3:14b')
            messages: List of message dicts
            options: Ollama-specific options (timeout, temperature, etc.)

        Returns:
            Dict with {"message": {"role": "assistant", "content": "..."}, ...}
        """
        options = options or {}
        response = self._client.chat(
            model=model,
            messages=messages,
            options=options,
        )
        return response

    def is_available(self) -> bool:
        """Check if Ollama server is reachable."""
        try:
            resp = httpx.get(f"{self._host}/", timeout=5.0)
            return resp.status_code == 200
        except Exception as e:
            logger.debug(f"Ollama availability check failed: {e}")
            return False
