"""
Message Intent Classifier Agent

Classifies user messages to determine appropriate routing:
- GREETING: Conversational greetings (hello, hi, hey)
- ACKNOWLEDGMENT: Acknowledgments (ok, thanks, got it)
- HELP_REQUEST: Requests for help or documentation
- CLARIFICATION: Direct responses to clarifying questions
- LOG_ANALYSIS: Actual log analysis requests
- CASUAL_CHAT: Off-topic conversational content

This agent runs BEFORE parameter extraction to avoid unnecessary
pipeline processing for non-analysis messages.
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any, Dict, List, Optional

import regex as re

from app.services.llm_providers import LLMProvider
from app.services.llm_gateway.gateway import CachePolicy, CacheableValue, get_llm_cache_gateway


logger = logging.getLogger(__name__)

_RE_FENCED_JSON = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
_RE_BALANCED_OBJ = re.compile(r"(\{(?:[^{}]|(?1))*\})", re.DOTALL)
_RE_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_RE_THINK_UNCLOSED = re.compile(r"<think>.*", re.DOTALL | re.IGNORECASE)


class MessageIntent(str, Enum):
    """Possible message intents."""
    GREETING = "GREETING"
    ACKNOWLEDGMENT = "ACKNOWLEDGMENT"
    HELP_REQUEST = "HELP_REQUEST"
    CLARIFICATION = "CLARIFICATION"
    LOG_ANALYSIS = "LOG_ANALYSIS"
    CASUAL_CHAT = "CASUAL_CHAT"


# Intents that require the full pipeline
PIPELINE_INTENTS = {MessageIntent.LOG_ANALYSIS, MessageIntent.CLARIFICATION}


class MessageIntentClassifier:
    """
    Classifies user messages to determine routing before parameter extraction.

    For simple messages like "hello", this prevents unnecessary LLM calls
    and pipeline processing.
    """

    def __init__(self, client: Optional[LLMProvider], model: str):
        self.client = client
        self.model = model

    def classify(
        self,
        text: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        cache_policy: Optional[CachePolicy] = None,
    ) -> Dict[str, Any]:
        """
        Classify the user's message intent.

        Args:
            text: The user's message
            conversation_history: Optional previous messages for context
            cache_policy: Optional cache policy

        Returns:
            {
                "intent": "GREETING" | "LOG_ANALYSIS" | etc,
                "confidence": 0.0-1.0,
                "reasoning": "why this intent was chosen",
                "requires_pipeline": bool,
                "response": Optional[str] - for non-pipeline intents
            }
        """
        # Quick pattern-based classification for common cases
        quick_result = self._quick_classify(text)
        if quick_result:
            logger.info(f"Quick classification: {quick_result['intent']} (confidence: {quick_result['confidence']})")
            return quick_result

        # Fall back to LLM classification for ambiguous cases
        if not self.client or not self.client.is_available():
            return self._fallback_classify(text)

        try:
            return self._llm_classify(text, conversation_history, cache_policy)
        except Exception as e:
            logger.warning(f"LLM classification failed, using fallback: {e}")
            return self._fallback_classify(text)

    def _quick_classify(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Fast pattern-based classification for obvious cases.
        Returns None if classification is ambiguous.
        """
        normalized = text.strip().lower()

        # Handle empty input
        if not normalized:
            return {
                "intent": MessageIntent.CASUAL_CHAT.value,
                "confidence": 0.5,
                "reasoning": "Empty message",
                "requires_pipeline": False,
                "response": "I didn't receive a message. How can I help you with log analysis?"
            }

        # Remove punctuation for matching
        clean = re.sub(r'[^\w\s]', '', normalized)
        words = clean.split()

        # Handle empty after punctuation removal (e.g., "...")
        if not words:
            return {
                "intent": MessageIntent.CASUAL_CHAT.value,
                "confidence": 0.5,
                "reasoning": "Message contains only punctuation",
                "requires_pipeline": False,
                "response": "I'm a log analysis assistant. How can I help you investigate logs today?"
            }

        # Greeting patterns
        greeting_patterns = {
            'hello', 'hi', 'hey', 'greetings', 'howdy', 'yo',
            'good morning', 'good afternoon', 'good evening',
            'morning', 'afternoon', 'evening',
            'whats up', 'wassup', 'sup'
        }

        if clean in greeting_patterns or (len(words) <= 3 and words[0] in greeting_patterns):
            return {
                "intent": MessageIntent.GREETING.value,
                "confidence": 0.95,
                "reasoning": "Message matches common greeting pattern",
                "requires_pipeline": False,
                "response": "Hello! How can I help you with log analysis today?"
            }

        # Acknowledgment patterns
        ack_patterns = {
            'ok', 'okay', 'thanks', 'thank you', 'got it',
            'understood', 'sure', 'alright', 'cool', 'great',
            'perfect', 'sounds good', 'will do', 'noted'
        }

        if clean in ack_patterns:
            return {
                "intent": MessageIntent.ACKNOWLEDGMENT.value,
                "confidence": 0.90,
                "reasoning": "Message is an acknowledgment",
                "requires_pipeline": False,
                "response": "Is there anything else you'd like me to help you with?"
            }

        # Help patterns
        help_patterns = ['help', 'what can you do', 'how do i', 'how does this work', 'documentation']
        if any(pattern in clean for pattern in help_patterns):
            return {
                "intent": MessageIntent.HELP_REQUEST.value,
                "confidence": 0.85,
                "reasoning": "Message is a help request",
                "requires_pipeline": False,
                "response": self._get_help_response()
            }

        # If message contains clear log analysis indicators, route to pipeline
        log_indicators = [
            'transaction', 'trace', 'log', 'error', 'failure', 'failed',
            'investigate', 'analyze', 'search', 'find', 'look for',
            'yesterday', 'today', 'last week', 'jan', 'feb', 'mar', 'apr',
            'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
            '2024', '2025', '2026'
        ]

        if any(indicator in clean for indicator in log_indicators):
            # This looks like a log analysis request, let the pipeline handle it
            return None

        # Very short messages without log indicators are likely casual
        if len(words) <= 2 and not any(indicator in clean for indicator in log_indicators):
            return {
                "intent": MessageIntent.CASUAL_CHAT.value,
                "confidence": 0.70,
                "reasoning": "Short message without log analysis indicators",
                "requires_pipeline": False,
                "response": "I'm a log analysis assistant. Could you please provide details about what you'd like me to investigate? For example, you can ask me to analyze transactions, search for errors, or investigate specific trace IDs."
            }

        # Ambiguous - needs LLM classification
        return None

    def _llm_classify(
        self,
        text: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        cache_policy: Optional[CachePolicy] = None,
    ) -> Dict[str, Any]:
        """Use LLM for intent classification when patterns are ambiguous."""
        messages = [{"role": "system", "content": self._system_prompt()}]

        # Add conversation history for context
        if conversation_history:
            # Include last few messages for context
            recent_history = conversation_history[-4:] if len(conversation_history) > 4 else conversation_history
            for msg in recent_history:
                messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": self._user_payload(text, conversation_history)})

        gateway = get_llm_cache_gateway()

        def compute() -> CacheableValue:
            resp = self.client.chat(model=self.model, messages=messages, options={"timeout": 15})
            raw = (resp.get("message") or {}).get("content") or ""
            result = self._parse_response(raw, text)
            return CacheableValue(value=result, cacheable=True)

        result, diag = gateway.cached(
            cache_type="intent_classification",
            model=self.model,
            messages=messages,
            options={"timeout": 15},
            default_ttl_seconds=300,  # Short TTL for intent classification
            policy=cache_policy,
            compute=compute,
        )

        logger.info(f"Intent classification cache: {diag.status} (key: {diag.key_prefix[:12] if diag.key_prefix else 'N/A'}...)")
        return result

    def _system_prompt(self) -> str:
        return """You are a message intent classifier for a log analysis system.
Your job is to classify user messages to determine how they should be handled.

Classify each message into ONE of these categories:

- GREETING: Conversational greetings like "hello", "hi", "hey", "good morning"
- ACKNOWLEDGMENT: Acknowledgments like "ok", "thanks", "got it", "understood"
- HELP_REQUEST: Requests for help like "help", "what can you do", "how does this work"
- CLARIFICATION: Direct response to a previous clarifying question (e.g., providing a date, ID, or keyword when asked)
- LOG_ANALYSIS: Request for log/transaction analysis - mentions dates, transaction IDs, errors, keywords, or investigation needs
- CASUAL_CHAT: Off-topic conversation that doesn't fit other categories

IMPORTANT RULES:
1. Output ONLY valid JSON. No markdown, no explanations outside the JSON.
2. Consider conversation history - if the system asked for a date and user responds with just "yesterday", that's CLARIFICATION not CASUAL_CHAT.
3. When in doubt between CASUAL_CHAT and LOG_ANALYSIS, prefer LOG_ANALYSIS (we can ask clarifying questions later).
4. Messages with dates, IDs, technical terms, or investigation keywords → LOG_ANALYSIS
5. Simple greetings without additional content → GREETING

OUTPUT FORMAT (strict JSON):
{
  "intent": "GREETING|ACKNOWLEDGMENT|HELP_REQUEST|CLARIFICATION|LOG_ANALYSIS|CASUAL_CHAT",
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}"""

    def _user_payload(self, text: str, conversation_history: Optional[List[Dict[str, str]]] = None) -> str:
        """Build user payload with context."""
        payload = {
            "message": text,
            "has_conversation_history": bool(conversation_history),
            "message_length": len(text.split())
        }

        # Add context about last system message if it was a question
        if conversation_history:
            for msg in reversed(conversation_history):
                if msg.get("role") == "assistant":
                    content = msg.get("content", "")
                    if "?" in content:
                        payload["last_system_asked_question"] = True
                    break

        return json.dumps(payload, ensure_ascii=False)

    def _parse_response(self, raw: str, original_text: str) -> Dict[str, Any]:
        """Parse LLM response and add pipeline routing."""
        try:
            text = (raw or "").strip()
            text = _RE_THINK_BLOCK.sub("", text)
            text = _RE_THINK_UNCLOSED.sub("", text).strip()

            fenced = _RE_FENCED_JSON.search(text)
            if fenced:
                text = fenced.group(1).strip()
            else:
                obj = _RE_BALANCED_OBJ.search(text)
                if obj:
                    text = obj.group(1).strip()

            result = json.loads(text)

            # Normalize and validate intent
            intent_str = result.get("intent", "LOG_ANALYSIS").upper()
            try:
                intent = MessageIntent(intent_str)
            except ValueError:
                intent = MessageIntent.LOG_ANALYSIS

            result["intent"] = intent.value
            result["requires_pipeline"] = intent in PIPELINE_INTENTS

            # Add response for non-pipeline intents
            if not result["requires_pipeline"]:
                result["response"] = self._get_response_for_intent(intent)

            return result

        except Exception as e:
            logger.warning(f"Failed to parse intent classification response: {e}")
            return self._fallback_classify(original_text)

    def _fallback_classify(self, text: str) -> Dict[str, Any]:
        """Fallback classification when LLM is unavailable."""
        # Default to LOG_ANALYSIS so the pipeline can ask clarifying questions
        return {
            "intent": MessageIntent.LOG_ANALYSIS.value,
            "confidence": 0.5,
            "reasoning": "Fallback classification - assuming log analysis request",
            "requires_pipeline": True
        }

    def _get_response_for_intent(self, intent: MessageIntent) -> str:
        """Get appropriate response for non-pipeline intents."""
        responses = {
            MessageIntent.GREETING: "Hello! How can I help you with log analysis today?",
            MessageIntent.ACKNOWLEDGMENT: "Is there anything else you'd like me to help you with?",
            MessageIntent.HELP_REQUEST: self._get_help_response(),
            MessageIntent.CASUAL_CHAT: "I'm a log analysis assistant. Could you please provide details about what you'd like me to investigate? For example, you can ask me to analyze transactions, search for errors, or investigate specific trace IDs.",
        }
        return responses.get(intent, "How can I help you?")

    def _get_help_response(self) -> str:
        """Generate help response explaining capabilities."""
        return """I'm a log analysis assistant. Here's what I can do:

**Log Analysis:**
- Search logs by date, transaction ID, or keywords
- Extract and correlate trace IDs across services
- Analyze transaction flows and identify issues

**How to use:**
1. Tell me what you want to investigate (e.g., "Failed transactions on 2025-01-10")
2. Provide any specific identifiers (transaction IDs, customer IDs, etc.)
3. I'll search the logs, compile relevant traces, and generate a report

**Example queries:**
- "Investigate failed bkash transactions yesterday"
- "Find logs for transaction ID TX123456"
- "Analyze NPSB errors from last week"

What would you like me to help you investigate?"""
