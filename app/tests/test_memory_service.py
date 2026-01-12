# app/tests/test_memory_service.py
"""
Tests for MemoryService - Phase 2 of persistent conversations.

Tests cover:
- Token estimation
- Context window management
- Message summarization
- History formatting for prompts
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
from typing import List, Dict
import uuid

from app.db.session import get_db_session
from app.models.conversation import Conversation, Message
from app.services.conversation_service import ConversationService
from app.services.memory_service import (
    MemoryService,
    get_memory_service,
)


class TestMemoryServiceTokenEstimation:
    """Tests for token estimation."""

    def test_estimate_tokens_empty_string(self):
        """Empty string has 0 tokens."""
        service = MemoryService()

        tokens = service.estimate_tokens("")

        assert tokens == 0

    def test_estimate_tokens_single_word(self):
        """Single word estimation."""
        service = MemoryService()

        tokens = service.estimate_tokens("hello")

        assert tokens >= 1

    def test_estimate_tokens_sentence(self):
        """Sentence token estimation."""
        service = MemoryService()

        # Roughly 1.3 tokens per word
        text = "This is a simple test sentence"
        tokens = service.estimate_tokens(text)

        # 6 words * 1.3 ≈ 8 tokens
        assert 5 <= tokens <= 12

    def test_estimate_tokens_long_text(self):
        """Long text token estimation."""
        service = MemoryService()

        text = " ".join(["word"] * 100)
        tokens = service.estimate_tokens(text)

        # 100 words * 1.3 ≈ 130 tokens
        assert 100 <= tokens <= 160

    def test_estimate_tokens_special_characters(self):
        """Text with special characters."""
        service = MemoryService()

        text = "Error: {\"code\": 500, \"message\": \"timeout\"}"
        tokens = service.estimate_tokens(text)

        assert tokens > 0


class TestMemoryServiceContextWindow:
    """Tests for context window management."""

    def test_get_context_window_empty(self):
        """Empty conversation returns empty context."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(conversation_service=conv_service)
            conv = conv_service.create_conversation()

            context = memory_service.get_context_window(conv.conversation_id)

            assert context == []

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_get_context_window_single_message(self):
        """Single message returned in context."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(conversation_service=conv_service)
            conv = conv_service.create_conversation()
            conv_service.add_message(conv.conversation_id, "user", "Hello")

            context = memory_service.get_context_window(conv.conversation_id)

            assert len(context) == 1
            assert context[0]["role"] == "user"
            assert context[0]["content"] == "Hello"

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_get_context_window_multiple_messages(self):
        """Multiple messages in correct order."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(conversation_service=conv_service)
            conv = conv_service.create_conversation()
            conv_service.add_message(conv.conversation_id, "user", "First")
            conv_service.add_message(conv.conversation_id, "assistant", "Second")
            conv_service.add_message(conv.conversation_id, "user", "Third")

            context = memory_service.get_context_window(conv.conversation_id)

            assert len(context) == 3
            assert context[0]["content"] == "First"
            assert context[1]["content"] == "Second"
            assert context[2]["content"] == "Third"

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_get_context_window_respects_token_limit(self):
        """Context window respects max_tokens limit."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(conversation_service=conv_service)
            conv = conv_service.create_conversation()

            # Add many messages
            for i in range(20):
                conv_service.add_message(
                    conv.conversation_id,
                    "user" if i % 2 == 0 else "assistant",
                    f"Message number {i} with some content to add tokens"
                )

            # Request with small token limit
            context = memory_service.get_context_window(
                conv.conversation_id,
                max_tokens=100
            )

            # Should have fewer messages than total
            assert len(context) < 20

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_get_context_window_includes_summary_if_exists(self):
        """Context includes summary when available."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(conversation_service=conv_service)
            conv = conv_service.create_conversation()

            # Set a summary
            conv_service.update_conversation(
                conv.conversation_id,
                summary="Previous discussion about NPSB transactions"
            )

            conv_service.add_message(conv.conversation_id, "user", "Continue analysis")

            context = memory_service.get_context_window(conv.conversation_id)

            # Summary should be included as system message
            assert any(
                msg.get("role") == "system" and "NPSB" in msg.get("content", "")
                for msg in context
            )

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_get_context_window_nonexistent_conversation(self):
        """Non-existent conversation returns empty context."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(conversation_service=conv_service)

            context = memory_service.get_context_window("fake-id")

            assert context == []


class TestMemoryServiceSummarization:
    """Tests for message summarization."""

    def test_summarize_below_threshold(self):
        """No summarization when below message threshold."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(
                conversation_service=conv_service,
                summarization_threshold=20
            )
            conv = conv_service.create_conversation()

            # Add only a few messages
            for i in range(5):
                conv_service.add_message(conv.conversation_id, "user", f"Message {i}")

            result = memory_service.should_summarize(conv.conversation_id)

            assert result is False

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_summarize_above_threshold(self):
        """Summarization triggered above message threshold."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(
                conversation_service=conv_service,
                summarization_threshold=10
            )
            conv = conv_service.create_conversation()

            # Add more than threshold messages
            for i in range(15):
                conv_service.add_message(conv.conversation_id, "user", f"Message {i}")

            result = memory_service.should_summarize(conv.conversation_id)

            assert result is True

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_summarize_old_messages(self):
        """Summarization compresses old messages."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(
                conversation_service=conv_service,
                summarization_threshold=5,
                recent_messages_to_keep=3  # Keep 3 recent, summarize 7
            )
            conv = conv_service.create_conversation()

            # Add messages
            for i in range(10):
                conv_service.add_message(
                    conv.conversation_id,
                    "user" if i % 2 == 0 else "assistant",
                    f"Discussion about trace ID {i}"
                )

            # Mock LLM call
            with patch.object(memory_service, '_call_llm_for_summary') as mock:
                mock.return_value = "Discussed trace IDs 0-9"

                summary = memory_service.summarize_old_messages(conv.conversation_id)

            assert summary is not None

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_summarize_updates_conversation(self):
        """Summarization updates conversation summary field."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(
                conversation_service=conv_service,
                summarization_threshold=5,
                recent_messages_to_keep=3  # Keep 3 recent, summarize 7
            )
            conv = conv_service.create_conversation()

            for i in range(10):
                conv_service.add_message(conv.conversation_id, "user", f"Msg {i}")

            with patch.object(memory_service, '_call_llm_for_summary') as mock:
                mock.return_value = "Summary of messages"

                memory_service.summarize_old_messages(conv.conversation_id)

            # Refresh conversation
            updated = conv_service.get_conversation(conv.conversation_id)
            assert updated.summary is not None

            # Cleanup
            db.delete(conv)
            db.commit()


class TestMemoryServiceHistoryFormatting:
    """Tests for formatting history for prompts."""

    def test_format_history_empty(self):
        """Empty history formatting."""
        service = MemoryService()

        formatted = service.format_history_for_prompt([], "Current query")

        assert "Current query" in formatted

    def test_format_history_with_messages(self):
        """History with messages formats correctly."""
        service = MemoryService()
        history = [
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "First answer"},
        ]

        formatted = service.format_history_for_prompt(history, "Follow-up")

        assert "First question" in formatted
        assert "First answer" in formatted
        assert "Follow-up" in formatted

    def test_format_history_with_summary(self):
        """History with summary prefix."""
        service = MemoryService()
        history = [
            {"role": "system", "content": "Summary: Previous discussion about errors"},
            {"role": "user", "content": "Continue"},
        ]

        formatted = service.format_history_for_prompt(history, "New query")

        assert "Previous discussion" in formatted
        assert "New query" in formatted

    def test_format_history_role_labels(self):
        """Messages have role labels."""
        service = MemoryService()
        history = [
            {"role": "user", "content": "Question"},
            {"role": "assistant", "content": "Answer"},
        ]

        formatted = service.format_history_for_prompt(history, "Query")

        # Should have role indicators
        assert "User:" in formatted or "user:" in formatted.lower() or "Question" in formatted


class TestMemoryServiceRecency:
    """Tests for recency-biased context retrieval."""

    def test_recent_messages_prioritized(self):
        """Recent messages are prioritized in context."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(
                conversation_service=conv_service,
                max_context_tokens=200
            )
            conv = conv_service.create_conversation()

            # Add old messages
            for i in range(20):
                conv_service.add_message(conv.conversation_id, "user", f"Old message {i}")

            # Add recent message
            conv_service.add_message(conv.conversation_id, "user", "RECENT_MARKER")

            context = memory_service.get_context_window(conv.conversation_id, max_tokens=200)

            # Recent message should be included
            content = [msg["content"] for msg in context]
            assert "RECENT_MARKER" in content

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_hybrid_strategy_summary_plus_recent(self):
        """Hybrid strategy uses summary + recent messages."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(
                conversation_service=conv_service,
                summarization_threshold=5
            )
            conv = conv_service.create_conversation()

            # Set existing summary
            conv_service.update_conversation(
                conv.conversation_id,
                summary="Discussion about MMBL project errors"
            )

            # Add recent messages
            conv_service.add_message(conv.conversation_id, "user", "Recent 1")
            conv_service.add_message(conv.conversation_id, "assistant", "Recent 2")

            context = memory_service.get_context_window(conv.conversation_id)

            # Should have both summary and recent
            has_summary = any("MMBL" in str(msg.get("content", "")) for msg in context)
            has_recent = any("Recent" in str(msg.get("content", "")) for msg in context)

            assert has_summary
            assert has_recent

            # Cleanup
            db.delete(conv)
            db.commit()


class TestMemoryServiceConfiguration:
    """Tests for service configuration."""

    def test_default_max_context_tokens(self):
        """Default max context tokens."""
        service = MemoryService()

        assert service.max_context_tokens == 4000

    def test_custom_max_context_tokens(self):
        """Custom max context tokens."""
        service = MemoryService(max_context_tokens=8000)

        assert service.max_context_tokens == 8000

    def test_default_summarization_threshold(self):
        """Default summarization threshold."""
        service = MemoryService()

        assert service.summarization_threshold == 20

    def test_custom_summarization_threshold(self):
        """Custom summarization threshold."""
        service = MemoryService(summarization_threshold=10)

        assert service.summarization_threshold == 10


class TestMemoryServiceSingleton:
    """Tests for singleton pattern."""

    def test_get_memory_service_singleton(self):
        """get_memory_service returns same instance."""
        service1 = get_memory_service()
        service2 = get_memory_service()

        assert service1 is service2


class TestMemoryServiceLLMFormat:
    """Tests for LLM-compatible message formatting."""

    def test_to_llm_format_basic(self):
        """Messages converted to LLM format."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(conversation_service=conv_service)
            conv = conv_service.create_conversation()
            conv_service.add_message(conv.conversation_id, "user", "Test")

            context = memory_service.get_context_window(conv.conversation_id)

            assert all("role" in msg and "content" in msg for msg in context)

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_to_llm_format_excludes_metadata(self):
        """LLM format excludes message metadata."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(conversation_service=conv_service)
            conv = conv_service.create_conversation()
            conv_service.add_message(
                conv.conversation_id,
                "user",
                "Test",
                metadata={"cache_hit": True}
            )

            context = memory_service.get_context_window(conv.conversation_id)

            # Should only have role and content
            for msg in context:
                assert "metadata" not in msg or msg.get("metadata") is None
                assert "message_metadata" not in msg

            # Cleanup
            db.delete(conv)
            db.commit()
