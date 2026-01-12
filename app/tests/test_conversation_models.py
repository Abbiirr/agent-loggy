# app/tests/test_conversation_models.py
"""Tests for Conversation, Message, and PipelineExecution models.

These tests verify Phase 1 of the persistent conversations implementation:
- Model creation and relationships
- CRUD operations
- Cascade delete behavior
- Serialization methods (to_dict, to_llm_format)
- Helper methods
"""

import pytest
import uuid
from datetime import datetime, timedelta

from app.db.session import get_db_session
from app.models import Conversation, Message, PipelineExecution


class TestConversationModel:
    """Tests for the Conversation model."""

    def test_create_conversation_minimal(self):
        """Test creating a conversation with minimal fields."""
        with get_db_session() as db:
            conv = Conversation(
                conversation_id=str(uuid.uuid4()),
            )
            db.add(conv)
            db.flush()

            assert conv.id is not None
            assert conv.status == "active"
            assert conv.is_active is True
            assert conv.project_code is None
            assert conv.created_at is not None

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_create_conversation_full(self):
        """Test creating a conversation with all fields."""
        conv_id = str(uuid.uuid4())
        with get_db_session() as db:
            conv = Conversation(
                conversation_id=conv_id,
                project_code="MMBL",
                env="prod",
                domain="transactions",
                title="Test Full Conversation",
                summary="This is a test summary",
                summary_token_count=100,
                status="active",
            )
            db.add(conv)
            db.flush()

            assert conv.conversation_id == conv_id
            assert conv.project_code == "MMBL"
            assert conv.env == "prod"
            assert conv.domain == "transactions"
            assert conv.title == "Test Full Conversation"
            assert conv.summary == "This is a test summary"
            assert conv.summary_token_count == 100

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_conversation_to_dict(self):
        """Test Conversation.to_dict() serialization."""
        with get_db_session() as db:
            conv = Conversation(
                conversation_id=str(uuid.uuid4()),
                project_code="NCC",
                title="Dict Test",
            )
            db.add(conv)
            db.flush()

            result = conv.to_dict()

            assert "id" in result
            assert "conversation_id" in result
            assert "project_code" in result
            assert result["project_code"] == "NCC"
            assert result["title"] == "Dict Test"
            assert result["message_count"] == 0
            assert result["has_summary"] is False
            assert "created_at" in result
            assert "updated_at" in result
            # Messages should not be included by default
            assert "messages" not in result

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_conversation_to_dict_with_messages(self):
        """Test Conversation.to_dict(include_messages=True)."""
        with get_db_session() as db:
            conv = Conversation(
                conversation_id=str(uuid.uuid4()),
                title="Messages Dict Test",
            )
            db.add(conv)
            db.flush()

            # Add a message
            msg = Message(
                conversation_id=conv.id,
                role="user",
                content="Test message",
            )
            db.add(msg)
            db.flush()

            result = conv.to_dict(include_messages=True)

            assert "messages" in result
            assert len(result["messages"]) == 1
            assert result["messages"][0]["role"] == "user"
            assert result["message_count"] == 1

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_conversation_get_message_count(self):
        """Test Conversation.get_message_count() method."""
        with get_db_session() as db:
            conv = Conversation(
                conversation_id=str(uuid.uuid4()),
            )
            db.add(conv)
            db.flush()

            assert conv.get_message_count() == 0

            # Add messages
            for i in range(3):
                msg = Message(
                    conversation_id=conv.id,
                    role="user" if i % 2 == 0 else "assistant",
                    content=f"Message {i}",
                )
                db.add(msg)
            db.flush()

            # Refresh to reload relationships
            db.refresh(conv)
            assert conv.get_message_count() == 3

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_conversation_get_last_message(self):
        """Test Conversation.get_last_message() method."""
        with get_db_session() as db:
            conv = Conversation(
                conversation_id=str(uuid.uuid4()),
            )
            db.add(conv)
            db.flush()

            assert conv.get_last_message() is None

            # Add messages
            msg1 = Message(conversation_id=conv.id, role="user", content="First")
            msg2 = Message(conversation_id=conv.id, role="assistant", content="Last")
            db.add(msg1)
            db.add(msg2)
            db.flush()

            # Refresh to reload relationships
            db.refresh(conv)
            last = conv.get_last_message()
            assert last is not None
            assert last.content == "Last"

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_conversation_unique_conversation_id(self):
        """Test that conversation_id must be unique."""
        conv_id = str(uuid.uuid4())
        with get_db_session() as db:
            conv1 = Conversation(conversation_id=conv_id)
            db.add(conv1)
            db.flush()

            conv2 = Conversation(conversation_id=conv_id)
            db.add(conv2)

            with pytest.raises(Exception):  # IntegrityError
                db.flush()

            db.rollback()
            # Cleanup
            conv1 = db.query(Conversation).filter(
                Conversation.conversation_id == conv_id
            ).first()
            if conv1:
                db.delete(conv1)
                db.commit()


