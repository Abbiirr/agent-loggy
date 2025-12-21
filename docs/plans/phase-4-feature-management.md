# Phase 4: Feature Management Plan

## Executive Summary

This phase implements feature flag management using **Flagsmith** to enable safe AI feature rollouts, instant kill switches, graceful degradation, and percentage-based deployments. Feature flags are essential for AI systems due to their unpredictable behavior in production - this system allows instant rollback without code deployment.

**Timeline**: Week 5-6
**Dependencies**: Phase 1 (Database), Phase 2 (Configuration)
**Blocking**: None (can run parallel with Phase 3)

---

## Current State Analysis

### What Exists
| Component | Location | Status |
|-----------|----------|--------|
| Feature Flags | None | No feature flag system |
| Kill Switches | None | Cannot disable features without deploy |
| Degradation | None | No fallback mechanisms |
| A/B Testing | None | No traffic splitting |

### Problems with Current Approach
1. **No Kill Switch**: Cannot disable AI features during incidents
2. **No Gradual Rollout**: All-or-nothing deployments
3. **No Degradation**: System fails completely on AI errors
4. **No Experimentation**: Cannot A/B test prompts or models
5. **No Per-User Targeting**: Same experience for all users

---

## Target Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Feature Management Architecture                       │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                           Application Layer                                   │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                      AIFeatureController                                │ │
│  │                                                                         │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────────┐ │ │
│  │  │ Master Kill  │  │ Per-Feature  │  │ Degradation                  │ │ │
│  │  │ Switch       │  │ Flags        │  │ Handlers                     │ │ │
│  │  │              │  │              │  │                              │ │ │
│  │  │ ai_enabled   │  │ rag_enabled  │  │ RAGDegradationHandler        │ │ │
│  │  │ = true/false │  │ analysis_    │  │ AnalysisDegradationHandler   │ │ │
│  │  │              │  │ enabled      │  │ StreamDegradationHandler     │ │ │
│  │  │              │  │ streaming_   │  │                              │ │ │
│  │  │              │  │ enabled      │  │ Returns: cached/simplified/  │ │ │
│  │  │              │  │              │  │          bypass responses    │ │ │
│  │  └──────┬───────┘  └──────┬───────┘  └──────────────┬───────────────┘ │ │
│  │         │                 │                         │                  │ │
│  │         └─────────────────┼─────────────────────────┘                  │ │
│  │                           │                                            │ │
│  └───────────────────────────┼────────────────────────────────────────────┘ │
│                              │                                               │
└──────────────────────────────┼───────────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                          Flagsmith Service                                    │
│                                                                              │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────┐  │
│  │ Environment          │  │ Feature Flags         │  │ Segments         │  │
│  │                      │  │                       │  │                  │  │
│  │ - production         │  │ - ai_master_switch    │  │ - beta_users     │  │
│  │ - staging            │  │ - rag_enabled         │  │ - internal       │  │
│  │ - development        │  │ - analysis_enabled    │  │ - high_volume    │  │
│  │                      │  │ - streaming_enabled   │  │                  │  │
│  │                      │  │ - new_model_rollout   │  │                  │  │
│  └──────────────────────┘  └──────────────────────┘  └──────────────────┘  │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │ Percentage Rollouts                                                   │  │
│  │                                                                       │  │
│  │  new_model_rollout: 10% → 25% → 50% → 100%                           │  │
│  │  rag_v2: beta_users (100%) + internal (100%) + all (0%)              │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                          Request Flow                                         │
│                                                                              │
│   Request → Check Master Switch → Check Feature Flag → Execute or Degrade   │
│                                                                              │
│   ┌─────────┐     ┌──────────────┐     ┌───────────────┐     ┌───────────┐ │
│   │ Request │────▶│ Master ON?   │────▶│ Feature ON?   │────▶│ Execute   │ │
│   └─────────┘     └──────┬───────┘     └───────┬───────┘     │ Feature   │ │
│                          │                     │              └───────────┘ │
│                          │ NO                  │ NO                         │
│                          ▼                     ▼                            │
│                   ┌──────────────┐     ┌───────────────┐                   │
│                   │ Return       │     │ Degradation   │                   │
│                   │ "AI Disabled"│     │ Handler       │                   │
│                   └──────────────┘     └───────────────┘                   │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Flagsmith Setup

### Docker Compose Addition

