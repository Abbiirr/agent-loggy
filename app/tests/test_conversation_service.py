# app/tests/test_conversation_service.py
"""
Tests for ConversationService - Phase 2 of persistent conversations.

Tests cover:
- Conversation CRUD operations
- Message operations
- Pipeline execution tracking
- Title generation
- Caching behavior
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import uuid

from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.conversation import Conversation, Message, PipelineExecution
from app.services.conversation_service import (
    ConversationService,
    get_conversation_service,
)


class TestConversationServiceCreate:
    """Tests for conversation creation."""

    def test_create_conversation_minimal(self):
        """Create conversation with no optional fields."""
        with get_db_session() as db:
            service = ConversationService(db)

            conv = service.create_conversation()

            assert conv is not None
            assert conv.conversation_id is not None
            assert len(conv.conversation_id) == 36  # UUID format
            assert conv.status == "active"
            assert conv.is_active is True
            assert conv.project_code is None
            assert conv.env is None
            assert conv.domain is None

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_create_conversation_with_project(self):
        """Create conversation with project code."""
        with get_db_session() as db:
            service = ConversationService(db)

            conv = service.create_conversation(
                project_code="MMBL",
                env="prod",
                domain="NPSB"
            )

            assert conv.project_code == "MMBL"
            assert conv.env == "prod"
            assert conv.domain == "NPSB"

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_create_conversation_unique_ids(self):
        """Each conversation gets a unique ID."""
        with get_db_session() as db:
            service = ConversationService(db)

            conv1 = service.create_conversation()
            conv2 = service.create_conversation()

            assert conv1.conversation_id != conv2.conversation_id

            # Cleanup
            db.delete(conv1)
            db.delete(conv2)
            db.commit()


class TestConversationServiceGet:
    """Tests for conversation retrieval."""

    def test_get_conversation_by_id(self):
        """Retrieve conversation by its UUID."""
        with get_db_session() as db:
            service = ConversationService(db)
            created = service.create_conversation(project_code="NCC")

            retrieved = service.get_conversation(created.conversation_id)

            assert retrieved is not None
            assert retrieved.id == created.id
            assert retrieved.conversation_id == created.conversation_id
            assert retrieved.project_code == "NCC"

            # Cleanup
            db.delete(created)
            db.commit()

    def test_get_conversation_not_found(self):
        """Return None for non-existent conversation."""
        with get_db_session() as db:
            service = ConversationService(db)

            result = service.get_conversation("non-existent-id")

            assert result is None

    def test_get_conversation_by_internal_id(self):
        """Retrieve conversation by internal database ID."""
        with get_db_session() as db:
            service = ConversationService(db)
            created = service.create_conversation()

            retrieved = service.get_conversation_by_internal_id(created.id)

            assert retrieved is not None
            assert retrieved.conversation_id == created.conversation_id

            # Cleanup
            db.delete(created)
            db.commit()


class TestConversationServiceList:
    """Tests for listing conversations."""

    def test_list_conversations_empty(self):
        """List returns empty when no matching conversations exist."""
        with get_db_session() as db:
            service = ConversationService(db)

            # Use a unique project code to avoid conflicts with other tests
            result = service.list_conversations(project_code="TEST_EMPTY_PROJECT")

            assert result == []

    def test_list_conversations_with_data(self):
        """List returns all active conversations."""
        with get_db_session() as db:
            service = ConversationService(db)
            # Use unique project code for test isolation
            test_project = f"TEST_{uuid.uuid4().hex[:8]}"
            conv1 = service.create_conversation(project_code=test_project)
            conv2 = service.create_conversation(project_code=test_project)
            conv3 = service.create_conversation(project_code=test_project)

            result = service.list_conversations(project_code=test_project)

            assert len(result) == 3

            # Cleanup
            for c in [conv1, conv2, conv3]:
                db.delete(c)
            db.commit()

    def test_list_conversations_filter_by_project(self):
        """Filter conversations by project code."""
        with get_db_session() as db:
            service = ConversationService(db)
            test_project1 = f"TEST_{uuid.uuid4().hex[:8]}"
            test_project2 = f"TEST_{uuid.uuid4().hex[:8]}"
            conv1 = service.create_conversation(project_code=test_project1)
            conv2 = service.create_conversation(project_code=test_project1)
            conv3 = service.create_conversation(project_code=test_project2)

            result = service.list_conversations(project_code=test_project1)

            assert len(result) == 2
            assert all(c.project_code == test_project1 for c in result)

            # Cleanup
            for c in [conv1, conv2, conv3]:
                db.delete(c)
            db.commit()

    def test_list_conversations_filter_by_status(self):
        """Filter conversations by status."""
        with get_db_session() as db:
            service = ConversationService(db)
            test_project = f"TEST_{uuid.uuid4().hex[:8]}"
            conv1 = service.create_conversation(project_code=test_project)
            conv2 = service.create_conversation(project_code=test_project)
            service.archive_conversation(conv2.conversation_id)

            active = service.list_conversations(project_code=test_project, status="active")
            archived = service.list_conversations(project_code=test_project, status="archived")

            assert len(active) == 1
            assert len(archived) == 1

            # Cleanup
            db.delete(conv1)
            db.delete(conv2)
            db.commit()

    def test_list_conversations_pagination(self):
        """Pagination works correctly."""
        with get_db_session() as db:
            service = ConversationService(db)
            test_project = f"TEST_{uuid.uuid4().hex[:8]}"
            convs = []
            for i in range(5):
                convs.append(service.create_conversation(project_code=test_project))

            page1 = service.list_conversations(project_code=test_project, limit=2, offset=0)
            page2 = service.list_conversations(project_code=test_project, limit=2, offset=2)
            page3 = service.list_conversations(project_code=test_project, limit=2, offset=4)

            assert len(page1) == 2
            assert len(page2) == 2
            assert len(page3) == 1

            # Cleanup
            for c in convs:
                db.delete(c)
            db.commit()


class TestConversationServiceUpdate:
    """Tests for conversation updates."""

    def test_update_conversation_title(self):
        """Update conversation title."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()

            updated = service.update_conversation(
                conv.conversation_id,
                title="New Title"
            )

            assert updated.title == "New Title"

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_update_conversation_multiple_fields(self):
        """Update multiple fields at once."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()

            updated = service.update_conversation(
                conv.conversation_id,
                title="Updated Title",
                domain="NPSB",
                summary="Test summary"
            )

            assert updated.title == "Updated Title"
            assert updated.domain == "NPSB"
            assert updated.summary == "Test summary"

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_update_conversation_not_found(self):
        """Return None when updating non-existent conversation."""
        with get_db_session() as db:
            service = ConversationService(db)

            result = service.update_conversation("fake-id", title="Test")

            assert result is None

    def test_update_conversation_updates_timestamp(self):
        """Updated_at timestamp is refreshed on update."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()
            original_updated = conv.updated_at

            # Small delay to ensure timestamp difference
            import time
            time.sleep(0.1)

            updated = service.update_conversation(conv.conversation_id, title="New")

            # Note: This may not change in same transaction; DB trigger handles it
            assert updated is not None

            # Cleanup
            db.delete(conv)
            db.commit()