class TestMessageModel:
    """Tests for the Message model."""

    def test_create_message(self):
        """Test creating a message."""
        with get_db_session() as db:
            conv = Conversation(conversation_id=str(uuid.uuid4()))
            db.add(conv)
            db.flush()

            msg = Message(
                conversation_id=conv.id,
                role="user",
                content="Hello, world!",
                message_type="prompt",
                token_count=5,
            )
            db.add(msg)
            db.flush()

            assert msg.id is not None
            assert msg.role == "user"
            assert msg.content == "Hello, world!"
            assert msg.message_type == "prompt"
            assert msg.token_count == 5
            assert msg.created_at is not None

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_message_with_metadata(self):
        """Test creating a message with JSONB metadata."""
        with get_db_session() as db:
            conv = Conversation(conversation_id=str(uuid.uuid4()))
            db.add(conv)
            db.flush()

            metadata = {
                "cache_hit": True,
                "step_name": "parameter_extraction",
                "tokens_used": 150,
            }
            msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content="Analysis complete",
                message_metadata=metadata,
            )
            db.add(msg)
            db.flush()

            # Query back and verify
            fetched = db.query(Message).filter(Message.id == msg.id).first()
            assert fetched.message_metadata == metadata
            assert fetched.message_metadata["cache_hit"] is True

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_message_to_dict(self):
        """Test Message.to_dict() serialization."""
        with get_db_session() as db:
            conv = Conversation(conversation_id=str(uuid.uuid4()))
            db.add(conv)
            db.flush()

            msg = Message(
                conversation_id=conv.id,
                role="user",
                content="Test content",
                message_type="prompt",
            )
            db.add(msg)
            db.flush()

            result = msg.to_dict()

            assert result["role"] == "user"
            assert result["content"] == "Test content"
            assert result["message_type"] == "prompt"
            assert "created_at" in result

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_message_to_llm_format(self):
        """Test Message.to_llm_format() for LLM context."""
        with get_db_session() as db:
            conv = Conversation(conversation_id=str(uuid.uuid4()))
            db.add(conv)
            db.flush()

            msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content="Here is my response",
                message_type="analysis",
                token_count=100,
            )
            db.add(msg)
            db.flush()

            result = msg.to_llm_format()

            # Should only have role and content
            assert result == {"role": "assistant", "content": "Here is my response"}
            assert "message_type" not in result
            assert "token_count" not in result

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_message_relationship_to_conversation(self):
        """Test that Message has proper relationship to Conversation."""
        with get_db_session() as db:
            conv = Conversation(
                conversation_id=str(uuid.uuid4()),
                title="Relationship Test",
            )
            db.add(conv)
            db.flush()

            msg = Message(
                conversation_id=conv.id,
                role="user",
                content="Test",
            )
            db.add(msg)
            db.flush()

            # Access conversation through message
            assert msg.conversation is not None
            assert msg.conversation.title == "Relationship Test"

            # Cleanup
            db.delete(conv)
            db.commit()