```yaml
# docker-compose.yml additions

services:
  # ... existing services ...

  flagsmith:
    image: flagsmith/flagsmith:latest
    ports:
      - "8001:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/flagsmith
      - DJANGO_ALLOWED_HOSTS=*
      - ENABLE_ADMIN_ACCESS_USER_PASS=true
      - ALLOW_REGISTRATION_WITHOUT_INVITE=true
    depends_on:
      - db
    volumes:
      - flagsmith_data:/flagsmith

  flagsmith-processor:
    image: flagsmith/flagsmith:latest
    command: run-task-processor
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/flagsmith
    depends_on:
      - flagsmith
      - db

volumes:
  flagsmith_data:
```

### Initial Flagsmith Configuration

Create these flags in Flagsmith UI or via API:

| Flag Name | Type | Default | Description |
|-----------|------|---------|-------------|
| `ai_master_switch` | Boolean | `true` | Master kill switch for all AI |
| `rag_enabled` | Boolean | `true` | Enable RAG retrieval |
| `analysis_enabled` | Boolean | `true` | Enable trace analysis |
| `streaming_enabled` | Boolean | `true` | Enable SSE streaming |
| `verification_enabled` | Boolean | `true` | Enable verification agent |
| `new_model_rollout` | Boolean | `false` | New model percentage rollout |
| `contextual_chunking` | Boolean | `false` | Use contextual vs late chunking |
| `reranking_enabled` | Boolean | `true` | Enable Cohere reranking |
| `max_context_messages` | Integer | `20` | Remote config value |
| `llm_timeout_seconds` | Integer | `120` | Remote config value |

---

## Core Implementation

### File: `app/features/__init__.py`

```python
"""Feature flag management package."""

from app.features.ai_feature_controller import AIFeatureController, get_feature_controller
from app.features.degradation_handlers import (
    DegradationHandler,
    RAGDegradationHandler,
    AnalysisDegradationHandler,
    StreamDegradationHandler
)

__all__ = [
    'AIFeatureController',
    'get_feature_controller',
    'DegradationHandler',
    'RAGDegradationHandler',
    'AnalysisDegradationHandler',
    'StreamDegradationHandler'
]
```

### File: `app/features/ai_feature_controller.py`

