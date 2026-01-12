# app/tests/test_conversation_streaming.py
"""
Tests for conversation streaming integration - Phase 6.

Tests cover:
- SSE streaming endpoint validation
- Configuration settings
- Feature flag behavior

Note: Full SSE streaming tests are limited due to TestClient's limitations
with async generators. Integration tests should use actual HTTP client.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import json

from app.main import app
from app.db.session import get_db_session
from app.services.conversation_service import ConversationService
from app.services.memory_service import MemoryService
from app import config


@pytest.fixture
def enable_feature():
    """Enable persistent conversations feature."""
    original_value = config.settings.USE_PERSISTENT_CONVERSATIONS
    config.settings.USE_PERSISTENT_CONVERSATIONS = True
    yield
    config.settings.USE_PERSISTENT_CONVERSATIONS = original_value


@pytest.fixture
def client(enable_feature):
    """Create test client with feature enabled."""
    return TestClient(app)


class TestStreamingEndpointValidation:
    """Tests for streaming endpoint validation."""

    def test_stream_not_found_conversation(self, client):
        """Stream returns 404 for non-existent conversation."""
        response = client.get("/api/conversations/fake-conv/stream/fake-exec")
        assert response.status_code == 404

    def test_stream_not_found_execution(self, client, enable_feature):
        """Stream returns 404 for non-existent execution."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()

            try:
                response = client.get(
                    f"/api/conversations/{conv.conversation_id}/stream/fake-exec"
                )
                assert response.status_code == 404
            finally:
                service.delete_conversation(conv.conversation_id)

    def test_stream_already_completed_execution(self, client, enable_feature):
        """Stream returns 400 for already completed execution."""
        with get_db_session() as db:
            service = ConversationService(db)

            conv = service.create_conversation()
            service.add_message(conv.conversation_id, "user", "Test")
            execution = service.create_execution(conv.conversation_id, "Test")

            # Mark as completed
            service.update_execution(execution.execution_id, status="completed")

            try:
                response = client.get(
                    f"/api/conversations/{conv.conversation_id}/stream/{execution.execution_id}"
                )
                assert response.status_code == 400
                assert "already" in response.json()["detail"].lower()
            finally:
                service.delete_conversation(conv.conversation_id)

    def test_stream_already_failed_execution(self, client, enable_feature):
        """Stream returns 400 for already failed execution."""
        with get_db_session() as db:
            service = ConversationService(db)

            conv = service.create_conversation()
            service.add_message(conv.conversation_id, "user", "Test")
            execution = service.create_execution(conv.conversation_id, "Test")

            # Mark as failed
            service.update_execution(execution.execution_id, status="failed")

            try:
                response = client.get(
                    f"/api/conversations/{conv.conversation_id}/stream/{execution.execution_id}"
                )
                assert response.status_code == 400
            finally:
                service.delete_conversation(conv.conversation_id)