class TestPipelineExecutionModel:
    """Tests for the PipelineExecution model."""

    def test_create_execution(self):
        """Test creating a pipeline execution."""
        with get_db_session() as db:
            conv = Conversation(conversation_id=str(uuid.uuid4()))
            db.add(conv)
            db.flush()

            execution = PipelineExecution(
                conversation_id=conv.id,
                execution_id=str(uuid.uuid4()),
                prompt="Find failed transactions",
                status="pending",
            )
            db.add(execution)
            db.flush()

            assert execution.id is not None
            assert execution.status == "pending"
            assert execution.started_at is not None
            assert execution.completed_at is None

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_execution_with_results(self):
        """Test execution with JSONB result fields."""
        with get_db_session() as db:
            conv = Conversation(conversation_id=str(uuid.uuid4()))
            db.add(conv)
            db.flush()

            execution = PipelineExecution(
                conversation_id=conv.id,
                execution_id=str(uuid.uuid4()),
                prompt="Find errors",
                status="complete",
                extracted_params={"time_frame": "yesterday", "query_keys": ["error"]},
                plan={"steps": ["extract", "search", "analyze"]},
                trace_ids=["trace-001", "trace-002", "trace-003"],
                report_files=["report_001.txt", "report_002.txt"],
                cache_diagnostics={"hits": 5, "misses": 2},
                completed_at=datetime.utcnow(),
            )
            db.add(execution)
            db.flush()

            # Query back
            fetched = db.query(PipelineExecution).filter(
                PipelineExecution.id == execution.id
            ).first()

            assert fetched.extracted_params["time_frame"] == "yesterday"
            assert len(fetched.trace_ids) == 3
            assert "report_001.txt" in fetched.report_files

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_execution_is_complete(self):
        """Test PipelineExecution.is_complete() method."""
        with get_db_session() as db:
            conv = Conversation(conversation_id=str(uuid.uuid4()))
            db.add(conv)
            db.flush()

            exec1 = PipelineExecution(
                conversation_id=conv.id,
                execution_id=str(uuid.uuid4()),
                prompt="Test 1",
                status="pending",
            )
            exec2 = PipelineExecution(
                conversation_id=conv.id,
                execution_id=str(uuid.uuid4()),
                prompt="Test 2",
                status="complete",
            )
            exec3 = PipelineExecution(
                conversation_id=conv.id,
                execution_id=str(uuid.uuid4()),
                prompt="Test 3",
                status="error",
            )
            db.add_all([exec1, exec2, exec3])
            db.flush()

            assert exec1.is_complete() is False
            assert exec2.is_complete() is True
            assert exec3.is_complete() is True

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_execution_is_streaming(self):
        """Test PipelineExecution.is_streaming() method."""
        with get_db_session() as db:
            conv = Conversation(conversation_id=str(uuid.uuid4()))
            db.add(conv)
            db.flush()

            exec1 = PipelineExecution(
                conversation_id=conv.id,
                execution_id=str(uuid.uuid4()),
                prompt="Test",
                status="streaming",
            )
            exec2 = PipelineExecution(
                conversation_id=conv.id,
                execution_id=str(uuid.uuid4()),
                prompt="Test",
                status="complete",
            )
            db.add_all([exec1, exec2])
            db.flush()

            assert exec1.is_streaming() is True
            assert exec2.is_streaming() is False

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_execution_duration_seconds(self):
        """Test PipelineExecution.duration_seconds() method."""
        with get_db_session() as db:
            conv = Conversation(conversation_id=str(uuid.uuid4()))
            db.add(conv)
            db.flush()

            start_time = datetime.utcnow()
            end_time = start_time + timedelta(seconds=45)

            execution = PipelineExecution(
                conversation_id=conv.id,
                execution_id=str(uuid.uuid4()),
                prompt="Test",
                status="complete",
                started_at=start_time,
                completed_at=end_time,
            )
            db.add(execution)
            db.flush()

            duration = execution.duration_seconds()
            assert duration is not None
            assert abs(duration - 45.0) < 0.1

            # Test incomplete execution
            exec_incomplete = PipelineExecution(
                conversation_id=conv.id,
                execution_id=str(uuid.uuid4()),
                prompt="Test",
                status="streaming",
            )
            db.add(exec_incomplete)
            db.flush()

            assert exec_incomplete.duration_seconds() is None

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_execution_to_dict(self):
        """Test PipelineExecution.to_dict() serialization."""
        with get_db_session() as db:
            conv = Conversation(conversation_id=str(uuid.uuid4()))
            db.add(conv)
            db.flush()

            execution = PipelineExecution(
                conversation_id=conv.id,
                execution_id=str(uuid.uuid4()),
                prompt="Test prompt",
                status="complete",
                trace_ids=["t1", "t2"],
            )
            db.add(execution)
            db.flush()

            result = execution.to_dict()

            assert "execution_id" in result
            assert result["status"] == "complete"
            assert result["prompt"] == "Test prompt"
            assert result["trace_ids"] == ["t1", "t2"]
            assert "duration_seconds" in result

            # Cleanup
            db.delete(conv)
            db.commit()