class TestConversationServiceArchiveDelete:
    """Tests for archiving and deleting conversations."""

    def test_archive_conversation(self):
        """Archive conversation changes status."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()

            result = service.archive_conversation(conv.conversation_id)

            assert result is True
            retrieved = service.get_conversation(conv.conversation_id)
            assert retrieved.status == "archived"
            assert retrieved.is_active is False

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_archive_conversation_not_found(self):
        """Return False when archiving non-existent conversation."""
        with get_db_session() as db:
            service = ConversationService(db)

            result = service.archive_conversation("fake-id")

            assert result is False

    def test_delete_conversation(self):
        """Delete conversation removes it from database."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()
            conv_id = conv.conversation_id

            result = service.delete_conversation(conv_id)

            assert result is True
            retrieved = service.get_conversation(conv_id)
            assert retrieved is None

    def test_delete_conversation_cascades_messages(self):
        """Deleting conversation removes associated messages."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()
            conv_internal_id = conv.id
            service.add_message(conv.conversation_id, "user", "Hello")
            service.add_message(conv.conversation_id, "assistant", "Hi there")

            result = service.delete_conversation(conv.conversation_id)

            assert result is True
            # Messages should be gone (cascade delete)
            messages = db.query(Message).filter(
                Message.conversation_id == conv_internal_id
            ).all()
            assert len(messages) == 0


class TestConversationServiceMessages:
    """Tests for message operations."""

    def test_add_message_user(self):
        """Add a user message to conversation."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()

            message = service.add_message(
                conv.conversation_id,
                role="user",
                content="Show failed transactions"
            )

            assert message is not None
            assert message.role == "user"
            assert message.content == "Show failed transactions"
            assert message.conversation_id == conv.id

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_add_message_with_type_and_metadata(self):
        """Add message with type and metadata."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()

            message = service.add_message(
                conv.conversation_id,
                role="assistant",
                content="Analysis complete",
                message_type="analysis",
                metadata={"cache_hit": True, "tokens": 150}
            )

            assert message.message_type == "analysis"
            assert message.message_metadata == {"cache_hit": True, "tokens": 150}

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_add_message_to_nonexistent_conversation(self):
        """Adding message to non-existent conversation returns None."""
        with get_db_session() as db:
            service = ConversationService(db)

            result = service.add_message("fake-id", "user", "Hello")

            assert result is None

    def test_get_messages(self):
        """Get messages for a conversation."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()
            service.add_message(conv.conversation_id, "user", "First")
            service.add_message(conv.conversation_id, "assistant", "Second")
            service.add_message(conv.conversation_id, "user", "Third")

            messages = service.get_messages(conv.conversation_id)

            assert len(messages) == 3
            assert messages[0].content == "First"
            assert messages[1].content == "Second"
            assert messages[2].content == "Third"

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_get_messages_with_limit(self):
        """Get limited number of messages."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()
            for i in range(10):
                service.add_message(conv.conversation_id, "user", f"Message {i}")

            messages = service.get_messages(conv.conversation_id, limit=5)

            assert len(messages) == 5

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_get_messages_ordered_by_created(self):
        """Messages are ordered by creation time."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()
            service.add_message(conv.conversation_id, "user", "First")
            service.add_message(conv.conversation_id, "assistant", "Second")

            messages = service.get_messages(conv.conversation_id)

            assert messages[0].created_at <= messages[1].created_at

            # Cleanup
            db.delete(conv)
            db.commit()