```python
"""
AIFeatureController - Central control for AI feature flags.

Provides:
- Master kill switch for all AI features
- Per-feature enable/disable
- Percentage-based rollouts
- User segment targeting
- Graceful degradation
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, Generic
import threading

from flagsmith import Flagsmith
from flagsmith.models import Flags

from app.config import settings
from app.features.degradation_handlers import (
    DegradationHandler,
    RAGDegradationHandler,
    AnalysisDegradationHandler,
    StreamDegradationHandler,
    DefaultDegradationHandler
)

logger = logging.getLogger(__name__)

T = TypeVar('T')


class FeatureState(Enum):
    """Possible states for a feature."""
    ENABLED = "enabled"
    DISABLED = "disabled"
    DEGRADED = "degraded"
    PERCENTAGE_ROLLOUT = "percentage_rollout"


@dataclass
class FeatureContext:
    """Context for feature flag evaluation."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    environment: Optional[str] = None
    traits: Optional[Dict[str, Any]] = None


class AIFeatureController:
    """
    Central controller for AI feature flags.

    Usage:
        controller = AIFeatureController.get_instance()

        # Check if feature is enabled
        if controller.is_enabled("rag"):
            result = rag_pipeline.search(query)
        else:
            result = controller.get_degraded_response("rag", query)

        # With context for user targeting
        context = FeatureContext(user_id="user123", traits={"plan": "premium"})
        if controller.is_enabled("new_model", context):
            use_new_model()
    """

    _instance: Optional["AIFeatureController"] = None
    _lock = threading.Lock()

    # Feature name to degradation handler mapping
    DEGRADATION_HANDLERS: Dict[str, type] = {
        "rag": RAGDegradationHandler,
        "analysis": AnalysisDegradationHandler,
        "streaming": StreamDegradationHandler,
    }

    # Feature name to flag name mapping
    FEATURE_FLAGS: Dict[str, str] = {
        "rag": "rag_enabled",
        "analysis": "analysis_enabled",
        "streaming": "streaming_enabled",
        "verification": "verification_enabled",
        "new_model": "new_model_rollout",
        "contextual_chunking": "contextual_chunking",
        "reranking": "reranking_enabled",
    }

    def __init__(self):
        """Initialize Flagsmith client."""
        self.enabled = settings.get("FEATURE_FLAGS_ENABLED", True)

        if self.enabled:
            flagsmith_url = settings.get("FLAGSMITH_URL", "http://localhost:8001/api/v1/")
            flagsmith_key = settings.get("FLAGSMITH_ENVIRONMENT_KEY")

            if not flagsmith_key:
                logger.warning("FLAGSMITH_ENVIRONMENT_KEY not set, using defaults")
                self.enabled = False
            else:
                self.client = Flagsmith(
                    environment_key=flagsmith_key,
                    api_url=flagsmith_url,
                    enable_local_evaluation=True,
                    environment_refresh_interval_seconds=60
                )

        # Initialize degradation handlers
        self.degradation_handlers: Dict[str, DegradationHandler] = {}
        self._init_degradation_handlers()

        # Cache for flag values
        self._flags_cache: Optional[Flags] = None
        self._cache_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "AIFeatureController":
        """Get singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _init_degradation_handlers(self) -> None:
        """Initialize degradation handlers for each feature."""
        for feature_name, handler_class in self.DEGRADATION_HANDLERS.items():
            self.degradation_handlers[feature_name] = handler_class()

    def _get_flags(self, context: Optional[FeatureContext] = None) -> Flags:
        """Get flags, optionally for a specific user context."""
        if not self.enabled:
            return None

        if context and context.user_id:
            # Get identity-specific flags
            traits = context.traits or {}
            return self.client.get_identity_flags(
                identifier=context.user_id,
                traits=traits
            )
        else:
            # Get environment flags
            with self._cache_lock:
                if self._flags_cache is None:
                    self._flags_cache = self.client.get_environment_flags()
                return self._flags_cache

    def refresh_flags(self) -> None:
        """Force refresh of cached flags."""
        with self._cache_lock:
            self._flags_cache = None

        if self.enabled:
            self.client.update_environment()

    # =========================================================================
    # MASTER SWITCH
    # =========================================================================

    def is_ai_enabled(self, context: Optional[FeatureContext] = None) -> bool:
        """
        Check master AI kill switch.

        This is the FIRST check before any AI feature.
        If False, ALL AI features are disabled.
        """
        if not self.enabled:
            return True  # Default to enabled if Flagsmith not configured

        flags = self._get_flags(context)
        if flags is None:
            return True

        try:
            return flags.is_feature_enabled("ai_master_switch")
        except Exception as e:
            logger.error(f"Error checking master switch: {e}")
            return True  # Fail open

    # =========================================================================
    # FEATURE CHECKS
    # =========================================================================

    def is_enabled(
        self,
        feature: str,
        context: Optional[FeatureContext] = None
    ) -> bool:
        """
        Check if a specific feature is enabled.

        Always checks master switch first.

        Args:
            feature: Feature name (e.g., "rag", "analysis", "streaming")
            context: Optional user context for targeting

        Returns:
            True if feature is enabled
        """
        # Check master switch first
        if not self.is_ai_enabled(context):
            logger.info(f"Feature '{feature}' blocked by master switch")
            return False

        if not self.enabled:
            return True  # Default enabled

        flag_name = self.FEATURE_FLAGS.get(feature, f"{feature}_enabled")
        flags = self._get_flags(context)

        if flags is None:
            return True

        try:
            return flags.is_feature_enabled(flag_name)
        except Exception as e:
            logger.error(f"Error checking feature '{feature}': {e}")
            return True  # Fail open

    def get_feature_value(
        self,
        feature: str,
        default: Any = None,
        context: Optional[FeatureContext] = None
    ) -> Any:
        """
        Get a feature's remote config value.

        Args:
            feature: Feature name
            default: Default value if not found
            context: Optional user context

        Returns:
            Feature value or default
        """
        if not self.enabled:
            return default

        flag_name = self.FEATURE_FLAGS.get(feature, feature)
        flags = self._get_flags(context)

        if flags is None:
            return default

        try:
            return flags.get_feature_value(flag_name, default)
        except Exception as e:
            logger.error(f"Error getting value for '{feature}': {e}")
            return default

    # =========================================================================
    # DEGRADATION
    # =========================================================================

    def get_degraded_response(
        self,
        feature: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Get a degraded response when feature is disabled.

        Args:
            feature: Feature name
            *args, **kwargs: Arguments to pass to degradation handler

        Returns:
            Degraded response appropriate for the feature
        """
        handler = self.degradation_handlers.get(
            feature,
            DefaultDegradationHandler()
        )

        return handler.handle(*args, **kwargs)

    def execute_with_fallback(
        self,
        feature: str,
        func: Callable[..., T],
        *args,
        context: Optional[FeatureContext] = None,
        **kwargs
    ) -> T:
        """
        Execute a function with automatic fallback to degradation.

        Args:
            feature: Feature name
            func: Function to execute if enabled
            *args, **kwargs: Function arguments
            context: Optional user context

        Returns:
            Function result or degraded response
        """
        if self.is_enabled(feature, context):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Feature '{feature}' failed: {e}, using degradation")
                return self.get_degraded_response(feature, *args, **kwargs)
        else:
            return self.get_degraded_response(feature, *args, **kwargs)

    # =========================================================================
    # STATUS & MONITORING
    # =========================================================================

    def get_all_feature_states(
        self,
        context: Optional[FeatureContext] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Get current state of all features.

        Returns:
            Dict mapping feature name to state info
        """
        states = {}

        # Master switch
        ai_enabled = self.is_ai_enabled(context)
        states["ai_master_switch"] = {
            "enabled": ai_enabled,
            "state": FeatureState.ENABLED.value if ai_enabled else FeatureState.DISABLED.value
        }

        # Individual features
        for feature, flag_name in self.FEATURE_FLAGS.items():
            enabled = self.is_enabled(feature, context)
            value = self.get_feature_value(feature, context=context)

            states[feature] = {
                "enabled": enabled,
                "flag_name": flag_name,
                "value": value,
                "state": FeatureState.ENABLED.value if enabled else FeatureState.DISABLED.value,
                "has_degradation": feature in self.degradation_handlers
            }

        return states

    def log_feature_state(self) -> None:
        """Log current feature state for debugging."""
        states = self.get_all_feature_states()

        logger.info("Current feature states:")
        for feature, state in states.items():
            logger.info(f"  {feature}: {state['state']} (enabled={state['enabled']})")


# Convenience function
def get_feature_controller() -> AIFeatureController:
    """Get the singleton AIFeatureController instance."""
    return AIFeatureController.get_instance()
```

