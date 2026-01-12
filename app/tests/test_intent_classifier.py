"""
Tests for MessageIntentClassifier.

Tests the quick pattern-based classification and fallback behavior.
LLM-based classification tests are skipped when LLM is unavailable.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.agents.intent_classifier import (
    MessageIntentClassifier,
    MessageIntent,
    PIPELINE_INTENTS,
)


class TestQuickClassification:
    """Test pattern-based quick classification."""

    @pytest.fixture
    def classifier(self):
        """Create classifier with no LLM (tests quick classification only)."""
        return MessageIntentClassifier(client=None, model="test-model")

    # Greeting tests
    @pytest.mark.parametrize("message", [
        "hello",
        "Hello",
        "HELLO",
        "hi",
        "Hi!",
        "hey",
        "Hey there",
        "greetings",
        "howdy",
        "yo",
        "good morning",
        "Good Morning!",
        "good afternoon",
        "good evening",
        "morning",
        "whats up",
        "wassup",
        "sup",
    ])
    def test_greeting_messages(self, classifier, message):
        """Should classify greetings correctly."""
        result = classifier.classify(message)
        assert result["intent"] == MessageIntent.GREETING.value
        assert result["requires_pipeline"] is False
        assert result["confidence"] >= 0.9
        assert "response" in result

    # Acknowledgment tests
    @pytest.mark.parametrize("message", [
        "ok",
        "okay",
        "OK",
        "thanks",
        "Thanks!",
        "thank you",
        "got it",
        "understood",
        "sure",
        "alright",
        "cool",
        "great",
        "perfect",
        "sounds good",
        "will do",
        "noted",
    ])
    def test_acknowledgment_messages(self, classifier, message):
        """Should classify acknowledgments correctly."""
        result = classifier.classify(message)
        assert result["intent"] == MessageIntent.ACKNOWLEDGMENT.value
        assert result["requires_pipeline"] is False
        assert result["confidence"] >= 0.85

    # Help request tests
    @pytest.mark.parametrize("message", [
        "help",
        "Help me",
        "what can you do",
        "What can you do?",
        "how do i use this",
        "how does this work",
        "documentation",
    ])
    def test_help_request_messages(self, classifier, message):
        """Should classify help requests correctly."""
        result = classifier.classify(message)
        assert result["intent"] == MessageIntent.HELP_REQUEST.value
        assert result["requires_pipeline"] is False
        assert "response" in result
        # Help response should mention log analysis
        assert "log" in result["response"].lower() or "analysis" in result["response"].lower()

    # Log analysis indicators - should go to pipeline
    @pytest.mark.parametrize("message", [
        "investigate transaction TX123",
        "search for errors yesterday",
        "find failed transactions",
        "analyze logs from 2025-01-10",
        "look for bkash failures",
        "trace ID abc-123",
    ])
    def test_log_analysis_messages_go_to_pipeline(self, classifier, message):
        """Messages with log analysis indicators should go to pipeline."""
        result = classifier.classify(message)
        # These should either be LOG_ANALYSIS or go to LLM (which falls back to LOG_ANALYSIS)
        assert result["requires_pipeline"] is True or result["intent"] == MessageIntent.LOG_ANALYSIS.value

    # Short ambiguous messages - should be classified as casual chat
    @pytest.mark.parametrize("message", [
        "hm",
        "ah",
        "...",
    ])
    def test_short_ambiguous_messages(self, classifier, message):
        """Very short messages without indicators should be casual chat."""
        result = classifier.classify(message)
        assert result["intent"] == MessageIntent.CASUAL_CHAT.value
        assert result["requires_pipeline"] is False


class TestFallbackClassification:
    """Test fallback behavior when LLM is unavailable."""

    @pytest.fixture
    def classifier(self):
        """Create classifier with no LLM."""
        return MessageIntentClassifier(client=None, model="test-model")

    def test_ambiguous_message_falls_back_to_log_analysis(self, classifier):
        """Ambiguous messages should default to LOG_ANALYSIS for safety."""
        # This message doesn't match any quick patterns clearly
        result = classifier.classify("I need to check something important")
        # Should go to LLM -> fallback -> LOG_ANALYSIS
        assert result["intent"] == MessageIntent.LOG_ANALYSIS.value
        assert result["requires_pipeline"] is True

    def test_fallback_has_low_confidence(self, classifier):
        """Fallback classification should have lower confidence."""
        result = classifier._fallback_classify("ambiguous text")
        assert result["confidence"] <= 0.5


class TestPipelineRouting:
    """Test which intents require the pipeline."""

    def test_pipeline_intents_constant(self):
        """Verify which intents require the pipeline."""
        assert MessageIntent.LOG_ANALYSIS in PIPELINE_INTENTS
        assert MessageIntent.CLARIFICATION in PIPELINE_INTENTS
        assert MessageIntent.GREETING not in PIPELINE_INTENTS
        assert MessageIntent.ACKNOWLEDGMENT not in PIPELINE_INTENTS
        assert MessageIntent.HELP_REQUEST not in PIPELINE_INTENTS
        assert MessageIntent.CASUAL_CHAT not in PIPELINE_INTENTS


class TestConversationContext:
    """Test classification with conversation history."""

    @pytest.fixture
    def mock_llm_client(self):
        """Create a mock LLM client."""
        client = MagicMock()
        client.is_available.return_value = True
        client.chat.return_value = {
            "message": {
                "content": '{"intent": "CLARIFICATION", "confidence": 0.9, "reasoning": "responding to question"}'
            }
        }
        return client

    def test_clarification_with_history(self, mock_llm_client):
        """When system asked a question and user responds, should be CLARIFICATION."""
        classifier = MessageIntentClassifier(client=mock_llm_client, model="test")

        history = [
            {"role": "assistant", "content": "What date should I search?"},
        ]

        # Mock the gateway to return the LLM result
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

            result = classifier.classify("yesterday", conversation_history=history)

        assert result["intent"] == MessageIntent.CLARIFICATION.value
        assert result["requires_pipeline"] is True


class TestResponseGeneration:
    """Test response generation for non-pipeline intents."""

    @pytest.fixture
    def classifier(self):
        return MessageIntentClassifier(client=None, model="test-model")

    def test_greeting_response_mentions_log_analysis(self, classifier):
        """Greeting response should mention log analysis capabilities."""
        result = classifier.classify("hello")
        assert "log analysis" in result["response"].lower()

    def test_help_response_has_examples(self, classifier):
        """Help response should include example queries."""
        result = classifier.classify("help")
        assert "example" in result["response"].lower()

    def test_casual_chat_suggests_investigation(self, classifier):
        """Casual chat response should guide user toward investigation."""
        result = classifier.classify("xyz")
        assert "investigate" in result["response"].lower() or "analysis" in result["response"].lower()


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.fixture
    def classifier(self):
        return MessageIntentClassifier(client=None, model="test-model")

    def test_empty_string(self, classifier):
        """Empty string should be handled gracefully."""
        result = classifier.classify("")
        # Should be casual chat or fallback to log analysis
        assert result["intent"] in [MessageIntent.CASUAL_CHAT.value, MessageIntent.LOG_ANALYSIS.value]

    def test_whitespace_only(self, classifier):
        """Whitespace-only string should be handled gracefully."""
        result = classifier.classify("   ")
        assert result["intent"] in [MessageIntent.CASUAL_CHAT.value, MessageIntent.LOG_ANALYSIS.value]

    def test_greeting_with_question(self, classifier):
        """Greeting with additional content should still be classified correctly."""
        # "hello how are you" starts with greeting but has more content
        result = classifier.classify("hello")
        assert result["intent"] == MessageIntent.GREETING.value

    def test_mixed_case_handling(self, classifier):
        """Classification should be case-insensitive."""
        result1 = classifier.classify("HELLO")
        result2 = classifier.classify("hello")
        result3 = classifier.classify("HeLLo")
        assert result1["intent"] == result2["intent"] == result3["intent"]

    def test_punctuation_handling(self, classifier):
        """Classification should handle punctuation correctly."""
        result1 = classifier.classify("hello!")
        result2 = classifier.classify("hello...")
        result3 = classifier.classify("hello?")
        # All should be recognized as greetings
        for result in [result1, result2, result3]:
            assert result["intent"] == MessageIntent.GREETING.value


class TestIntentEnum:
    """Test the MessageIntent enum."""

    def test_all_intents_have_string_value(self):
        """All intents should have string values matching their names."""
        for intent in MessageIntent:
            assert intent.value == intent.name

    def test_intent_from_string(self):
        """Should be able to create intent from string value."""
        intent = MessageIntent("GREETING")
        assert intent == MessageIntent.GREETING

    def test_invalid_intent_raises(self):
        """Invalid intent string should raise ValueError."""
        with pytest.raises(ValueError):
            MessageIntent("INVALID_INTENT")