class TestMessageFlow:
    """Tests for message creation flow."""

    def test_add_message_creates_execution(self, client, enable_feature):
        """Adding message creates pending execution."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation(project_code="MMBL")

            try:
                response = client.post(
                    f"/api/conversations/{conv.conversation_id}/messages",
                    json={"content": "Show NPSB errors"}
                )

                assert response.status_code == 200
                data = response.json()
                assert "execution_id" in data
                assert "stream_url" in data
                assert conv.conversation_id in data["stream_url"]
                assert data["execution_id"] in data["stream_url"]

                # Verify execution was created
                execution = service.get_execution(data["execution_id"])
                assert execution is not None
                assert execution.status == "pending"
                assert execution.prompt == "Show NPSB errors"

            finally:
                service.delete_conversation(conv.conversation_id)

    def test_add_message_stores_user_message(self, client, enable_feature):
        """Adding message stores user message in DB."""
        with get_db_session() as db:
            service = ConversationService(db)
            conv = service.create_conversation()

            try:
                client.post(
                    f"/api/conversations/{conv.conversation_id}/messages",
                    json={"content": "Test user message"}
                )

                messages = service.get_messages(conv.conversation_id)
                assert len(messages) == 1
                assert messages[0].role == "user"
                assert messages[0].content == "Test user message"
                assert messages[0].message_type == "prompt"

            finally:
                service.delete_conversation(conv.conversation_id)


class TestConfigurationSettings:
    """Tests for conversation configuration settings."""

    def test_memory_service_uses_config_defaults(self, enable_feature):
        """MemoryService uses configuration defaults."""
        memory_service = MemoryService()

        assert memory_service.max_context_tokens == config.settings.CONVERSATION_CONTEXT_TOKENS
        assert memory_service.summarization_threshold == config.settings.CONVERSATION_SUMMARIZATION_THRESHOLD
        assert memory_service.recent_messages_to_keep == config.settings.CONVERSATION_RECENT_MESSAGES

    def test_memory_service_allows_override(self, enable_feature):
        """MemoryService allows parameter override."""
        memory_service = MemoryService(
            max_context_tokens=1000,
            summarization_threshold=5,
            recent_messages_to_keep=3
        )

        assert memory_service.max_context_tokens == 1000
        assert memory_service.summarization_threshold == 5
        assert memory_service.recent_messages_to_keep == 3

    def test_config_values_exist(self):
        """All configuration values are defined."""
        assert hasattr(config.settings, 'CONVERSATION_MAX_MESSAGES')
        assert hasattr(config.settings, 'CONVERSATION_SUMMARIZATION_THRESHOLD')
        assert hasattr(config.settings, 'CONVERSATION_CONTEXT_TOKENS')
        assert hasattr(config.settings, 'CONVERSATION_RECENT_MESSAGES')
        assert hasattr(config.settings, 'CONVERSATION_TITLE_AUTO_GENERATE')

    def test_config_default_values(self):
        """Configuration has reasonable defaults."""
        assert config.settings.CONVERSATION_MAX_MESSAGES > 0
        assert config.settings.CONVERSATION_SUMMARIZATION_THRESHOLD > 0
        assert config.settings.CONVERSATION_CONTEXT_TOKENS > 0
        assert config.settings.CONVERSATION_RECENT_MESSAGES > 0


class TestFeatureFlagStreaming:
    """Tests for feature flag on streaming endpoint."""

    def test_streaming_disabled_when_feature_off(self):
        """Streaming endpoint returns 501 when feature disabled."""
        original_value = config.settings.USE_PERSISTENT_CONVERSATIONS
        config.settings.USE_PERSISTENT_CONVERSATIONS = False

        try:
            client = TestClient(app)
            response = client.get("/api/conversations/test/stream/test")
            assert response.status_code == 501
        finally:
            config.settings.USE_PERSISTENT_CONVERSATIONS = original_value

    def test_add_message_disabled_when_feature_off(self):
        """Add message returns 501 when feature disabled."""
        original_value = config.settings.USE_PERSISTENT_CONVERSATIONS
        config.settings.USE_PERSISTENT_CONVERSATIONS = False

        try:
            client = TestClient(app)
            response = client.post(
                "/api/conversations/test/messages",
                json={"content": "Test"}
            )
            assert response.status_code == 501
        finally:
            config.settings.USE_PERSISTENT_CONVERSATIONS = original_value


class TestConversationContextIntegration:
    """Tests for conversation context handling (without full streaming)."""

    def test_memory_service_gets_context_for_conversation(self, enable_feature):
        """MemoryService can retrieve context for conversation."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(conversation_service=conv_service)

            conv = conv_service.create_conversation()

            try:
                # Add some messages
                conv_service.add_message(conv.conversation_id, "user", "First question")
                conv_service.add_message(conv.conversation_id, "assistant", "First answer")
                conv_service.add_message(conv.conversation_id, "user", "Second question")

                # Get context window
                context = memory_service.get_context_window(conv.conversation_id)

                assert len(context) == 3
                assert context[0]["role"] == "user"
                assert context[0]["content"] == "First question"
                assert context[2]["content"] == "Second question"

            finally:
                conv_service.delete_conversation(conv.conversation_id)

    def test_context_includes_summary_when_available(self, enable_feature):
        """Context window includes summary when conversation has one."""
        with get_db_session() as db:
            conv_service = ConversationService(db)
            memory_service = MemoryService(conversation_service=conv_service)

            conv = conv_service.create_conversation()

            try:
                # Set summary
                conv_service.update_conversation(
                    conv.conversation_id,
                    summary="Previous discussion about NPSB errors"
                )

                # Add recent message
                conv_service.add_message(conv.conversation_id, "user", "Continue analysis")

                context = memory_service.get_context_window(conv.conversation_id)

                # Should have summary as system message
                system_messages = [m for m in context if m["role"] == "system"]
                assert len(system_messages) == 1
                assert "NPSB" in system_messages[0]["content"]

            finally:
                conv_service.delete_conversation(conv.conversation_id)

    def test_execution_tracks_conversation(self, enable_feature):
        """Execution is properly linked to conversation."""
        with get_db_session() as db:
            service = ConversationService(db)

            conv = service.create_conversation(project_code="MMBL")
            execution = service.create_execution(conv.conversation_id, "Test prompt")

            try:
                assert execution.conversation_id == conv.id
                assert execution.prompt == "Test prompt"
                assert execution.status == "pending"

                # Get executions for conversation
                executions = service.get_executions(conv.conversation_id)
                assert len(executions) == 1
                assert executions[0].execution_id == execution.execution_id

            finally:
                service.delete_conversation(conv.conversation_id)