### File: `app/features/degradation_handlers.py`

```python
"""
Degradation handlers for graceful fallback when features are disabled.

Each handler provides a sensible fallback response that maintains
system functionality without the full AI capability.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class DegradationHandler(ABC):
    """Abstract base class for degradation handlers."""

    @abstractmethod
    def handle(self, *args, **kwargs) -> Any:
        """
        Handle a degraded request.

        Should return a reasonable fallback response.
        """
        pass

    @property
    def degradation_message(self) -> str:
        """Message explaining the degradation."""
        return "Feature temporarily unavailable"


class DefaultDegradationHandler(DegradationHandler):
    """Default handler when no specific handler exists."""

    def handle(self, *args, **kwargs) -> Dict[str, Any]:
        return {
            "status": "degraded",
            "message": self.degradation_message,
            "timestamp": datetime.utcnow().isoformat()
        }


class RAGDegradationHandler(DegradationHandler):
    """
    Degradation handler for RAG pipeline.

    When RAG is disabled:
    - Returns empty context
    - Uses cached rules if available
    - Falls back to keyword matching
    """

    def __init__(self, cache_client: Optional[Any] = None):
        self.cache_client = cache_client

    @property
    def degradation_message(self) -> str:
        return "RAG retrieval temporarily disabled, using basic search"

    def handle(
        self,
        query: str = "",
        top_k: int = 10,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Return degraded RAG response.

        Args:
            query: Search query
            top_k: Number of results requested

        Returns:
            Degraded response with empty or cached results
        """
        logger.info(f"RAG degraded for query: {query[:50]}...")

        # Try to get cached results
        cached_results = self._get_cached_results(query)

        if cached_results:
            return {
                "status": "degraded",
                "source": "cache",
                "message": self.degradation_message,
                "results": cached_results,
                "total": len(cached_results)
            }

        # Return empty results with explanation
        return {
            "status": "degraded",
            "source": "none",
            "message": self.degradation_message,
            "results": [],
            "total": 0,
            "fallback_suggestion": "Try using exact keyword search instead"
        }

    def _get_cached_results(self, query: str) -> List[Dict]:
        """Attempt to get cached results."""
        if self.cache_client is None:
            return []

        try:
            # Try to get from cache
            cache_key = f"rag:query:{hash(query)}"
            cached = self.cache_client.get(cache_key)
            if cached:
                return cached
        except Exception:
            pass

        return []


class AnalysisDegradationHandler(DegradationHandler):
    """
    Degradation handler for trace analysis.

    When analysis is disabled:
    - Returns basic trace statistics
    - Skips LLM-based analysis
    - Provides raw log data only
    """

    @property
    def degradation_message(self) -> str:
        return "AI analysis temporarily disabled, showing raw trace data"

    def handle(
        self,
        trace_id: str = "",
        log_entries: Optional[List[Dict]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Return degraded analysis response.

        Args:
            trace_id: Trace identifier
            log_entries: Raw log entries

        Returns:
            Basic statistics without AI analysis
        """
        logger.info(f"Analysis degraded for trace: {trace_id}")

        log_entries = log_entries or []

        # Compute basic statistics
        stats = self._compute_basic_stats(log_entries)

        return {
            "status": "degraded",
            "message": self.degradation_message,
            "trace_id": trace_id,
            "analysis_type": "basic_stats",
            "statistics": stats,
            "ai_analysis": None,
            "recommendation": "Full AI analysis unavailable. Review logs manually."
        }

    def _compute_basic_stats(self, log_entries: List[Dict]) -> Dict[str, Any]:
        """Compute basic statistics without AI."""
        if not log_entries:
            return {"total_entries": 0}

        error_count = sum(1 for e in log_entries if "error" in str(e).lower())
        warning_count = sum(1 for e in log_entries if "warn" in str(e).lower())

        # Extract unique services
        services = set()
        for entry in log_entries:
            if "service" in entry:
                services.add(entry["service"])

        return {
            "total_entries": len(log_entries),
            "error_count": error_count,
            "warning_count": warning_count,
            "services": list(services),
            "time_range": {
                "start": log_entries[0].get("timestamp") if log_entries else None,
                "end": log_entries[-1].get("timestamp") if log_entries else None
            }
        }


class StreamDegradationHandler(DegradationHandler):
    """
    Degradation handler for streaming responses.

    When streaming is disabled:
    - Returns complete response instead of stream
    - Adds degradation notice
    """

    @property
    def degradation_message(self) -> str:
        return "Streaming temporarily disabled, returning complete response"

    def handle(
        self,
        response_content: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Return non-streaming response.

        Args:
            response_content: Content that would have been streamed

        Returns:
            Complete response with degradation notice
        """
        logger.info("Streaming degraded, returning complete response")

        return {
            "status": "degraded",
            "message": self.degradation_message,
            "streaming": False,
            "content": response_content,
            "events": [
                {"event": "message", "data": response_content},
                {"event": "done", "data": {"degraded": True}}
            ]
        }


class ModelDegradationHandler(DegradationHandler):
    """
    Degradation handler when a specific model is unavailable.

    Falls back to a simpler/faster model.
    """

    def __init__(self, fallback_model: str = "ollama:qwen3:4b"):
        self.fallback_model = fallback_model

    @property
    def degradation_message(self) -> str:
        return f"Primary model unavailable, using fallback: {self.fallback_model}"

    def handle(
        self,
        prompt: str = "",
        original_model: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Return info about fallback model.

        The actual model call should be made by the caller using
        the fallback model specified here.
        """
        logger.info(f"Model degraded from {original_model} to {self.fallback_model}")

        return {
            "status": "degraded",
            "message": self.degradation_message,
            "original_model": original_model,
            "fallback_model": self.fallback_model,
            "use_model": self.fallback_model
        }


class VerificationDegradationHandler(DegradationHandler):
    """
    Degradation handler for verification agent.

    When verification is disabled:
    - Skips verification step
    - Returns unverified analysis
    """

    @property
    def degradation_message(self) -> str:
        return "Verification step skipped"

    def handle(
        self,
        analysis_result: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Return unverified analysis.

        Args:
            analysis_result: Analysis to be verified

        Returns:
            Analysis marked as unverified
        """
        logger.info("Verification degraded, returning unverified result")

        return {
            "status": "degraded",
            "message": self.degradation_message,
            "verified": False,
            "verification_skipped": True,
            "analysis": analysis_result,
            "warning": "Results have not been verified. Review with caution."
        }
```

