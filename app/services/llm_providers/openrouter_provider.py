"""OpenRouter LLM Provider - uses OpenAI-compatible API."""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterProvider:
    """LLM provider for OpenRouter API (OpenAI-compatible)."""

    def __init__(self, api_key: str, site_url: str = "https://agent-loggy.local"):
        """Initialize the OpenRouter provider.

        Args:
            api_key: OpenRouter API key
            site_url: Site URL for OpenRouter headers (required by their API)
        """
        self._api_key = api_key
        self._site_url = site_url
        self._http_client = httpx.Client(timeout=120.0)
        logger.info("Initialized OpenRouterProvider")

    @property
    def provider_name(self) -> str:
        return "openrouter"

    def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send chat completion via OpenRouter API.

        OpenRouter uses OpenAI-compatible API format. This method transforms
        the response to match Ollama's format for compatibility.

        Args:
            model: Model identifier (e.g., 'anthropic/claude-3.5-sonnet')
            messages: List of message dicts
            options: Options dict (timeout, temperature, max_tokens, etc.)

        Returns:
            Dict with {"message": {"role": "assistant", "content": "..."}}
        """
        options = options or {}

        # Extract timeout from options (our convention)
        timeout = options.pop("timeout", 120)

        # Build request payload
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
        }

        # Map common options to OpenAI format
        if "temperature" in options:
            payload["temperature"] = options["temperature"]
        if "max_tokens" in options:
            payload["max_tokens"] = options["max_tokens"]

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self._site_url,
            "X-Title": "agent-loggy",
        }

        # Log request
        msg_count = len(messages)
        logger.info(f"OpenRouter request: model={model}, messages={msg_count}, timeout={timeout}s")
        start_time = time.time()

        try:
            response = self._http_client.post(
                OPENROUTER_API_URL,
                json=payload,
                headers=headers,
                timeout=float(timeout),
            )
            elapsed = time.time() - start_time

            if response.status_code != 200:
                logger.error(f"OpenRouter error: status={response.status_code}, elapsed={elapsed:.2f}s, body={response.text[:500]}")
                response.raise_for_status()

            data = response.json()

            # Log usage if available
            usage = data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", "?")
            completion_tokens = usage.get("completion_tokens", "?")
            logger.info(f"OpenRouter response: status=200, elapsed={elapsed:.2f}s, tokens={prompt_tokens}+{completion_tokens}")

        except httpx.TimeoutException as e:
            elapsed = time.time() - start_time
            logger.error(f"OpenRouter timeout after {elapsed:.2f}s: {e}")
            raise

        # Transform OpenAI format to Ollama-compatible format
        # OpenAI: {"choices": [{"message": {"role": "...", "content": "..."}}]}
        # Ollama: {"message": {"role": "...", "content": "..."}}
        if "choices" in data and len(data["choices"]) > 0:
            return {"message": data["choices"][0]["message"]}

        raise ValueError("Invalid response from OpenRouter API")

    def is_available(self) -> bool:
        """Check if OpenRouter API key is configured."""
        return bool(self._api_key)
