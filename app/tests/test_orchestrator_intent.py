"""
Tests for Orchestrator intent classification integration.

Verifies that the orchestrator correctly routes messages based on intent:
- Greetings short-circuit the pipeline
- Log analysis requests proceed through the pipeline
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.orchestrator import Orchestrator


class TestOrchestratorIntentRouting:
    """Test that orchestrator correctly routes based on intent."""

    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mock LLM provider."""
        provider = MagicMock()
        provider.is_available.return_value = False  # Force quick classification
        return provider

    @pytest.fixture
    def orchestrator(self, mock_llm_provider, tmp_path):
        """Create orchestrator with mocked LLM."""
        def mock_get_setting(category, key, default=None):
            defaults = {
                ("paths", "analysis_output"): str(tmp_path / "analysis"),
                ("paths", "verification_output"): str(tmp_path / "verification"),
            }
            return defaults.get((category, key), default)

        with patch('app.orchestrator.get_setting', side_effect=mock_get_setting):
            return Orchestrator(mock_llm_provider, model="test-model", log_base_dir=str(tmp_path))

    @pytest.mark.asyncio
    async def test_greeting_short_circuits_pipeline(self, orchestrator):
        """Greeting messages should return early without running the pipeline."""
        events = []
        async for event_name, data in orchestrator.analyze_stream(
            text="hello",
            project="TEST",
            env="prod",
            domain="test"
        ):
            events.append((event_name, data))

        # Should have: Classified Intent, then done
        event_names = [e[0] for e in events]
        assert "Classified Intent" in event_names
        assert "done" in event_names

        # Should NOT have parameter extraction or later steps
        assert "Extracted Parameters" not in event_names
        assert "Found relevant files" not in event_names

        # Done event should indicate non-pipeline response
        done_event = next(e for e in events if e[0] == "done")
        assert done_event[1].get("status") == "non_pipeline_response"
        assert done_event[1].get("intent") == "GREETING"
        assert "message" in done_event[1]

    @pytest.mark.asyncio
    async def test_help_request_short_circuits_pipeline(self, orchestrator):
        """Help requests should return early without running the pipeline."""
        events = []
        async for event_name, data in orchestrator.analyze_stream(
            text="help",
            project="TEST",
            env="prod",
            domain="test"
        ):
            events.append((event_name, data))

        event_names = [e[0] for e in events]
        assert "Classified Intent" in event_names
        assert "done" in event_names
        assert "Extracted Parameters" not in event_names

        done_event = next(e for e in events if e[0] == "done")
        assert done_event[1].get("status") == "non_pipeline_response"
        assert done_event[1].get("intent") == "HELP_REQUEST"

    @pytest.mark.asyncio
    async def test_acknowledgment_short_circuits_pipeline(self, orchestrator):
        """Acknowledgments should return early without running the pipeline."""
        events = []
        async for event_name, data in orchestrator.analyze_stream(
            text="thanks",
            project="TEST",
            env="prod",
            domain="test"
        ):
            events.append((event_name, data))

        event_names = [e[0] for e in events]
        assert "Classified Intent" in event_names
        assert "done" in event_names
        assert "Extracted Parameters" not in event_names

        done_event = next(e for e in events if e[0] == "done")
        assert done_event[1].get("status") == "non_pipeline_response"
        assert done_event[1].get("intent") == "ACKNOWLEDGMENT"

    @pytest.mark.asyncio
    async def test_log_analysis_proceeds_to_pipeline(self, orchestrator):
        """Log analysis requests should proceed through the pipeline."""
        # Mock the planning agent to return can_proceed=False (so we don't need full setup)
        orchestrator.planning_agent.run = MagicMock(return_value={
            "can_proceed": False,
            "blocking_questions": ["What date should I search?"],
            "goal": "Analyze logs",
            "assumptions": [],
            "steps": [],
            "expected_artifacts": [],
            "warnings": []
        })

        events = []
        async for event_name, data in orchestrator.analyze_stream(
            text="investigate failed transactions yesterday",
            project="TEST",
            env="prod",
            domain="test"
        ):
            events.append((event_name, data))

        event_names = [e[0] for e in events]

        # Should have intent classification AND parameter extraction
        assert "Classified Intent" in event_names
        assert "Extracted Parameters" in event_names

        # Should have proceeded to planning (even if stopped there)
        assert "Need Clarification" in event_names or "done" in event_names


class TestOrchestratorIntentClassification:
    """Test the intent classification step itself."""

    @pytest.fixture
    def mock_llm_provider(self):
        provider = MagicMock()
        provider.is_available.return_value = False
        return provider

    @pytest.fixture
    def orchestrator(self, mock_llm_provider, tmp_path):
        def mock_get_setting(category, key, default=None):
            defaults = {
                ("paths", "analysis_output"): str(tmp_path / "analysis"),
                ("paths", "verification_output"): str(tmp_path / "verification"),
            }
            return defaults.get((category, key), default)

        with patch('app.orchestrator.get_setting', side_effect=mock_get_setting):
            return Orchestrator(mock_llm_provider, model="test-model", log_base_dir=str(tmp_path))

    def test_step0_classify_intent_returns_dict(self, orchestrator):
        """Step 0 should return a dictionary with expected keys."""
        result = orchestrator._step0_classify_intent("hello")

        assert isinstance(result, dict)
        assert "intent" in result
        assert "confidence" in result
        assert "requires_pipeline" in result

    def test_step0_greeting_does_not_require_pipeline(self, orchestrator):
        """Greetings should not require the pipeline."""
        result = orchestrator._step0_classify_intent("hello")

        assert result["intent"] == "GREETING"
        assert result["requires_pipeline"] is False

    def test_step0_log_query_requires_pipeline(self, orchestrator):
        """Log analysis queries should require the pipeline."""
        result = orchestrator._step0_classify_intent("find errors in transaction logs yesterday")

        assert result["requires_pipeline"] is True


class TestOrchestratorWithConversationHistory:
    """Test intent classification with conversation context."""

    @pytest.fixture
    def mock_llm_provider(self):
        provider = MagicMock()
        provider.is_available.return_value = True
        provider.chat.return_value = {
            "message": {
                "content": '{"intent": "CLARIFICATION", "confidence": 0.9, "reasoning": "responding to question"}'
            }
        }
        return provider

    @pytest.fixture
    def orchestrator(self, mock_llm_provider, tmp_path):
        def mock_get_setting(category, key, default=None):
            defaults = {
                ("paths", "analysis_output"): str(tmp_path / "analysis"),
                ("paths", "verification_output"): str(tmp_path / "verification"),
            }
            return defaults.get((category, key), default)

        with patch('app.orchestrator.get_setting', side_effect=mock_get_setting):
            return Orchestrator(mock_llm_provider, model="test-model", log_base_dir=str(tmp_path))

    def test_step0_with_conversation_history(self, orchestrator):
        """Intent classification should consider conversation history."""
        history = [
            {"role": "assistant", "content": "What date should I search?"}
        ]

        with patch('app.agents.intent_classifier.get_llm_cache_gateway') as mock_gateway:
            mock_cached = MagicMock()
            mock_cached.cached.return_value = (
                {
                    "intent": "CLARIFICATION",
                    "confidence": 0.9,
                    "reasoning": "responding to question",
                    "requires_pipeline": True
                },
                MagicMock(status="miss", key_prefix="test")
            )
            mock_gateway.return_value = mock_cached

            result = orchestrator._step0_classify_intent(
                "yesterday",
                conversation_history=history
            )

        assert result["intent"] == "CLARIFICATION"
        assert result["requires_pipeline"] is True