### File: `app/features/decorators.py`

```python
"""
Decorators for feature flag checks.
"""

import functools
import logging
from typing import Any, Callable, Optional, TypeVar

from app.features.ai_feature_controller import (
    AIFeatureController,
    FeatureContext,
    get_feature_controller
)

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


def require_feature(
    feature: str,
    fallback: Optional[Callable[..., Any]] = None
) -> Callable[[F], F]:
    """
    Decorator to require a feature flag to be enabled.

    Args:
        feature: Feature name to check
        fallback: Optional fallback function to call if disabled

    Usage:
        @require_feature("rag")
        def search_with_rag(query: str):
            return rag_pipeline.search(query)

        @require_feature("analysis", fallback=basic_analysis)
        def analyze_trace(trace_id: str):
            return ai_analysis(trace_id)
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            controller = get_feature_controller()

            # Extract context if provided
            context = kwargs.pop('feature_context', None)

            if controller.is_enabled(feature, context):
                return func(*args, **kwargs)
            else:
                logger.info(f"Feature '{feature}' disabled, using fallback")

                if fallback:
                    return fallback(*args, **kwargs)
                else:
                    return controller.get_degraded_response(feature, *args, **kwargs)

        return wrapper
    return decorator


def require_ai(func: F) -> F:
    """
    Decorator to require AI master switch to be enabled.

    Usage:
        @require_ai
        def generate_response(prompt: str):
            return llm.generate(prompt)
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        controller = get_feature_controller()

        context = kwargs.pop('feature_context', None)

        if controller.is_ai_enabled(context):
            return func(*args, **kwargs)
        else:
            logger.warning("AI master switch is OFF, blocking request")
            return {
                "status": "disabled",
                "message": "AI features are currently disabled",
                "error_code": "AI_DISABLED"
            }

    return wrapper


def feature_percentage(
    feature: str,
    percentage_key: str = "percentage"
) -> Callable[[F], F]:
    """
    Decorator for percentage-based rollouts.

    The feature flag value should be an integer 0-100 representing
    the percentage of requests that should use the new feature.

    Usage:
        @feature_percentage("new_model_rollout")
        def use_new_model():
            return new_model.generate()
    """
    import random

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            controller = get_feature_controller()

            # Get rollout percentage
            percentage = controller.get_feature_value(feature, default=0)

            if random.randint(1, 100) <= percentage:
                logger.debug(f"Percentage rollout: using feature '{feature}'")
                return func(*args, **kwargs)
            else:
                logger.debug(f"Percentage rollout: skipping feature '{feature}'")
                return controller.get_degraded_response(feature, *args, **kwargs)

        return wrapper
    return decorator
```