class TestCascadeDelete:
    """Tests for cascade delete behavior."""

    def test_cascade_delete_messages(self):
        """Test that deleting conversation cascades to messages."""
        with get_db_session() as db:
            conv = Conversation(conversation_id=str(uuid.uuid4()))
            db.add(conv)
            db.flush()
            conv_id = conv.id

            # Add messages
            for i in range(5):
                msg = Message(
                    conversation_id=conv.id,
                    role="user",
                    content=f"Message {i}",
                )
                db.add(msg)
            db.flush()

            # Verify messages exist
            msg_count = db.query(Message).filter(
                Message.conversation_id == conv_id
            ).count()
            assert msg_count == 5

            # Delete conversation
            db.delete(conv)
            db.commit()

            # Verify messages are deleted
            msg_count = db.query(Message).filter(
                Message.conversation_id == conv_id
            ).count()
            assert msg_count == 0

    def test_cascade_delete_executions(self):
        """Test that deleting conversation cascades to executions."""
        with get_db_session() as db:
            conv = Conversation(conversation_id=str(uuid.uuid4()))
            db.add(conv)
            db.flush()
            conv_id = conv.id

            # Add executions
            for i in range(3):
                execution = PipelineExecution(
                    conversation_id=conv.id,
                    execution_id=str(uuid.uuid4()),
                    prompt=f"Prompt {i}",
                )
                db.add(execution)
            db.flush()

            # Verify executions exist
            exec_count = db.query(PipelineExecution).filter(
                PipelineExecution.conversation_id == conv_id
            ).count()
            assert exec_count == 3

            # Delete conversation
            db.delete(conv)
            db.commit()

            # Verify executions are deleted
            exec_count = db.query(PipelineExecution).filter(
                PipelineExecution.conversation_id == conv_id
            ).count()
            assert exec_count == 0

    def test_cascade_delete_all(self):
        """Test complete cascade delete with messages and executions."""
        with get_db_session() as db:
            conv = Conversation(
                conversation_id=str(uuid.uuid4()),
                title="Cascade Test",
            )
            db.add(conv)
            db.flush()
            conv_id = conv.id

            # Add messages
            msg1 = Message(conversation_id=conv.id, role="user", content="Q1")
            msg2 = Message(conversation_id=conv.id, role="assistant", content="A1")
            db.add_all([msg1, msg2])

            # Add execution
            execution = PipelineExecution(
                conversation_id=conv.id,
                execution_id=str(uuid.uuid4()),
                prompt="Q1",
            )
            db.add(execution)
            db.flush()

            # Delete conversation
            db.delete(conv)
            db.commit()

            # Verify all related records are deleted
            assert db.query(Conversation).filter(
                Conversation.id == conv_id
            ).first() is None
            assert db.query(Message).filter(
                Message.conversation_id == conv_id
            ).count() == 0
            assert db.query(PipelineExecution).filter(
                PipelineExecution.conversation_id == conv_id
            ).count() == 0


class TestRelationshipOrdering:
    """Tests for relationship ordering."""

    def test_messages_ordered_by_created_at(self):
        """Test that messages are ordered by created_at."""
        with get_db_session() as db:
            conv = Conversation(conversation_id=str(uuid.uuid4()))
            db.add(conv)
            db.flush()

            # Add messages (order matters for test)
            msg1 = Message(conversation_id=conv.id, role="user", content="First")
            db.add(msg1)
            db.flush()

            msg2 = Message(conversation_id=conv.id, role="assistant", content="Second")
            db.add(msg2)
            db.flush()

            msg3 = Message(conversation_id=conv.id, role="user", content="Third")
            db.add(msg3)
            db.flush()

            # Refresh to get ordered relationship
            db.refresh(conv)

            # Check order
            assert len(conv.messages) == 3
            assert conv.messages[0].content == "First"
            assert conv.messages[1].content == "Second"
            assert conv.messages[2].content == "Third"

            # Cleanup
            db.delete(conv)
            db.commit()

    def test_executions_ordered_by_started_at_desc(self):
        """Test that executions are ordered by started_at descending."""
        with get_db_session() as db:
            conv = Conversation(conversation_id=str(uuid.uuid4()))
            db.add(conv)
            db.flush()

            # Add executions with different start times
            exec1 = PipelineExecution(
                conversation_id=conv.id,
                execution_id=str(uuid.uuid4()),
                prompt="First",
                started_at=datetime.utcnow() - timedelta(hours=2),
            )
            exec2 = PipelineExecution(
                conversation_id=conv.id,
                execution_id=str(uuid.uuid4()),
                prompt="Second",
                started_at=datetime.utcnow() - timedelta(hours=1),
            )
            exec3 = PipelineExecution(
                conversation_id=conv.id,
                execution_id=str(uuid.uuid4()),
                prompt="Third",
                started_at=datetime.utcnow(),
            )
            db.add_all([exec1, exec2, exec3])
            db.flush()

            # Refresh to get ordered relationship
            db.refresh(conv)

            # Check order (descending - newest first)
            assert len(conv.executions) == 3
            assert conv.executions[0].prompt == "Third"
            assert conv.executions[1].prompt == "Second"
            assert conv.executions[2].prompt == "First"

            # Cleanup
            db.delete(conv)
            db.commit()
