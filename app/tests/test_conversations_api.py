# app/tests/test_conversations_api.py
"""
Tests for Conversations API - Phase 4 of persistent conversations.

Tests cover:
- Conversation CRUD endpoints
- Message endpoints
- Pagination and filtering
- Error handling
- Feature flag functionality
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import uuid

from app.main import app
from app.db.session import get_db_session
from app.services.conversation_service import ConversationService
from app import config


@pytest.fixture
def enable_persistent_conversations():
    """Enable the persistent conversations feature flag for tests."""
    original_value = config.settings.USE_PERSISTENT_CONVERSATIONS
    config.settings.USE_PERSISTENT_CONVERSATIONS = True
    yield
    config.settings.USE_PERSISTENT_CONVERSATIONS = original_value


@pytest.fixture
def client(enable_persistent_conversations):
    """Create test client with feature flag enabled."""
    return TestClient(app)


@pytest.fixture
def cleanup_conversation():
    """Fixture to cleanup conversations after tests."""
    created_ids = []

    def track(conversation_id):
        created_ids.append(conversation_id)

    yield track

    # Cleanup after test
    with get_db_session() as db:
        service = ConversationService(db)
        for conv_id in created_ids:
            try:
                service.delete_conversation(conv_id)
            except Exception:
                pass


class TestCreateConversation:
    """Tests for POST /api/conversations."""

    def test_create_conversation_minimal(self, client, cleanup_conversation):
        """Create conversation with no optional fields."""
        response = client.post("/api/conversations", json={})

        assert response.status_code == 201
        data = response.json()
        assert "conversation_id" in data
        assert data["status"] == "active"
        cleanup_conversation(data["conversation_id"])

    def test_create_conversation_with_project(self, client, cleanup_conversation):
        """Create conversation with project details."""
        response = client.post("/api/conversations", json={
            "project": "MMBL",
            "env": "prod",
            "domain": "NPSB"
        })

        assert response.status_code == 201
        data = response.json()
        assert data["project_code"] == "MMBL"
        assert data["env"] == "prod"
        assert data["domain"] == "NPSB"
        cleanup_conversation(data["conversation_id"])

    def test_create_conversation_returns_valid_uuid(self, client, cleanup_conversation):
        """Conversation ID is a valid UUID."""
        response = client.post("/api/conversations", json={})

        assert response.status_code == 201
        data = response.json()
        # Validate UUID format
        uuid.UUID(data["conversation_id"])
        cleanup_conversation(data["conversation_id"])


class TestGetConversation:
    """Tests for GET /api/conversations/{conversation_id}."""

    def test_get_conversation_exists(self, client, cleanup_conversation):
        """Get existing conversation."""
        # Create first
        create_response = client.post("/api/conversations", json={"project": "NCC"})
        conv_id = create_response.json()["conversation_id"]
        cleanup_conversation(conv_id)

        # Get
        response = client.get(f"/api/conversations/{conv_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == conv_id
        assert data["project_code"] == "NCC"

    def test_get_conversation_not_found(self, client):
        """Get non-existent conversation returns 404."""
        response = client.get("/api/conversations/non-existent-id")

        assert response.status_code == 404

    def test_get_conversation_includes_messages(self, client, cleanup_conversation):
        """Get conversation includes messages."""
        # Create conversation
        create_response = client.post("/api/conversations", json={})
        conv_id = create_response.json()["conversation_id"]
        cleanup_conversation(conv_id)

        # Add messages directly via service for test setup
        with get_db_session() as db:
            service = ConversationService(db)
            service.add_message(conv_id, "user", "Test message")
            service.add_message(conv_id, "assistant", "Test response")

        # Get conversation
        response = client.get(f"/api/conversations/{conv_id}")

        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert len(data["messages"]) == 2


class TestListConversations:
    """Tests for GET /api/conversations."""

    def test_list_conversations_empty(self, client):
        """List returns empty when no matching conversations."""
        response = client.get("/api/conversations", params={
            "project": "NONEXISTENT_PROJECT_XYZ"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["conversations"] == []
        assert data["total"] == 0

    def test_list_conversations_with_data(self, client, cleanup_conversation):
        """List returns conversations."""
        # Create some test conversations
        test_project = f"TEST_{uuid.uuid4().hex[:8]}"
        for _ in range(3):
            resp = client.post("/api/conversations", json={"project": test_project})
            cleanup_conversation(resp.json()["conversation_id"])

        response = client.get("/api/conversations", params={"project": test_project})

        assert response.status_code == 200
        data = response.json()
        assert len(data["conversations"]) == 3
        assert data["total"] == 3

    def test_list_conversations_pagination(self, client, cleanup_conversation):
        """List supports pagination."""
        test_project = f"TEST_{uuid.uuid4().hex[:8]}"
        for _ in range(5):
            resp = client.post("/api/conversations", json={"project": test_project})
            cleanup_conversation(resp.json()["conversation_id"])

        # Get first page
        response = client.get("/api/conversations", params={
            "project": test_project,
            "limit": 2,
            "offset": 0
        })

        assert response.status_code == 200
        data = response.json()
        assert len(data["conversations"]) == 2
        assert data["total"] == 5
        assert data["limit"] == 2
        assert data["offset"] == 0

    def test_list_conversations_filter_by_status(self, client, cleanup_conversation):
        """List filters by status."""
        test_project = f"TEST_{uuid.uuid4().hex[:8]}"

        # Create active conversation
        resp1 = client.post("/api/conversations", json={"project": test_project})
        conv_id1 = resp1.json()["conversation_id"]
        cleanup_conversation(conv_id1)

        # Create and archive another
        resp2 = client.post("/api/conversations", json={"project": test_project})
        conv_id2 = resp2.json()["conversation_id"]
        cleanup_conversation(conv_id2)
        client.delete(f"/api/conversations/{conv_id2}")

        # List active only
        response = client.get("/api/conversations", params={
            "project": test_project,
            "status": "active"
        })

        data = response.json()
        assert len(data["conversations"]) == 1


class TestUpdateConversation:
    """Tests for PATCH /api/conversations/{conversation_id}."""

    def test_update_conversation_title(self, client, cleanup_conversation):
        """Update conversation title."""
        # Create
        create_resp = client.post("/api/conversations", json={})
        conv_id = create_resp.json()["conversation_id"]
        cleanup_conversation(conv_id)

        # Update
        response = client.patch(f"/api/conversations/{conv_id}", json={
            "title": "New Title"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "New Title"

    def test_update_conversation_not_found(self, client):
        """Update non-existent conversation returns 404."""
        response = client.patch("/api/conversations/fake-id", json={
            "title": "Test"
        })

        assert response.status_code == 404

    def test_update_conversation_multiple_fields(self, client, cleanup_conversation):
        """Update multiple fields."""
        create_resp = client.post("/api/conversations", json={})
        conv_id = create_resp.json()["conversation_id"]
        cleanup_conversation(conv_id)

        response = client.patch(f"/api/conversations/{conv_id}", json={
            "title": "Updated Title",
            "domain": "BEFTN"
        })

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert data["domain"] == "BEFTN"


class TestDeleteConversation:
    """Tests for DELETE /api/conversations/{conversation_id}."""

    def test_delete_conversation(self, client, cleanup_conversation):
        """Delete (archive) conversation."""
        # Create
        create_resp = client.post("/api/conversations", json={})
        conv_id = create_resp.json()["conversation_id"]
        # No need to cleanup - we're deleting

        # Delete
        response = client.delete(f"/api/conversations/{conv_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "archived"

        # Verify archived
        get_resp = client.get(f"/api/conversations/{conv_id}")
        if get_resp.status_code == 200:
            assert get_resp.json()["status"] == "archived"

    def test_delete_conversation_not_found(self, client):
        """Delete non-existent conversation returns 404."""
        response = client.delete("/api/conversations/fake-id")

        assert response.status_code == 404


class TestConversationMessages:
    """Tests for message-related endpoints."""

    def test_add_message_to_conversation(self, client, cleanup_conversation):
        """Add message via API."""
        # Create conversation
        create_resp = client.post("/api/conversations", json={})
        conv_id = create_resp.json()["conversation_id"]
        cleanup_conversation(conv_id)

        # Add message
        response = client.post(f"/api/conversations/{conv_id}/messages", json={
            "content": "Test message content"
        })

        assert response.status_code == 200 or response.status_code == 201

    def test_add_message_nonexistent_conversation(self, client):
        """Add message to non-existent conversation returns 404."""
        response = client.post("/api/conversations/fake-id/messages", json={
            "content": "Test"
        })

        assert response.status_code == 404


class TestConversationSchemas:
    """Tests for API response schemas."""

    def test_conversation_response_schema(self, client, cleanup_conversation):
        """Response contains expected fields."""
        response = client.post("/api/conversations", json={"project": "MMBL"})
        cleanup_conversation(response.json()["conversation_id"])

        data = response.json()
        expected_fields = [
            "conversation_id",
            "project_code",
            "env",
            "domain",
            "title",
            "status",
            "is_active",
            "created_at",
        ]

        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    def test_list_response_schema(self, client):
        """List response contains pagination metadata."""
        response = client.get("/api/conversations", params={
            "project": "NONEXISTENT"
        })

        data = response.json()
        assert "conversations" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data


class TestConversationErrorHandling:
    """Tests for API error handling."""

    def test_invalid_status_filter(self, client):
        """Invalid status filter handled gracefully."""
        response = client.get("/api/conversations", params={
            "status": "invalid_status"
        })

        # Should either return empty or validation error
        assert response.status_code in [200, 400, 422]

    def test_negative_offset(self, client):
        """Negative offset returns validation error."""
        response = client.get("/api/conversations", params={
            "offset": -1
        })

        assert response.status_code == 422

    def test_excessive_limit(self, client):
        """Excessive limit is capped or rejected."""
        response = client.get("/api/conversations", params={
            "limit": 1000
        })

        # Should either cap the limit or return validation error
        assert response.status_code in [200, 422]
        if response.status_code == 200:
            assert response.json()["limit"] <= 100


class TestFeatureFlag:
    """Tests for persistent conversations feature flag."""

    def test_feature_disabled_returns_501(self):
        """When feature flag is disabled, API returns 501."""
        # Temporarily disable feature flag
        original_value = config.settings.USE_PERSISTENT_CONVERSATIONS
        config.settings.USE_PERSISTENT_CONVERSATIONS = False

        try:
            client = TestClient(app)

            # Test all endpoints return 501
            response = client.post("/api/conversations", json={})
            assert response.status_code == 501
            assert "not enabled" in response.json()["detail"]

            response = client.get("/api/conversations")
            assert response.status_code == 501

            response = client.get("/api/conversations/test-id")
            assert response.status_code == 501

            response = client.patch("/api/conversations/test-id", json={"title": "Test"})
            assert response.status_code == 501

            response = client.delete("/api/conversations/test-id")
            assert response.status_code == 501

            response = client.post("/api/conversations/test-id/messages", json={"content": "Test"})
            assert response.status_code == 501

            response = client.get("/api/conversations/test-id/messages")
            assert response.status_code == 501

        finally:
            config.settings.USE_PERSISTENT_CONVERSATIONS = original_value

    def test_feature_enabled_allows_requests(self, client, cleanup_conversation):
        """When feature flag is enabled, API works normally."""
        response = client.post("/api/conversations", json={})

        assert response.status_code == 201
        data = response.json()
        assert "conversation_id" in data
        cleanup_conversation(data["conversation_id"])
