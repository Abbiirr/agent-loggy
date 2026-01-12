# app/tests/test_conversation_flow.py
"""
End-to-end conversation flow tests - Phase 5 of persistent conversations.

Tests cover:
- Complete conversation lifecycle
- Multi-turn conversations with context
- Memory service integration
- Summarization flow
- Orchestrator integration with conversations
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock
import uuid

from app.db.session import get_db_session
from app.services.conversation_service import ConversationService
from app.services.memory_service import MemoryService
from app.orchestrator import Orchestrator, PipelineContext
from app import config


@pytest.fixture
def enable_feature():
    """Enable persistent conversations feature."""
    original_value = config.settings.USE_PERSISTENT_CONVERSATIONS
    config.settings.USE_PERSISTENT_CONVERSATIONS = True
    yield
    config.settings.USE_PERSISTENT_CONVERSATIONS = original_value


class TestConversationLifecycle:
    """Tests for complete conversation lifecycle."""

    def test_create_add_messages_archive_flow(self, enable_feature):
        """Test full lifecycle: create -> messages -> archive."""
        with get_db_session() as db:
            service = ConversationService(db)

            # Create conversation
            conv = service.create_conversation(
                project_code="MMBL",
                env="prod",
                domain="NPSB"
            )
            assert conv.status == "active"

            # Add multiple messages
            service.add_message(conv.conversation_id, "user", "Show NPSB errors")
            service.add_message(conv.conversation_id, "assistant", "Found 5 NPSB errors...")
            service.add_message(conv.conversation_id, "user", "Show trace for the first one")
            service.add_message(conv.conversation_id, "assistant", "Trace ID abc123...")

            # Verify message count
            messages = service.get_messages(conv.conversation_id)
            assert len(messages) == 4

            # Archive
            service.archive_conversation(conv.conversation_id)
            conv = service.get_conversation(conv.conversation_id)
            assert conv.status == "archived"
            assert not conv.is_active

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_auto_title_generation(self, enable_feature):
        """Test automatic title generation from first message."""
        with get_db_session() as db:
            service = ConversationService(db)

            conv = service.create_conversation()
            assert conv.title is None

            # Add first message
            service.add_message(conv.conversation_id, "user", "Show all NPSB timeout errors from yesterday")

            # Generate title
            title = service.generate_title(conv.conversation_id)

            # Title should be generated from first message
            assert title is not None
            assert len(title) > 0
            assert len(title) <= 100  # Reasonable length

            # Cleanup
            db.delete(conv)
            db.commit()


class TestMultiTurnConversation:
    """Tests for multi-turn conversation with context."""

    def test_context_preserved_across_turns(self, enable_feature):
        """Context from earlier messages is available."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(conversation_service=conv_service)

            conv = conv_service.create_conversation()

            # First turn - user mentions domain
            conv_service.add_message(conv.conversation_id, "user", "Show NPSB errors from yesterday")
            conv_service.add_message(conv.conversation_id, "assistant", "Found 5 NPSB timeout errors")

            # Second turn - user refers to previous context
            conv_service.add_message(conv.conversation_id, "user", "Show trace for the first error")

            # Get context window
            context = memory_service.get_context_window(conv.conversation_id)

            # Should have all messages
            assert len(context) == 3
            assert any("NPSB" in msg["content"] for msg in context)
            assert any("first error" in msg["content"] for msg in context)

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_context_formatted_for_agent(self, enable_feature):
        """Context is properly formatted for agent prompts."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(conversation_service=conv_service)

            conv = conv_service.create_conversation()
            conv_service.add_message(conv.conversation_id, "user", "Analyze NPSB")
            conv_service.add_message(conv.conversation_id, "assistant", "Here are the results")

            context = memory_service.get_context_window(conv.conversation_id)
            formatted = memory_service.format_history_for_prompt(context, "Continue analysis")

            # Should be properly formatted
            assert "Previous Conversation:" in formatted
            assert "NPSB" in formatted
            assert "Continue analysis" in formatted

            # Cleanup
            db.delete(conv)
            db.commit()


class TestMemorySummarization:
    """Tests for memory summarization."""

    def test_summarization_triggered_above_threshold(self, enable_feature):
        """Summarization is triggered when message count exceeds threshold."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(
                conversation_service=conv_service,
                summarization_threshold=5,
                recent_messages_to_keep=3
            )

            conv = conv_service.create_conversation()

            # Add messages below threshold
            for i in range(4):
                conv_service.add_message(conv.conversation_id, "user", f"Message {i}")

            assert not memory_service.should_summarize(conv.conversation_id)

            # Add more to exceed threshold
            for i in range(4, 8):
                conv_service.add_message(conv.conversation_id, "user", f"Message {i}")

            assert memory_service.should_summarize(conv.conversation_id)

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_summary_included_in_context(self, enable_feature):
        """Summary is included in context window when available."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(conversation_service=conv_service)

            conv = conv_service.create_conversation()

            # Set summary directly
            conv_service.update_conversation(
                conv.conversation_id,
                summary="Previously discussed NPSB timeout errors for merchant ABC"
            )

            # Add recent messages
            conv_service.add_message(conv.conversation_id, "user", "Show more details")

            context = memory_service.get_context_window(conv.conversation_id)

            # Summary should be first as system message
            system_msgs = [m for m in context if m["role"] == "system"]
            assert len(system_msgs) > 0
            assert "NPSB" in system_msgs[0]["content"]

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_llm_summarization_called(self, enable_feature):
        """LLM is called for summarization."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(
                conversation_service=conv_service,
                summarization_threshold=3,
                recent_messages_to_keep=2
            )

            conv = conv_service.create_conversation()

            # Add enough messages to trigger summarization
            for i in range(6):
                conv_service.add_message(
                    conv.conversation_id,
                    "user" if i % 2 == 0 else "assistant",
                    f"Message about NPSB error {i}"
                )

            # Mock LLM call
            with patch.object(memory_service, '_call_llm_for_summary') as mock_llm:
                mock_llm.return_value = "Summary: Discussed NPSB errors 0-3"

                summary = memory_service.summarize_old_messages(conv.conversation_id)

                # LLM should be called
                assert mock_llm.called
                assert summary == "Summary: Discussed NPSB errors 0-3"

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_fallback_summary_on_llm_failure(self, enable_feature):
        """Fallback summary is used when LLM fails."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(
                conversation_service=conv_service,
                summarization_threshold=3,
                recent_messages_to_keep=2
            )

            conv = conv_service.create_conversation()

            for i in range(6):
                conv_service.add_message(conv.conversation_id, "user", f"Message {i}")

            # Mock LLM to raise exception
            with patch.object(memory_service, '_call_llm_for_summary') as mock_llm:
                mock_llm.side_effect = Exception("LLM unavailable")

                summary = memory_service.summarize_old_messages(conv.conversation_id)

                # Should have fallback summary
                assert summary is not None
                assert "Message" in summary or "messages" in summary.lower()

            # Cleanup
            db.delete(conv)
            db.commit()


class TestConversationWithExecution:
    """Tests for conversation with pipeline execution."""

    def test_execution_created_for_message(self, enable_feature):
        """Pipeline execution is created when message is added."""
        with get_db_session() as db:
            service = ConversationService(db)

            conv = service.create_conversation()

            # Create execution
            execution = service.create_execution(
                conv.conversation_id,
                prompt="Show NPSB errors"
            )

            assert execution.execution_id is not None
            assert execution.status == "pending"
            assert execution.prompt == "Show NPSB errors"

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_execution_status_updates(self, enable_feature):
        """Execution status is updated during processing."""
        with get_db_session() as db:
            service = ConversationService(db)

            conv = service.create_conversation()
            execution = service.create_execution(conv.conversation_id, "Test query")

            # Update to running
            service.update_execution(execution.execution_id, status="running")
            execution = service.get_execution(execution.execution_id)
            assert execution.status == "running"

            # Update to completed
            service.update_execution(
                execution.execution_id,
                status="completed",
                trace_ids=["abc123", "def456"],
                report_files=["report.md"]
            )
            execution = service.get_execution(execution.execution_id)
            assert execution.status == "completed"
            assert execution.trace_ids == ["abc123", "def456"]

            # Cleanup
            db.delete(conv)
            db.commit()


class TestOrchestratorConversationIntegration:
    """Tests for orchestrator integration with conversations."""

    def test_orchestrator_receives_conversation_context(self, enable_feature):
        """Orchestrator receives conversation history."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(conversation_service=conv_service)

            conv = conv_service.create_conversation()
            conv_service.add_message(conv.conversation_id, "user", "Show NPSB errors")
            conv_service.add_message(conv.conversation_id, "assistant", "Found 5 errors")

            # Get history for orchestrator
            history = memory_service.get_context_window(conv.conversation_id)

            assert len(history) == 2
            assert history[0]["role"] == "user"
            assert "NPSB" in history[0]["content"]

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_pipeline_context_includes_conversation(self, enable_feature):
        """PipelineContext includes conversation fields."""
        context = PipelineContext(
            text="Test query",
            project="MMBL",
            env="prod",
            domain="NPSB",
            conversation_id="test-conv-id",
            execution_id="test-exec-id",
            conversation_history=[
                {"role": "user", "content": "Previous query"}
            ]
        )

        assert context.conversation_id == "test-conv-id"
        assert context.execution_id == "test-exec-id"
        assert len(context.conversation_history) == 1