---

## API Endpoints

### File: `app/api/feature_routes.py`

```python
"""
FastAPI routes for feature flag management.
"""

from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.features.ai_feature_controller import (
    AIFeatureController,
    FeatureContext,
    get_feature_controller
)

router = APIRouter(prefix="/api/features", tags=["features"])


class FeatureCheckRequest(BaseModel):
    feature: str
    user_id: Optional[str] = None
    traits: Optional[Dict[str, Any]] = None


class FeatureStateResponse(BaseModel):
    feature: str
    enabled: bool
    value: Any = None
    state: str


@router.get("/status")
def get_feature_status():
    """
    Get status of all features.

    Returns current state of all feature flags.
    """
    controller = get_feature_controller()
    states = controller.get_all_feature_states()

    return {
        "flagsmith_enabled": controller.enabled,
        "features": states
    }


@router.get("/check/{feature}")
def check_feature(
    feature: str,
    user_id: Optional[str] = Query(default=None)
) -> FeatureStateResponse:
    """
    Check if a specific feature is enabled.

    Args:
        feature: Feature name
        user_id: Optional user ID for targeting
    """
    controller = get_feature_controller()

    context = FeatureContext(user_id=user_id) if user_id else None

    enabled = controller.is_enabled(feature, context)
    value = controller.get_feature_value(feature, context=context)

    return FeatureStateResponse(
        feature=feature,
        enabled=enabled,
        value=value,
        state="enabled" if enabled else "disabled"
    )


@router.post("/check")
def check_feature_with_context(request: FeatureCheckRequest) -> FeatureStateResponse:
    """
    Check feature with full context.

    Allows checking with user traits for segment targeting.
    """
    controller = get_feature_controller()

    context = FeatureContext(
        user_id=request.user_id,
        traits=request.traits
    )

    enabled = controller.is_enabled(request.feature, context)
    value = controller.get_feature_value(request.feature, context=context)

    return FeatureStateResponse(
        feature=request.feature,
        enabled=enabled,
        value=value,
        state="enabled" if enabled else "disabled"
    )


@router.post("/refresh")
def refresh_flags():
    """
    Force refresh of feature flags from Flagsmith.
    """
    controller = get_feature_controller()
    controller.refresh_flags()

    return {"status": "refreshed"}


@router.get("/health")
def feature_health():
    """
    Health check for feature flag system.
    """
    controller = get_feature_controller()

    try:
        # Try to fetch a flag
        ai_enabled = controller.is_ai_enabled()

        return {
            "status": "healthy",
            "flagsmith_enabled": controller.enabled,
            "ai_master_switch": ai_enabled
        }
    except Exception as e:
        return {
            "status": "degraded",
            "error": str(e),
            "flagsmith_enabled": controller.enabled
        }
```

