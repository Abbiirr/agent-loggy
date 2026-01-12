# app/services/memory_service.py
"""
Service for managing conversation context window and memory summarization.

Handles token-aware context management for long conversations, ensuring
LLM prompts stay within token limits while preserving important context.
"""

from typing import Any, Dict, List, Optional
import logging

from app.config import settings
from app.services.conversation_service import ConversationService, get_conversation_service

logger = logging.getLogger(__name__)


# Default summarization prompt
SUMMARIZATION_PROMPT = """
Summarize the following conversation history for a log analysis assistant.
Preserve:
- Key parameters mentioned (dates, trace IDs, domains, project codes)
- Important findings and conclusions
- User preferences and corrections
- Error patterns and resolutions discussed

Conversation:
{messages}

Summary (be concise, focus on actionable context):
"""


class MemoryService:
    """
    Manages conversation context window and summarization.

    Provides strategies for fitting long conversations into token-limited
    LLM context windows:
    - Sliding window: Use last N messages directly
    - Summarization: Compress older messages into summary
    - Hybrid: Summary + last N messages

    Usage:
        service = MemoryService()
        context = service.get_context_window(conversation_id, max_tokens=4000)
        formatted = service.format_history_for_prompt(context, "Current query")
    """

    # Token estimation multiplier (tokens per word)
    TOKENS_PER_WORD = 1.3

    def __init__(
        self,
        conversation_service: Optional[ConversationService] = None,
        max_context_tokens: Optional[int] = None,
        summarization_threshold: Optional[int] = None,
        recent_messages_to_keep: Optional[int] = None
    ):
        """
        Initialize MemoryService.

        Args:
            conversation_service: ConversationService instance (uses singleton if None)
            max_context_tokens: Maximum tokens for context window (uses config if None)
            summarization_threshold: Number of messages before summarization kicks in (uses config if None)
            recent_messages_to_keep: Number of recent messages to always include (uses config if None)
        """
        self._conversation_service = conversation_service
        self.max_context_tokens = max_context_tokens if max_context_tokens is not None else settings.CONVERSATION_CONTEXT_TOKENS
        self.summarization_threshold = summarization_threshold if summarization_threshold is not None else settings.CONVERSATION_SUMMARIZATION_THRESHOLD
        self.recent_messages_to_keep = recent_messages_to_keep if recent_messages_to_keep is not None else settings.CONVERSATION_RECENT_MESSAGES

    @property
    def conversation_service(self) -> ConversationService:
        """Get conversation service (lazy initialization)."""
        if self._conversation_service is None:
            self._conversation_service = get_conversation_service()
        return self._conversation_service

    # ─── Token Estimation ─────────────────────────────────────────────────

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses a simple word-based estimation. More accurate tokenization
        would require a tokenizer library.

        Args:
            text: Text to estimate tokens for

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Split on whitespace and count words
        words = text.split()
        word_count = len(words)

        # Apply multiplier (accounts for subword tokenization)
        return int(word_count * self.TOKENS_PER_WORD)

    def estimate_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Estimate total tokens for a list of messages.

        Args:
            messages: List of message dicts with 'role' and 'content'

        Returns:
            Total estimated token count
        """
        total = 0
        for msg in messages:
            # Add role overhead (approximately 4 tokens per message for formatting)
            total += 4
            total += self.estimate_tokens(msg.get("content", ""))
        return total

    # ─── Context Window ───────────────────────────────────────────────────

    def get_context_window(
        self,
        conversation_id: str,
        max_tokens: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Get messages that fit within token budget.

        Strategy: [summary if exists] + [recent N messages]

        Args:
            conversation_id: The conversation's UUID
            max_tokens: Maximum tokens for context (uses default if None)

        Returns:
            List of messages in LLM format [{role, content}, ...]
        """
        if max_tokens is None:
            max_tokens = self.max_context_tokens

        # Get conversation for summary
        conv = self.conversation_service.get_conversation(conversation_id)
        if not conv:
            return []

        # Get all messages
        messages = self.conversation_service.get_messages(
            conversation_id,
            limit=100  # Get enough messages
        )

        if not messages:
            return []

        context = []
        tokens_used = 0

        # Include summary as system message if it exists
        if conv.summary:
            summary_msg = {
                "role": "system",
                "content": f"Previous conversation summary: {conv.summary}"
            }
            summary_tokens = self.estimate_tokens(summary_msg["content"]) + 4
            context.append(summary_msg)
            tokens_used += summary_tokens

        # Convert messages to LLM format
        llm_messages = [msg.to_llm_format() for msg in messages]

        # Calculate tokens needed for all messages
        total_message_tokens = self.estimate_messages_tokens(llm_messages)

        if tokens_used + total_message_tokens <= max_tokens:
            # All messages fit
            context.extend(llm_messages)
        else:
            # Need to trim - prioritize recent messages
            remaining_budget = max_tokens - tokens_used

            # Work backwards from most recent
            selected = []
            for msg in reversed(llm_messages):
                msg_tokens = self.estimate_tokens(msg["content"]) + 4
                if remaining_budget >= msg_tokens:
                    selected.insert(0, msg)
                    remaining_budget -= msg_tokens
                else:
                    break

            context.extend(selected)

        return context

    # ─── Summarization ────────────────────────────────────────────────────

    def should_summarize(self, conversation_id: str) -> bool:
        """
        Check if conversation should be summarized.

        Args:
            conversation_id: The conversation's UUID

        Returns:
            True if message count exceeds threshold
        """
        messages = self.conversation_service.get_messages(
            conversation_id,
            limit=self.summarization_threshold + 1
        )
        return len(messages) > self.summarization_threshold

    def summarize_old_messages(self, conversation_id: str) -> Optional[str]:
        """
        Compress older messages into a summary.

        Keeps recent messages intact, summarizes older ones.

        Args:
            conversation_id: The conversation's UUID

        Returns:
            Generated summary or None
        """
        conv = self.conversation_service.get_conversation(conversation_id)
        if not conv:
            return None

        messages = self.conversation_service.get_messages(
            conversation_id,
            limit=100
        )

        if len(messages) <= self.recent_messages_to_keep:
            return None

        # Get messages to summarize (excluding recent ones)
        to_summarize = messages[:-self.recent_messages_to_keep]

        if not to_summarize:
            return None

        # Format messages for summarization
        formatted_messages = "\n".join([
            f"{msg.role.upper()}: {msg.content}"
            for msg in to_summarize
        ])

        # Call LLM for summary
        try:
            summary = self._call_llm_for_summary(formatted_messages)
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            # Fallback to simple truncation
            summary = self._create_fallback_summary(to_summarize)

        # Update conversation with summary
        self.conversation_service.update_conversation(
            conversation_id,
            summary=summary,
            summary_token_count=self.estimate_tokens(summary)
        )

        return summary

    def _call_llm_for_summary(self, messages_text: str) -> str:
        """
        Call LLM to generate summary.

        Uses the configured LLM provider to generate a concise summary
        of conversation history.

        Args:
            messages_text: Formatted messages text

        Returns:
            Generated summary
        """
        from app.services.llm_providers import create_llm_provider

        try:
            provider, model = create_llm_provider()

            prompt = SUMMARIZATION_PROMPT.format(messages=messages_text)
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that summarizes conversations concisely."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            response = provider.chat(model=model, messages=messages)

            # Extract content from response
            if isinstance(response, dict):
                content = response.get("message", {}).get("content", "")
                if content:
                    return content.strip()

            # Fallback if response format unexpected
            logger.warning(f"Unexpected LLM response format: {type(response)}")
            return self._create_fallback_summary_from_text(messages_text)

        except Exception as e:
            logger.error(f"LLM summarization failed: {e}")
            raise  # Let caller handle with fallback

    def _create_fallback_summary_from_text(self, messages_text: str) -> str:
        """
        Create a simple fallback summary from messages text.

        Args:
            messages_text: Formatted messages text

        Returns:
            Simple summary string
        """
        lines = messages_text.split("\n")
        if len(lines) > 5:
            return f"Conversation summary ({len(lines)} messages): " + lines[0][:100]
        return messages_text[:200]

    def _create_fallback_summary(self, messages: list) -> str:
        """
        Create a simple fallback summary when LLM is unavailable.

        Args:
            messages: List of Message objects

        Returns:
            Simple summary string
        """
        if not messages:
            return ""

        # Extract key information
        user_messages = [m for m in messages if m.role == "user"]

        if user_messages:
            first = user_messages[0].content[:100]
            last = user_messages[-1].content[:100] if len(user_messages) > 1 else ""
            return f"Discussed: {first}... ({len(messages)} messages total)"

        return f"Conversation with {len(messages)} messages"

    # ─── History Formatting ───────────────────────────────────────────────

    def format_history_for_prompt(
        self,
        history: List[Dict[str, str]],
        current_query: str
    ) -> str:
        """
        Format conversation history for agent prompts.

        Creates a readable format for including in LLM system prompts.

        Args:
            history: List of message dicts [{role, content}, ...]
            current_query: The current user query

        Returns:
            Formatted string for prompt inclusion
        """
        sections = []

        # Add history if present
        if history:
            sections.append("## Previous Conversation:")
            for msg in history:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")

                if role == "system":
                    sections.append(f"[Context: {content}]")
                elif role == "user":
                    sections.append(f"User: {content}")
                elif role == "assistant":
                    sections.append(f"Assistant: {content}")

            sections.append("")  # Empty line separator

        # Add current query
        sections.append("## Current Query:")
        sections.append(current_query)

        return "\n".join(sections)

    def get_messages_for_context(
        self,
        conversation_id: str,
        exclude_last: int = 0
    ) -> List[Dict[str, str]]:
        """
        Get messages suitable for context, optionally excluding recent ones.

        Useful when you want to include history but exclude the current
        message being processed.

        Args:
            conversation_id: The conversation's UUID
            exclude_last: Number of recent messages to exclude

        Returns:
            List of messages in LLM format
        """
        messages = self.conversation_service.get_messages(
            conversation_id,
            limit=100
        )

        if exclude_last > 0 and len(messages) > exclude_last:
            messages = messages[:-exclude_last]

        return [msg.to_llm_format() for msg in messages]


# Singleton instance for convenience
_memory_service: Optional[MemoryService] = None


def get_memory_service() -> MemoryService:
    """Get the singleton MemoryService instance."""
    global _memory_service
    if _memory_service is None:
        _memory_service = MemoryService()
    return _memory_service
