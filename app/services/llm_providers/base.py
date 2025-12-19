"""LLM Provider Protocol - defines the interface for all LLM providers."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol defining the interface for LLM providers.

    All providers must implement:
    - provider_name: Identifier for the provider
    - chat(): Send chat completion requests
    - is_available(): Check provider availability
    """

    @property
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'ollama', 'openrouter')."""
        ...

    def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Send a chat completion request.

        Args:
            model: The model identifier
            messages: List of message dicts with 'role' and 'content' keys
            options: Optional provider-specific options (timeout, temperature, etc.)

        Returns:
            Dict with at least {"message": {"role": str, "content": str}}
        """
        ...

    def is_available(self) -> bool:
        """Check if the provider is available and configured."""
        ...