---

## Integration Examples

### Updated Orchestrator

```python
# app/orchestrator.py (excerpt)

from app.features import get_feature_controller
from app.features.decorators import require_ai, require_feature


class Orchestrator:

    def __init__(self):
        self.feature_controller = get_feature_controller()

    @require_ai
    async def process_request(self, request: ChatRequest):
        """Process a chat request with feature flag checks."""

        # Check individual features
        if self.feature_controller.is_enabled("rag"):
            context = await self._get_rag_context(request)
        else:
            context = self.feature_controller.get_degraded_response(
                "rag", query=request.message
            )

        # Analysis with fallback
        if self.feature_controller.is_enabled("analysis"):
            analysis = await self._analyze_traces(traces)
        else:
            analysis = self.feature_controller.get_degraded_response(
                "analysis", trace_id=trace_id, log_entries=entries
            )

        return response

    @require_feature("streaming")
    async def stream_response(self, session_id: str):
        """Stream response with feature flag check."""
        # This will automatically use degradation if streaming disabled
        async for event in self._generate_events():
            yield event
```

### Updated Verify Agent

```python
# app/agents/verify_agent.py (excerpt)

from app.features import get_feature_controller


class RelevanceAnalyzerAgent:

    def __init__(self):
        self.feature_controller = get_feature_controller()

    def analyze_relevance(self, trace_data: dict) -> dict:
        """Analyze trace relevance with feature checks."""

        # Use RAG if enabled
        rag_context = self.feature_controller.execute_with_fallback(
            "rag",
            self._get_rag_context,
            trace_data["query"],
            trace_data["domain"]
        )

        # Use verification if enabled
        if self.feature_controller.is_enabled("verification"):
            result = self._verify_with_llm(trace_data, rag_context)
        else:
            result = self.feature_controller.get_degraded_response(
                "verification",
                analysis_result={"trace_data": trace_data}
            )

        return result
```

---

## File-by-File Implementation Steps

| Step | File | Action | Description |
|------|------|--------|-------------|
| 1 | `requirements.txt` | MODIFY | Add `flagsmith>=3.5.0` |
| 2 | `docker-compose.yml` | MODIFY | Add Flagsmith services |
| 3 | `app/features/__init__.py` | CREATE | Package init |
| 4 | `app/features/ai_feature_controller.py` | CREATE | Main controller |
| 5 | `app/features/degradation_handlers.py` | CREATE | Fallback handlers |
| 6 | `app/features/decorators.py` | CREATE | Convenience decorators |
| 7 | `app/api/feature_routes.py` | CREATE | REST API |
| 8 | `app/main.py` | MODIFY | Register feature routes |
| 9 | `config/settings.toml` | MODIFY | Add Flagsmith config |
| 10 | `app/orchestrator.py` | MODIFY | Integrate feature checks |
| 11 | `app/agents/verify_agent.py` | MODIFY | Add feature checks |
| 12 | `scripts/init_flagsmith.py` | CREATE | Initialize flags |

---

## Dependencies to Add

