# Code Review: DB Configuration Phases 3-5

**Date:** 2025-01-12
**Author:** Claude Code
**Scope:** Wiring database-backed configuration into runtime components

---

## Overview

This code review covers the changes made to complete Phases 3-5 of the database configuration feature. The goal was to move hardcoded configuration values to the database, allowing runtime configuration without code changes.

---

## Files Modified

### 1. `app/tools/loki/loki_query_builder.py`

**Change:** Loki base URL now loaded from database settings

**Before:**
```python
BASE_URL = "https://loki-gateway.local.fintech23.xyz/loki/api/v1/query_range"
```

**After:**
```python
def _get_loki_base_url() -> str:
    """Get Loki base URL from DB settings or fallback to default."""
    try:
        from app.services.config_service import get_setting
        return get_setting("loki", "base_url", "https://loki-gateway.local.fintech23.xyz/loki/api/v1/query_range")
    except Exception:
        return "https://loki-gateway.local.fintech23.xyz/loki/api/v1/query_range"

BASE_URL = _get_loki_base_url()
```

**Rationale:**
- Allows changing Loki endpoint without code deployment
- Graceful fallback if DB unavailable
- Import inside function to avoid circular imports at module load

---

### 2. `app/agents/verify_agent.py`

#### Change 1: Relevance thresholds from database

**Before:**
```python
self.HIGHLY_RELEVANT_THRESHOLD = 80
self.RELEVANT_THRESHOLD = 60
self.POTENTIALLY_RELEVANT_THRESHOLD = 40
```

**After:**
```python
from app.services.config_service import get_setting
self.HIGHLY_RELEVANT_THRESHOLD = get_setting("thresholds", "highly_relevant", 80)
self.RELEVANT_THRESHOLD = get_setting("thresholds", "relevant", 60)
self.POTENTIALLY_RELEVANT_THRESHOLD = get_setting("thresholds", "potentially_relevant", 40)
```

#### Change 2: Output directory from database

**Before:**
```python
def __init__(self, client: LLMProvider, model: str, output_dir: str = "relevance_analysis", ...):
```

**After:**
```python
def __init__(self, client: LLMProvider, model: str, output_dir: str = None, ...):
    if output_dir is None:
        from app.services.config_service import get_setting
        output_dir = get_setting("paths", "verification_output", "app/verification_reports")
```

#### Change 3: RAGContextManager uses database for context rules

**Before:**
```python
class RAGContextManager:
    def load_context_rules(self):
        """Load context rules from CSV file"""
        # Only CSV loading
```

**After:**
```python
class RAGContextManager:
    def load_context_rules(self):
        """Load context rules from database (if enabled) or CSV file fallback."""
        if settings.USE_DB_SETTINGS:
            try:
                self._load_from_database()
                if self.rules:
                    logger.info(f"Loaded {len(self.rules)} context rules from database")
                    return
            except Exception as e:
                logger.warning(f"Failed to load context rules from database, falling back to CSV: {e}")
        self._load_from_csv()

    def _load_from_database(self):
        """Load context rules from database."""
        from app.db.session import get_db_session
        from app.models.context_rule import ContextRule as DBContextRule
        # ... loads from context_rules table
```

**Rationale:**
- Feature flag controlled (`USE_DB_SETTINGS`)
- Graceful CSV fallback
- No breaking changes to existing deployments

---

### 3. `app/orchestrator.py`

#### Change 1: Output directories from database

**Before:**
```python
def __init__(self, llm_provider: LLMProvider, model: str, log_base_dir: str = "./data"):
    self.analyze_agent = AnalyzeAgent(llm_provider, model, output_dir="app/comprehensive_analysis")
    self.verify_agent = RelevanceAnalyzerAgent(llm_provider, model, output_dir="app/verification_reports")
```

**After:**
```python
def __init__(self, llm_provider: LLMProvider, model: str, log_base_dir: str = None):
    analysis_output = get_setting("paths", "analysis_output", "app/comprehensive_analysis")
    verification_output = get_setting("paths", "verification_output", "app/verification_reports")
    self.analyze_agent = AnalyzeAgent(llm_provider, model, output_dir=analysis_output)
    self.verify_agent = RelevanceAnalyzerAgent(llm_provider, model, output_dir=verification_output)
```

#### Change 2: Loki namespace from project service

**Before:**
```python
ctx.unique_filename = download_logs_cached(
    filters={"service_namespace": ctx.project.lower()},
    ...
)
```