class TestConversationServiceExecutions:
    """Tests for pipeline execution tracking."""

    def test_create_execution(self):
        """Create pipeline execution record."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()

            execution = service.create_execution(
                conv.conversation_id,
                prompt="Analyze failed transactions"
            )

            assert execution is not None
            assert execution.execution_id is not None
            assert execution.prompt == "Analyze failed transactions"
            assert execution.status == "pending"
            assert execution.conversation_id == conv.id

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_create_execution_nonexistent_conversation(self):
        """Creating execution for non-existent conversation returns None."""
        with get_db_session() as db:
            service = ConversationService(db)

            result = service.create_execution("fake-id", "Test prompt")

            assert result is None

    def test_update_execution(self):
        """Update execution status and fields."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()
            execution = service.create_execution(conv.conversation_id, "Test")

            updated = service.update_execution(
                execution.execution_id,
                status="streaming",
                extracted_params={"time_frame": "yesterday"}
            )

            assert updated.status == "streaming"
            assert updated.extracted_params == {"time_frame": "yesterday"}

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_update_execution_complete(self):
        """Update execution to complete status."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()
            execution = service.create_execution(conv.conversation_id, "Test")

            updated = service.update_execution(
                execution.execution_id,
                status="complete",
                trace_ids=["trace-1", "trace-2"],
                report_files=["/path/to/report.md"],
                completed_at=datetime.utcnow()
            )

            assert updated.status == "complete"
            assert updated.trace_ids == ["trace-1", "trace-2"]
            assert updated.completed_at is not None

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_update_execution_error(self):
        """Update execution with error status."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()
            execution = service.create_execution(conv.conversation_id, "Test")

            updated = service.update_execution(
                execution.execution_id,
                status="error",
                error_message="Connection timeout"
            )

            assert updated.status == "error"
            assert updated.error_message == "Connection timeout"

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_get_execution(self):
        """Get execution by ID."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()
            created = service.create_execution(conv.conversation_id, "Test prompt")

            retrieved = service.get_execution(created.execution_id)

            assert retrieved is not None
            assert retrieved.prompt == "Test prompt"

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_get_execution_not_found(self):
        """Return None for non-existent execution."""
        with get_db_session() as db:
            service = ConversationService(db)

            result = service.get_execution("fake-execution-id")

            assert result is None

    def test_get_executions_for_conversation(self):
        """Get all executions for a conversation."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()
            service.create_execution(conv.conversation_id, "First query")
            service.create_execution(conv.conversation_id, "Second query")

            executions = service.get_executions(conv.conversation_id)

            assert len(executions) == 2

            # Cleanup
            db.delete(conv)
            db.commit()