```txt
# requirements.txt additions
flagsmith>=3.5.0
```

---

## Testing Strategy

### Unit Tests

```python
# tests/unit/test_feature_controller.py

import pytest
from unittest.mock import MagicMock, patch
from app.features.ai_feature_controller import AIFeatureController, FeatureContext


class TestAIFeatureController:

    @pytest.fixture
    def mock_flagsmith(self):
        with patch('app.features.ai_feature_controller.Flagsmith') as mock:
            mock_client = MagicMock()
            mock_flags = MagicMock()
            mock_flags.is_feature_enabled.return_value = True
            mock_flags.get_feature_value.return_value = 100
            mock_client.get_environment_flags.return_value = mock_flags
            mock.return_value = mock_client
            yield mock_client

    def test_master_switch_enabled(self, mock_flagsmith):
        controller = AIFeatureController()
        assert controller.is_ai_enabled() is True

    def test_master_switch_disabled(self, mock_flagsmith):
        mock_flags = mock_flagsmith.get_environment_flags.return_value
        mock_flags.is_feature_enabled.return_value = False

        controller = AIFeatureController()
        assert controller.is_ai_enabled() is False

    def test_feature_blocked_by_master(self, mock_flagsmith):
        mock_flags = mock_flagsmith.get_environment_flags.return_value

        def side_effect(flag_name):
            if flag_name == "ai_master_switch":
                return False
            return True

        mock_flags.is_feature_enabled.side_effect = side_effect

        controller = AIFeatureController()
        assert controller.is_enabled("rag") is False

    def test_degradation_handler_called(self, mock_flagsmith):
        mock_flags = mock_flagsmith.get_environment_flags.return_value
        mock_flags.is_feature_enabled.return_value = False

        controller = AIFeatureController()
        result = controller.get_degraded_response("rag", query="test")

        assert result["status"] == "degraded"


class TestDegradationHandlers:

    def test_rag_degradation(self):
        from app.features.degradation_handlers import RAGDegradationHandler

        handler = RAGDegradationHandler()
        result = handler.handle(query="test query")

        assert result["status"] == "degraded"
        assert result["results"] == []

    def test_analysis_degradation(self):
        from app.features.degradation_handlers import AnalysisDegradationHandler

        handler = AnalysisDegradationHandler()
        log_entries = [
            {"message": "error occurred", "level": "ERROR"},
            {"message": "warning issued", "level": "WARN"}
        ]

        result = handler.handle(trace_id="trace123", log_entries=log_entries)

        assert result["statistics"]["error_count"] == 1
        assert result["statistics"]["warning_count"] == 1
```

### Integration Tests

```python
# tests/integration/test_feature_api.py

import pytest
from fastapi.testclient import TestClient
from app.main import app


class TestFeatureAPI:

    @pytest.fixture
    def client(self):
        return TestClient(app)

    def test_get_feature_status(self, client):
        response = client.get("/api/features/status")
        assert response.status_code == 200
        assert "features" in response.json()

    def test_check_feature(self, client):
        response = client.get("/api/features/check/rag")
        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data
        assert "feature" in data

    def test_refresh_flags(self, client):
        response = client.post("/api/features/refresh")
        assert response.status_code == 200
        assert response.json()["status"] == "refreshed"
```

---

## Critical Files Reference

| File | Lines | Purpose |
|------|-------|---------|
| `app/features/ai_feature_controller.py` | All | NEW - Central controller |
| `app/features/degradation_handlers.py` | All | NEW - Fallback handlers |
| `app/features/decorators.py` | All | NEW - Convenience decorators |
| `app/api/feature_routes.py` | All | NEW - REST API |
| `docker-compose.yml` | Add Flagsmith | Flagsmith service |
| `app/orchestrator.py` | Integrate | Add feature checks |

---

## Acceptance Criteria

| Criterion | Verification Procedure |
|-----------|------------------------|
| Flagsmith running | Access http://localhost:8001 |
| Master switch works | Disable ai_master_switch, verify all AI blocked |
| Per-feature flags work | Disable rag_enabled, verify RAG returns degraded |
| Degradation handlers work | Disable feature, verify fallback response |
| User targeting works | Set trait, verify different flag value |
| Percentage rollout works | Set 50%, verify ~50% get feature |
| API endpoints work | All /api/features/* return 200 |
| Decorators work | Use @require_feature, verify behavior |