**After:**
```python
loki_namespace = get_loki_namespace(ctx.project, ctx.env or "prod")
logger.debug(f"Using Loki namespace: {loki_namespace} for project: {ctx.project}")

ctx.unique_filename = download_logs_cached(
    filters={"service_namespace": loki_namespace},
    ...
)
```

#### Change 3: File-based log path from project service

**Before:**
```python
def _step2_search_logs_file_based(self, ctx: PipelineContext) -> Dict[str, Any]:
    ctx.log_files = self.file_searcher.find_and_verify(ctx.params)
```

**After:**
```python
def _step2_search_logs_file_based(self, ctx: PipelineContext) -> Dict[str, Any]:
    project_service = get_project_service()
    log_base_path = project_service.get_log_base_path(ctx.project, ctx.env or "prod")

    if log_base_path:
        file_searcher = FileSearcher(Path(log_base_path), self.file_searcher.client, self.file_searcher.model)
        ctx.log_files = file_searcher.find_and_verify(ctx.params)
    else:
        ctx.log_files = self.file_searcher.find_and_verify(ctx.params)
```

#### Change 4: Negate keys from database

**Before:**
```python
def _load_negate_keys(self) -> List[str]:
    """Load negation keys from CSV configuration file."""
    # Only CSV loading
```

**After:**
```python
def _load_negate_keys(self) -> List[str]:
    """Load negation keys from database (if enabled) or CSV configuration file."""
    if settings.USE_DB_SETTINGS:
        try:
            negate_keys = self._load_negate_keys_from_db()
            if negate_keys:
                return negate_keys
        except Exception as e:
            logger.warning(f"Failed to load negate keys from database, falling back to CSV: {e}")
    return self._load_negate_keys_from_csv()

def _load_negate_keys_from_db(self) -> List[str]:
    """Load negation keys from app_settings table."""
    # Loads from app_settings where category='negate_rules', key='terms'
```

#### Change 5: Fixed negate keys CSV path

**Before:**
```python
NEGATE_RULES_PATH = "app_settings/negate_keys.csv"
```

**After:**
```python
NEGATE_RULES_PATH = "app/app_settings/negate_keys.csv"
```

---

## New Files Created

### 1. `alembic/versions/seed_negate_rules.py`

Seeds default negate terms in `app_settings` table:

```python
DEFAULT_NEGATE_TERMS = [
    "processMfsStatusUpdateInvocationEvent",
    "MFS_TRANSFER_STATUS_UPDATE_SCHEDULER_INVOCATION_TOPIC",
    "HEARTBEAT",
    "HEALTH_CHECK",
    # ... more terms
]
```

Stored as JSON array in `app_settings.negate_rules.terms`.

### 2. `alembic/versions/seed_default_settings.py`

Seeds default configuration values:

| Category | Key | Default Value |
|----------|-----|---------------|
| loki | base_url | https://loki-gateway.local.fintech23.xyz/... |
| thresholds | highly_relevant | 80 |
| thresholds | relevant | 60 |
| thresholds | potentially_relevant | 40 |
| thresholds | batch_size | 10 |
| paths | analysis_output | app/comprehensive_analysis |
| paths | verification_output | app/verification_reports |

---

## Import Changes

Added to `app/orchestrator.py`:
```python
from app.services.project_service import is_file_based, is_loki_based, get_loki_namespace, get_project_service
from app.services.config_service import get_setting
```

---

## Feature Flags

All changes are controlled by existing feature flags:

| Flag | Purpose |
|------|---------|
| `USE_DB_SETTINGS` | Enable DB-backed app settings (thresholds, paths, negate keys, context rules) |
| `USE_DB_PROJECTS` | Enable DB-backed project configuration (Loki namespace, log paths) |

**Default behavior:** Both flags default to `false`, so existing deployments are unaffected.

---

## Testing

All 251 tests pass after changes:

```
===================== 251 passed, 519 warnings in 19.45s ======================
```

No new tests were added for these configuration changes as they are covered by existing integration tests that use the fallback defaults.

---

## Migration Path

1. Deploy code changes (no impact - uses defaults)
2. Run migrations: `uv run alembic upgrade head`
3. Enable feature flags in `.env`:
   ```
   USE_DB_SETTINGS=true
   USE_DB_PROJECTS=true
   ```
4. Restart application

---

## Potential Issues

1. **Circular imports:** Avoided by using lazy imports inside functions
2. **DB unavailability:** All changes have graceful fallbacks
3. **Cache invalidation:** Settings use TTL cache; changes take effect after cache expires or manual invalidation

---

## Recommendations

1. Consider adding admin API endpoints to modify settings at runtime
2. Add monitoring/alerting for settings cache hit rates
3. Document all configurable settings in a central location