class TestTokenManagement:
    """Tests for token-aware context management."""

    def test_context_respects_token_limit(self, enable_feature):
        """Context window respects token limits."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(
                conversation_service=conv_service,
                max_context_tokens=200
            )

            conv = conv_service.create_conversation()

            # Add many messages with substantial content
            for i in range(20):
                conv_service.add_message(
                    conv.conversation_id,
                    "user",
                    f"This is message number {i} with some additional content to increase token count"
                )

            context = memory_service.get_context_window(conv.conversation_id)

            # Should have fewer messages than total
            assert len(context) < 20

            # Token estimate should be under limit
            tokens = memory_service.estimate_messages_tokens(context)
            assert tokens <= 200 + 50  # Allow some buffer

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_recent_messages_prioritized(self, enable_feature):
        """Most recent messages are prioritized in context."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(
                conversation_service=conv_service,
                max_context_tokens=100
            )

            conv = conv_service.create_conversation()

            for i in range(10):
                conv_service.add_message(conv.conversation_id, "user", f"Message {i}")

            # Add distinctive recent message
            conv_service.add_message(conv.conversation_id, "user", "MOST_RECENT_MESSAGE")

            context = memory_service.get_context_window(conv.conversation_id)

            # Most recent should be included
            contents = [m["content"] for m in context]
            assert "MOST_RECENT_MESSAGE" in contents

            # Cleanup
            db.delete(conv)
            db.commit()


class TestConversationPersistence:
    """Tests for conversation persistence across sessions."""

    def test_conversation_persists_after_session_close(self, enable_feature):
        """Conversation persists after DB session close."""
        conv_id = None

        # Create conversation in one session
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation(project_code="TEST_PERSIST")
            conv_id = conv.conversation_id
            service.add_message(conv_id, "user", "Test message")

        # Retrieve in new session
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.get_conversation(conv_id)

            assert conv is not None
            assert conv.project_code == "TEST_PERSIST"

            messages = service.get_messages(conv_id)
            assert len(messages) == 1
            assert messages[0].content == "Test message"

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_messages_ordered_chronologically(self, enable_feature):
        """Messages are retrieved in chronological order."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()

            # Add messages with small delays (simulated by order)
            service.add_message(conv.conversation_id, "user", "First")
            service.add_message(conv.conversation_id, "assistant", "Second")
            service.add_message(conv.conversation_id, "user", "Third")

            messages = service.get_messages(conv.conversation_id)

            assert messages[0].content == "First"
            assert messages[1].content == "Second"
            assert messages[2].content == "Third"

            # Cleanup
            db.delete(conv)
            db.commit()