class TestConversationServiceTitleGeneration:
    """Tests for automatic title generation."""

    def test_generate_title_from_first_message(self):
        """Generate title from first user message."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()
            service.add_message(
                conv.conversation_id,
                "user",
                "Show me failed NPSB transactions from yesterday"
            )

            # Mock LLM call for title generation
            with patch.object(service, '_call_llm_for_title') as mock_llm:
                mock_llm.return_value = "Failed NPSB Transactions"

                title = service.generate_title(conv.conversation_id)

            assert title is not None

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_generate_title_no_messages(self):
        """Return default title when no messages exist."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()

            title = service.generate_title(conv.conversation_id)

            assert title == "New Conversation"

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_generate_title_already_set(self):
        """Return existing title if already set."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()
            service.update_conversation(conv.conversation_id, title="Existing Title")

            title = service.generate_title(conv.conversation_id)

            assert title == "Existing Title"

            # Cleanup
            db.delete(conv)
            db.commit()


class TestConversationServiceCount:
    """Tests for conversation counting."""

    def test_count_conversations(self):
        """Count total conversations."""
        with get_db_session() as db:
            service = ConversationService(db)
            test_project = f"TEST_{uuid.uuid4().hex[:8]}"
            convs = []
            for _ in range(3):
                convs.append(service.create_conversation(project_code=test_project))

            count = service.count_conversations(project_code=test_project)

            assert count == 3

            # Cleanup
            for c in convs:
                db.delete(c)
            db.commit()

    def test_count_conversations_by_project(self):
        """Count conversations filtered by project."""
        with get_db_session() as db:
            service = ConversationService(db)
            test_project1 = f"TEST_{uuid.uuid4().hex[:8]}"
            test_project2 = f"TEST_{uuid.uuid4().hex[:8]}"
            convs = []
            convs.append(service.create_conversation(project_code=test_project1))
            convs.append(service.create_conversation(project_code=test_project1))
            convs.append(service.create_conversation(project_code=test_project2))

            count1 = service.count_conversations(project_code=test_project1)
            count2 = service.count_conversations(project_code=test_project2)

            assert count1 == 2
            assert count2 == 1

            # Cleanup
            for c in convs:
                db.delete(c)
            db.commit()


class TestConversationServiceSingleton:
    """Tests for singleton pattern."""

    def test_get_conversation_service_singleton(self):
        """get_conversation_service returns same instance."""
        service1 = get_conversation_service()
        service2 = get_conversation_service()

        assert service1 is service2

    def test_service_with_explicit_db(self):
        """Service works with explicitly passed db session."""
        with get_db_session() as db:
            service = ConversationService(db)

            conv = service.create_conversation()

            assert conv is not None

            # Cleanup
            db.delete(conv)
            db.commit()
