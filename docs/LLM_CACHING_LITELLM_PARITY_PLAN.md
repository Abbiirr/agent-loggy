# LLM Caching - LiteLLM Parity Implementation Plan

This document provides a comprehensive implementation plan to upgrade the existing LLM caching layer to achieve full LiteLLM parity.

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Gap Analysis vs LiteLLM](#gap-analysis-vs-litellm)
4. [Implementation Plan](#implementation-plan)
   - [Phase 1: Configuration Enhancements](#phase-1-configuration-enhancements)
   - [Phase 2: Cache Policy Schema Update](#phase-2-cache-policy-schema-update)
   - [Phase 3: Gateway Logic Updates](#phase-3-gateway-logic-updates)
   - [Phase 4: Admin Endpoint Enhancements](#phase-4-admin-endpoint-enhancements)
   - [Phase 5: Response Header Middleware](#phase-5-response-header-middleware)
   - [Phase 6: Dependency Updates](#phase-6-dependency-updates)
   - [Phase 7: Documentation Update](#phase-7-documentation-update)
   - [Phase 8: Tests](#phase-8-tests)
5. [File Change Summary](#file-change-summary)
6. [Migration Guide](#migration-guide)
7. [References](#references)

---

## Executive Summary

**Goal:** Upgrade the existing LLM caching layer to achieve full LiteLLM parity with:
- Config-driven controls (`mode`, `supported_call_types`)
- Default-off mode with `use_cache` opt-in
- Enhanced admin endpoints (round-trip ping, batch delete)
- Response header for cache key visibility
- Performance optimizations (orjson)

**Impact:** No breaking changes. All defaults preserve existing behavior.

**Estimated Scope:** 9 files to modify, ~300-400 lines of changes.

---

## Current State Analysis

### Architecture Overview

The codebase implements a dual-layer LLM response cache:

```
┌─────────────────────────────────────────────────────────────────┐
│                        LLMCacheGateway                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────┐    ┌───────────────┐    ┌────────────────┐  │
│  │  L1 Cache     │    │  L2 Cache     │    │  SingleFlight  │  │
│  │ (LRU+TTL)     │◄──►│  (Redis)      │◄──►│  (Stampede)    │  │
│  │ In-Memory     │    │  Optional     │    │  Protection    │  │
│  └───────────────┘    └───────────────┘    └────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  Used by: ParametersAgent, AnalyzeAgent, RelevanceAnalyzerAgent │
└─────────────────────────────────────────────────────────────────┘
```

### Current Files

| File | Purpose | Lines |
|------|---------|-------|
| `app/services/llm_gateway/gateway.py` | Core cache gateway | 552 |
| `app/schemas/CachePolicy.py` | Pydantic request schema | 16 |
| `app/routers/cache_admin.py` | Admin REST endpoints | 43 |
| `app/config.py` | Environment settings | 51 |

### Current Configuration (app/config.py:19-33)

```python
# --- LLM cache / gateway ---
LLM_CACHE_ENABLED: bool = True
LLM_CACHE_NAMESPACE: str = "default"
LLM_CACHE_L1_MAX_ENTRIES: int = 10_000
LLM_CACHE_L1_TTL_SECONDS: int = 60

# Enable shared (cross-worker/pod) cache with Redis
LLM_CACHE_L2_ENABLED: bool = False
LLM_CACHE_REDIS_URL: Optional[str] = None
LLM_CACHE_L2_AUTO_ENABLE: bool = True

# Explicit invalidation knobs
LLM_GATEWAY_VERSION: str = "v1"
PROMPT_VERSION: str = "v1"
```

### Current Cache Policy (app/schemas/CachePolicy.py)

```python
class CachePolicyModel(BaseModel):
    enabled: bool = True          # Enable/disable caching
    no_cache: bool = False        # Skip cache lookup (force refresh)
    no_store: bool = False        # Don't store result
    ttl_seconds: Optional[int]    # Per-request TTL override
    s_maxage_seconds: Optional[int]  # Staleness threshold
    namespace: Optional[str]      # Per-request namespace
```

### Current Admin Endpoints (app/routers/cache_admin.py)

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/cache/ping` | GET | Check L1/L2 connectivity (ping only, no round-trip) |
| `/cache/stats` | GET | Full cache statistics |
| `/cache/delete` | POST | Delete single key: `{"key": "..."}` |
| `/cache/clear-l1` | POST | Clear entire L1 cache |

### Cache Types Used by Agents

| Agent | Cache Type | Default TTL |
|-------|------------|-------------|
| `ParametersAgent.run()` | `parameter_extraction` | 7200s (2h) |
| `AnalyzeAgent._analyze_single_trace()` | `trace_analysis` | 14400s (4h) |
| `AnalyzeAgent._analyze_single_trace_from_entries()` | `trace_entries_analysis` | 14400s (4h) |
| `AnalyzeAgent._assess_overall_quality()` | `quality_assessment` | 7200s (2h) |
| `RelevanceAnalyzerAgent._analyze_relevance_with_rag()` | `relevance_analysis` | 14400s (4h) |
| `PlanningAgent.plan()` | `planning` | 600s (10m) |

---

## Gap Analysis vs LiteLLM

| Feature | Current | LiteLLM | Gap | Priority |
|---------|---------|---------|-----|----------|
| Mode (default_on/off) | Always on | `mode: default_on\|default_off` | Missing | High |
| `use_cache` opt-in | No | Yes (for default_off mode) | Missing | High |
| `supported_call_types` | Implicit | Explicit allowlist | Missing | Medium |
| `/cache/ping` round-trip | Ping only | Set/get test with latency | Missing | Medium |
| `/cache/delete` batch | Single key | Multiple keys | Missing | Medium |
| Response header | No | `x-litellm-cache-key` | Missing | Low |
| JSON serialization | stdlib json | orjson | Performance gap | Medium |
| Disk cache | No | Yes | Out of scope | - |
| Semantic cache | No | Yes (redis-semantic) | Out of scope | - |
| S3/GCS cache | No | Yes | Out of scope | - |

### LiteLLM Features Reference

From [LiteLLM Proxy Caching](https://docs.litellm.ai/docs/proxy/caching):

```yaml
# LiteLLM config.yaml example
litellm_settings:
  cache: True
  cache_params:
    type: redis
    ttl: 600
    namespace: "myapp"
    mode: "default_off"  # Requires use_cache opt-in
    supported_call_types: ["completion", "embedding"]
```

Per-request controls:
```json
{
  "cache": {
    "use-cache": true,      // Opt-in (required when mode=default_off)
    "no-cache": false,      // Bypass lookup
    "no-store": false,      // Don't store
    "ttl": 3600,            // TTL override
    "s-maxage": 1800,       // Staleness threshold
    "namespace": "user123"  // Namespace override
  }
}
```

---

## Implementation Plan

### Phase 1: Configuration Enhancements

**File:** `app/config.py`

**Changes:** Add new settings after line 33

```python
# --- LLM cache / gateway ---
LLM_CACHE_ENABLED: bool = True
LLM_CACHE_NAMESPACE: str = "default"
LLM_CACHE_L1_MAX_ENTRIES: int = 10_000
LLM_CACHE_L1_TTL_SECONDS: int = 60

# Enable shared (cross-worker/pod) cache with Redis
LLM_CACHE_L2_ENABLED: bool = False
LLM_CACHE_REDIS_URL: Optional[str] = None
LLM_CACHE_L2_AUTO_ENABLE: bool = True

# Explicit invalidation knobs
LLM_GATEWAY_VERSION: str = "v1"
PROMPT_VERSION: str = "v1"

# ─── NEW: LiteLLM-style cache controls ────────────────────────
# Cache mode: "default_on" (cache by default) or "default_off" (require use_cache opt-in)
LLM_CACHE_MODE: str = "default_on"

# Allowlist of cache types that are eligible for caching.
# If empty, all types are allowed. Set to specific types to restrict.
LLM_CACHE_SUPPORTED_CALL_TYPES: str = ""  # Comma-separated, e.g. "parameter_extraction,trace_analysis"
# Note: Using str instead of list for env var compatibility. Will parse to list.
```

**Implementation Details:**

Add helper property to parse `LLM_CACHE_SUPPORTED_CALL_TYPES`:

```python
@property
def llm_cache_supported_call_types_list(self) -> list[str]:
    """Parse comma-separated supported_call_types into list."""
    raw = self.LLM_CACHE_SUPPORTED_CALL_TYPES.strip()
    if not raw:
        return []  # Empty = all types allowed
    return [t.strip() for t in raw.split(",") if t.strip()]
```

---

### Phase 2: Cache Policy Schema Update

**File:** `app/schemas/CachePolicy.py`

**Full Updated File:**

```python
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class CachePolicyModel(BaseModel):
    """Per-request cache policy controls (LiteLLM-compatible).

    Attributes:
        enabled: Global enable/disable for this request (default: True)
        use_cache: Opt-in flag for default_off mode (default: False)
                   When LLM_CACHE_MODE="default_off", this must be True to use cache.
        no_cache: Skip cache lookup, force fresh computation (default: False)
        no_store: Don't store the result in cache (default: False)
        ttl_seconds: Override default TTL for this response (default: None = use default)
        s_maxage_seconds: Only accept cached values younger than this (default: None)
        namespace: Override cache namespace for this request (default: None = use global)
    """
    enabled: bool = True
    use_cache: bool = False  # NEW: Required for default_off mode
    no_cache: bool = False
    no_store: bool = False
    ttl_seconds: Optional[int] = Field(default=None, ge=1)
    s_maxage_seconds: Optional[int] = Field(default=None, ge=1)
    namespace: Optional[str] = None
```

---

### Phase 3: Gateway Logic Updates

**File:** `app/services/llm_gateway/gateway.py`

#### 3.1 Replace stdlib json with orjson

**At line 4, replace:**
```python
import json
```

**With:**
```python
import orjson
```

**At line 21-22, replace `_canonical_json` function:**
```python
def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
```

**With:**
```python
def _canonical_json(obj: Any) -> bytes:
    """Canonical JSON serialization using orjson for performance."""
    return orjson.dumps(obj, option=orjson.OPT_SORT_KEYS)
```

**At line 25-26, update `_sha256_hex` to accept bytes:**
```python
def _sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()
```

**At line 364-366, update `_encode_envelope`:**
```python
def _encode_envelope(self, value: Any) -> bytes:
    envelope = {"created_at": _now_s(), "value": value}
    return orjson.dumps(envelope)  # Changed from _canonical_json
```

**At line 368-371, update `_decode_envelope`:**
```python
def _decode_envelope(self, payload: bytes) -> tuple[float, Any]:
    obj = orjson.loads(payload)  # Changed from json.loads
    created_at = float(obj.get("created_at") or 0.0)
    return created_at, obj.get("value")
```

#### 3.2 Update CachePolicy dataclass

**At lines 87-107, add `use_cache` field:**

```python
@dataclass(frozen=True)
class CachePolicy:
    enabled: bool = True
    use_cache: bool = False  # NEW: Opt-in for default_off mode
    no_cache: bool = False
    no_store: bool = False
    ttl_seconds: Optional[int] = None
    s_maxage_seconds: Optional[int] = None
    namespace: Optional[str] = None

    @staticmethod
    def from_dict(d: Optional[dict[str, Any]]) -> "CachePolicy":
        if not d:
            return CachePolicy()
        return CachePolicy(
            enabled=bool(d.get("enabled", True)),
            use_cache=bool(d.get("use_cache", False)),  # NEW
            no_cache=bool(d.get("no_cache", False)),
            no_store=bool(d.get("no_store", False)),
            ttl_seconds=d.get("ttl_seconds"),
            s_maxage_seconds=d.get("s_maxage_seconds"),
            namespace=d.get("namespace"),
        )
```

#### 3.3 Add new diagnostic status values

**At line 112, update `CacheDiagnostics` docstring:**

```python
@dataclass(frozen=True)
class CacheDiagnostics:
    status: str  # HIT_L1 | HIT_L2 | MISS | BYPASS | BYPASS_DISABLED | BYPASS_DEFAULT_OFF | BYPASS_UNSUPPORTED_TYPE | COALESCED
    key_prefix: str
    key: Optional[str] = None  # NEW: Full cache key for header
    layer: Optional[str] = None  # l1|l2
    ttl_seconds: Optional[int] = None
    waited: bool = False
```

#### 3.4 Update `cached()` method with mode and call type checks

**At line 378-396, add checks at the start of the method:**

```python
def cached(
    self,
    *,
    cache_type: str,
    model: str,
    messages: list[dict[str, Any]],
    options: Optional[dict[str, Any]],
    default_ttl_seconds: int,
    policy: Optional[CachePolicy],
    compute: Callable[[], CacheableValue],
) -> tuple[Any, CacheDiagnostics]:
    self.calls += 1
    pol = policy or CachePolicy()

    # ─── NEW: Check supported_call_types allowlist ───────────────
    supported_types = settings.llm_cache_supported_call_types_list
    if supported_types and cache_type not in supported_types:
        # Call type not in allowlist - bypass cache
        self.bypasses += 1
        v = compute()
        return v.value, CacheDiagnostics(
            status="BYPASS_UNSUPPORTED_TYPE",
            key_prefix="",
            ttl_seconds=pol.ttl_seconds,
        )

    # ─── NEW: Check cache mode (default_on vs default_off) ───────
    cache_mode = getattr(settings, "LLM_CACHE_MODE", "default_on")
    if cache_mode == "default_off" and not pol.use_cache:
        # Default-off mode requires explicit opt-in via use_cache=True
        self.bypasses += 1
        v = compute()
        return v.value, CacheDiagnostics(
            status="BYPASS_DEFAULT_OFF",
            key_prefix="",
            ttl_seconds=pol.ttl_seconds,
        )

    # ─── Existing: Check enabled flag ────────────────────────────
    if not self.enabled or not pol.enabled:
        self.bypasses += 1
        v = compute()
        return v.value, CacheDiagnostics(
            status="BYPASS_DISABLED",
            key_prefix="",
            ttl_seconds=pol.ttl_seconds,
        )

    # ... rest of existing method ...
```

#### 3.5 Store full cache key in diagnostics for header

**At line 409, after generating the key, include it in diagnostics:**

```python
key = make_cache_key(
    cache_type=cache_type,
    namespace=namespace,
    model=model,
    messages=messages,
    options=options,
    gateway_version=self.gateway_version,
    prompt_version=self.prompt_version,
)
key_prefix = key.split(":")[-1][:12]

# Store full key for response header (NEW)
full_key = key
```

**Update all `CacheDiagnostics` return statements to include `key=full_key`:**

```python
return value, CacheDiagnostics(
    status="HIT_L1",
    key_prefix=key_prefix,
    key=full_key,  # NEW
    layer="l1",
    ttl_seconds=ttl,
)
```

#### 3.6 Update `from_settings()` to load new config

**At line 317-340, add new settings:**

```python
@staticmethod
def from_settings() -> "LLMCacheGateway":
    enabled = bool(getattr(settings, "LLM_CACHE_ENABLED", True))
    namespace = getattr(settings, "LLM_CACHE_NAMESPACE", "default")
    gateway_version = getattr(settings, "LLM_GATEWAY_VERSION", "v1")
    prompt_version = getattr(settings, "PROMPT_VERSION", "v1")

    # NEW: Load mode setting
    cache_mode = getattr(settings, "LLM_CACHE_MODE", "default_on")

    l1_max_entries = int(getattr(settings, "LLM_CACHE_L1_MAX_ENTRIES", 10_000))
    l1_ttl_seconds = int(getattr(settings, "LLM_CACHE_L1_TTL_SECONDS", 60))

    redis_url = getattr(settings, "LLM_CACHE_REDIS_URL", None)
    l2_enabled = bool(getattr(settings, "LLM_CACHE_L2_ENABLED", False))
    l2_auto_enable = bool(getattr(settings, "LLM_CACHE_L2_AUTO_ENABLE", True))

    return LLMCacheGateway(
        enabled=enabled,
        gateway_version=gateway_version,
        prompt_version=prompt_version,
        namespace=namespace,
        l1_max_entries=l1_max_entries,
        l1_ttl_seconds=l1_ttl_seconds,
        redis_url=redis_url,
        l2_enabled=l2_enabled,
        l2_auto_enable=l2_auto_enable,
    )
```

---

### Phase 4: Admin Endpoint Enhancements

**File:** `app/routers/cache_admin.py`

**Full Updated File:**

```python
# app/routers/cache_admin.py
from __future__ import annotations

import time
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.llm_gateway.gateway import get_llm_cache_gateway


router = APIRouter(prefix="/cache", tags=["cache"])


# ─── Request/Response Models ──────────────────────────────────────


class CacheDeleteRequest(BaseModel):
    """Request body for cache deletion.

    Supports both single key (legacy) and batch deletion (new).
    At least one of `key` or `keys` must be provided.
    """
    key: Optional[str] = None       # Legacy: single key
    keys: Optional[list[str]] = None  # New: batch of keys


class CacheDeleteResponse(BaseModel):
    """Response for cache deletion."""
    deleted: int      # Number of keys actually deleted
    requested: int    # Number of keys requested for deletion


class CachePingResponse(BaseModel):
    """Response for cache ping endpoint."""
    l1: dict
    l2: Optional[dict] = None


# ─── Endpoints ────────────────────────────────────────────────────


@router.get("/ping", response_model=CachePingResponse)
def cache_ping():
    """Check cache connectivity with round-trip test.

    - L1: Always healthy (in-memory)
    - L2: Performs SET/GET/DEL round-trip test with latency measurement

    Returns:
        {
            "l1": {"ok": true},
            "l2": {"healthy": true, "latency_ms": 1.23} or {"healthy": false, "error": "..."}
        }
    """
    gw = get_llm_cache_gateway()
    result = {"l1": {"ok": True}, "l2": None}

    # L2 round-trip test (if enabled)
    if gw.l2 is not None:
        try:
            test_key = f"__ping_test_{uuid4().hex[:8]}"
            test_value = b"ping_test_value"

            start = time.time()

            # SET
            gw.l2.set(test_key, test_value, ttl_seconds=10)

            # GET
            retrieved = gw.l2.get(test_key)

            # DEL
            gw.l2.delete(test_key)

            latency_ms = (time.time() - start) * 1000

            result["l2"] = {
                "healthy": retrieved == test_value,
                "latency_ms": round(latency_ms, 2),
            }
        except Exception as e:
            result["l2"] = {
                "healthy": False,
                "error": str(e),
            }
    else:
        # L2 not configured/connected
        result["l2"] = gw.ping_l2()  # Returns configuration status

    return result


@router.get("/stats")
def cache_stats():
    """Get comprehensive cache statistics.

    Returns counters for hits, misses, bypasses, evictions, etc.
    for both L1 and L2 cache layers.
    """
    gw = get_llm_cache_gateway()
    return gw.stats()


@router.post("/delete", response_model=CacheDeleteResponse)
def cache_delete(req: CacheDeleteRequest):
    """Delete one or more cache keys.

    Supports both legacy single-key and new batch formats:
    - Legacy: {"key": "llm:trace_analysis:abc123..."}
    - Batch: {"keys": ["llm:...", "llm:..."]}
    - Combined: {"key": "...", "keys": ["...", "..."]}

    Returns:
        {"deleted": <count>, "requested": <count>}
    """
    gw = get_llm_cache_gateway()

    # Collect all keys to delete
    keys_to_delete: list[str] = []
    if req.keys:
        keys_to_delete.extend(req.keys)
    if req.key:
        keys_to_delete.append(req.key)

    if not keys_to_delete:
        raise HTTPException(
            status_code=400,
            detail="Must provide 'key' or 'keys' in request body",
        )

    # Delete each key
    deleted_count = 0
    for key in keys_to_delete:
        result = gw.delete(key)
        if result.get("l1_deleted") or result.get("l2_deleted"):
            deleted_count += 1

    return CacheDeleteResponse(
        deleted=deleted_count,
        requested=len(keys_to_delete),
    )


@router.post("/clear-l1")
def cache_clear_l1():
    """Clear the entire L1 (in-memory) cache.

    Use with caution - this will invalidate all cached LLM responses
    in this process. Other workers/pods are not affected.
    """
    gw = get_llm_cache_gateway()
    gw.clear_l1()
    return {"ok": True}
```

---

### Phase 5: Response Header Middleware

**New File:** `app/middleware/cache_header.py`

```python
"""Middleware to add X-LLM-Cache-Key response header.

This middleware adds a header with the cache key when an LLM cache
was used during request processing. Useful for debugging and observability.
"""
from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# Context variable to pass cache key from gateway to middleware
# Set by LLMCacheGateway.cached() when cache is used
cache_key_var: ContextVar[Optional[str]] = ContextVar("llm_cache_key", default=None)


def set_cache_key_for_response(key: str) -> None:
    """Set the cache key to be included in the response header.

    Called from LLMCacheGateway.cached() when a cache operation occurs.
    """
    cache_key_var.set(key)


def get_cache_key_for_response() -> Optional[str]:
    """Get the cache key set during request processing."""
    return cache_key_var.get()


def clear_cache_key() -> None:
    """Clear the cache key context var."""
    cache_key_var.set(None)


class CacheHeaderMiddleware(BaseHTTPMiddleware):
    """Middleware that adds X-LLM-Cache-Key header to responses.

    When an LLM cache operation occurs during request handling,
    the cache key is stored in a context variable. This middleware
    reads that variable and adds it as a response header.

    Header: X-LLM-Cache-Key: llm:trace_analysis:abc123...
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Clear any stale cache key from previous request
        clear_cache_key()

        # Process the request
        response = await call_next(request)

        # Add cache key header if set
        cache_key = get_cache_key_for_response()
        if cache_key:
            response.headers["X-LLM-Cache-Key"] = cache_key

        return response
```

**Update:** `app/services/llm_gateway/gateway.py`

Add import at top:
```python
from app.middleware.cache_header import set_cache_key_for_response
```

In `cached()` method, after cache operations, set the context var:
```python
# After generating cache key
set_cache_key_for_response(key)
```

**Update:** `app/main.py`

Register the middleware after CORS middleware (around line 28):

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.middleware.cache_header import CacheHeaderMiddleware  # NEW
from app.routers import chat_router, analysis_router, files_router, cache_router
from app.startup import lifespan

# ... logging setup ...

app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# NEW: Add cache header middleware
app.add_middleware(CacheHeaderMiddleware)

# Include routers
# ...
```

---

### Phase 6: Dependency Updates

**File:** `pyproject.toml`

Add `orjson` to dependencies:

```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "orjson>=3.9.0",
]
```

**Install:**
```bash
uv add orjson
```

---

### Phase 7: Documentation Update

**File:** `docs/LLM_CACHING_REVIEW.md`

Update the following sections:

#### Update "Remaining gaps vs the LiteLLM plan" section:

```markdown
### Remaining gaps vs the LiteLLM plan

~~- No "mode: default_off + use_cache opt-in" semantics~~ ✅ Implemented
~~- No `supported_call_types` allowlist~~ ✅ Implemented
~~- `/cache/ping` does not perform a set/get round-trip~~ ✅ Implemented
~~- `/cache/delete` deletes one key per call (not batch)~~ ✅ Implemented (backwards compatible)
~~- Uses stdlib `json`~~ ✅ Switched to orjson

Still not implemented (out of scope):
- Config is env-driven (Pydantic Settings), not YAML
- No disk cache backend
- No semantic caching
- No S3/GCS cache backends
```

#### Add new configuration section:

```markdown
### Configuration (env-driven)

All cache settings load via `app/config.py`:

**Core Settings:**
- `LLM_CACHE_ENABLED` (default `true`) - Global cache enable
- `LLM_CACHE_NAMESPACE` (default `default`) - Cache key namespace
- `LLM_CACHE_L1_MAX_ENTRIES` (default `10000`) - Max L1 entries
- `LLM_CACHE_L1_TTL_SECONDS` (default `60`) - L1 TTL

**L2 (Redis) Settings:**
- `LLM_CACHE_L2_ENABLED` (default `false`) - Enable Redis L2
- `LLM_CACHE_REDIS_URL` (default empty) - Redis connection URL
- `LLM_CACHE_L2_AUTO_ENABLE` (default `true`) - Auto-enable when Redis reachable

**Versioning:**
- `LLM_GATEWAY_VERSION` (default `v1`) - Bump to invalidate cache
- `PROMPT_VERSION` (default `v1`) - Bump when prompts change

**LiteLLM-Style Controls (NEW):**
- `LLM_CACHE_MODE` (default `default_on`) - `default_on` or `default_off`
- `LLM_CACHE_SUPPORTED_CALL_TYPES` (default empty = all) - Comma-separated allowlist
```

#### Update "Per-request cache policy" section:

```markdown
### Per-request cache policy (LiteLLM-like controls)

Public request schemas include an optional `cache` object:

```json
{
  "cache": {
    "enabled": true,           // Disable caching for this request
    "use_cache": true,         // Opt-in (required when mode=default_off)
    "no_cache": false,         // Bypass cache lookup
    "no_store": false,         // Don't store result
    "ttl_seconds": 3600,       // Override TTL
    "s_maxage_seconds": 1800,  // Staleness threshold
    "namespace": "user123"     // Override namespace
  }
}
```
```

#### Update "Cache Admin Endpoints" section:

```markdown
### Cache Admin Endpoints

- `GET /cache/ping` - Check L1/L2 connectivity with round-trip test
  ```json
  {"l1": {"ok": true}, "l2": {"healthy": true, "latency_ms": 1.23}}
  ```

- `GET /cache/stats` - Full cache statistics

- `POST /cache/delete` - Delete cache keys (single or batch)
  ```json
  // Legacy (still supported):
  {"key": "llm:trace_analysis:abc123..."}

  // Batch:
  {"keys": ["llm:...", "llm:..."]}
  ```

- `POST /cache/clear-l1` - Clear entire L1 cache
```

---

### Phase 8: Tests

**New/Update File:** `app/tests/test_llm_cache_gateway.py`

```python
"""Tests for LLM Cache Gateway LiteLLM parity features."""
import pytest
from unittest.mock import patch, MagicMock

from app.services.llm_gateway.gateway import (
    LLMCacheGateway,
    CachePolicy,
    CacheableValue,
    CacheDiagnostics,
)


class TestDefaultOffMode:
    """Tests for LLM_CACHE_MODE=default_off behavior."""

    def test_default_off_mode_bypasses_without_use_cache(self):
        """When mode=default_off and use_cache=False, cache should be bypassed."""
        with patch("app.services.llm_gateway.gateway.settings") as mock_settings:
            mock_settings.LLM_CACHE_MODE = "default_off"
            mock_settings.LLM_CACHE_ENABLED = True
            mock_settings.llm_cache_supported_call_types_list = []

            gateway = LLMCacheGateway(
                enabled=True,
                gateway_version="v1",
                prompt_version="v1",
                namespace="test",
                l1_max_entries=100,
                l1_ttl_seconds=60,
                redis_url=None,
                l2_enabled=False,
            )

            compute_called = False
            def compute():
                nonlocal compute_called
                compute_called = True
                return CacheableValue(value="test_result", cacheable=True)

            result, diag = gateway.cached(
                cache_type="test_type",
                model="test_model",
                messages=[{"role": "user", "content": "test"}],
                options=None,
                default_ttl_seconds=60,
                policy=CachePolicy(use_cache=False),  # No opt-in
                compute=compute,
            )

            assert compute_called
            assert diag.status == "BYPASS_DEFAULT_OFF"

    def test_default_off_mode_caches_with_use_cache(self):
        """When mode=default_off and use_cache=True, cache should work normally."""
        with patch("app.services.llm_gateway.gateway.settings") as mock_settings:
            mock_settings.LLM_CACHE_MODE = "default_off"
            mock_settings.LLM_CACHE_ENABLED = True
            mock_settings.llm_cache_supported_call_types_list = []

            gateway = LLMCacheGateway(
                enabled=True,
                gateway_version="v1",
                prompt_version="v1",
                namespace="test",
                l1_max_entries=100,
                l1_ttl_seconds=60,
                redis_url=None,
                l2_enabled=False,
            )

            call_count = 0
            def compute():
                nonlocal call_count
                call_count += 1
                return CacheableValue(value="test_result", cacheable=True)

            # First call - should compute and cache
            result1, diag1 = gateway.cached(
                cache_type="test_type",
                model="test_model",
                messages=[{"role": "user", "content": "test"}],
                options=None,
                default_ttl_seconds=60,
                policy=CachePolicy(use_cache=True),  # Opt-in
                compute=compute,
            )

            assert call_count == 1
            assert diag1.status == "MISS"

            # Second call - should hit cache
            result2, diag2 = gateway.cached(
                cache_type="test_type",
                model="test_model",
                messages=[{"role": "user", "content": "test"}],
                options=None,
                default_ttl_seconds=60,
                policy=CachePolicy(use_cache=True),
                compute=compute,
            )

            assert call_count == 1  # Not called again
            assert diag2.status == "HIT_L1"


class TestSupportedCallTypes:
    """Tests for LLM_CACHE_SUPPORTED_CALL_TYPES allowlist."""

    def test_unsupported_call_type_bypasses(self):
        """Cache types not in allowlist should bypass cache."""
        with patch("app.services.llm_gateway.gateway.settings") as mock_settings:
            mock_settings.LLM_CACHE_MODE = "default_on"
            mock_settings.LLM_CACHE_ENABLED = True
            mock_settings.llm_cache_supported_call_types_list = ["trace_analysis"]  # Only this type

            gateway = LLMCacheGateway(
                enabled=True,
                gateway_version="v1",
                prompt_version="v1",
                namespace="test",
                l1_max_entries=100,
                l1_ttl_seconds=60,
                redis_url=None,
                l2_enabled=False,
            )

            compute_called = False
            def compute():
                nonlocal compute_called
                compute_called = True
                return CacheableValue(value="test_result", cacheable=True)

            result, diag = gateway.cached(
                cache_type="parameter_extraction",  # Not in allowlist
                model="test_model",
                messages=[{"role": "user", "content": "test"}],
                options=None,
                default_ttl_seconds=60,
                policy=None,
                compute=compute,
            )

            assert compute_called
            assert diag.status == "BYPASS_UNSUPPORTED_TYPE"


class TestBatchDelete:
    """Tests for batch delete endpoint."""

    def test_batch_delete(self):
        """Should delete multiple keys in one request."""
        from app.routers.cache_admin import cache_delete, CacheDeleteRequest

        with patch("app.routers.cache_admin.get_llm_cache_gateway") as mock_get_gw:
            mock_gw = MagicMock()
            mock_gw.delete.return_value = {"l1_deleted": True, "l2_deleted": 0}
            mock_get_gw.return_value = mock_gw

            req = CacheDeleteRequest(keys=["key1", "key2", "key3"])
            response = cache_delete(req)

            assert response.requested == 3
            assert mock_gw.delete.call_count == 3

    def test_single_key_delete_backwards_compat(self):
        """Legacy single-key format should still work."""
        from app.routers.cache_admin import cache_delete, CacheDeleteRequest

        with patch("app.routers.cache_admin.get_llm_cache_gateway") as mock_get_gw:
            mock_gw = MagicMock()
            mock_gw.delete.return_value = {"l1_deleted": True, "l2_deleted": 0}
            mock_get_gw.return_value = mock_gw

            req = CacheDeleteRequest(key="single_key")
            response = cache_delete(req)

            assert response.requested == 1
            mock_gw.delete.assert_called_once_with("single_key")


class TestPingRoundtrip:
    """Tests for ping endpoint round-trip test."""

    def test_ping_roundtrip_l2(self):
        """L2 ping should perform SET/GET/DEL round-trip."""
        from app.routers.cache_admin import cache_ping

        with patch("app.routers.cache_admin.get_llm_cache_gateway") as mock_get_gw:
            mock_gw = MagicMock()
            mock_l2 = MagicMock()
            mock_l2.get.return_value = b"ping_test_value"
            mock_gw.l2 = mock_l2
            mock_get_gw.return_value = mock_gw

            response = cache_ping()

            assert response["l1"]["ok"] is True
            assert response["l2"]["healthy"] is True
            assert "latency_ms" in response["l2"]

            # Verify round-trip operations were called
            mock_l2.set.assert_called_once()
            mock_l2.get.assert_called_once()
            mock_l2.delete.assert_called_once()
```

---

## File Change Summary

| File | Action | Changes |
|------|--------|---------|
| `app/config.py` | Modify | Add `LLM_CACHE_MODE`, `LLM_CACHE_SUPPORTED_CALL_TYPES`, helper property |
| `app/schemas/CachePolicy.py` | Modify | Add `use_cache` field with docstring |
| `app/services/llm_gateway/gateway.py` | Modify | orjson, mode/type checks, `use_cache` in CachePolicy, key in diagnostics |
| `app/routers/cache_admin.py` | Modify | Batch delete, round-trip ping, response models |
| `app/middleware/cache_header.py` | Create | New middleware for X-LLM-Cache-Key header |
| `app/main.py` | Modify | Register CacheHeaderMiddleware |
| `pyproject.toml` | Modify | Add orjson dependency |
| `docs/LLM_CACHING_REVIEW.md` | Modify | Update documentation |
| `app/tests/test_llm_cache_gateway.py` | Create/Modify | Add tests for new features |

---

## Migration Guide

### For Existing Deployments

No action required. All new features are opt-in with backwards-compatible defaults:

- `LLM_CACHE_MODE` defaults to `default_on` (existing behavior)
- `LLM_CACHE_SUPPORTED_CALL_TYPES` defaults to empty (all types allowed)
- `/cache/delete` accepts both `{"key": "..."}` and `{"keys": [...]}` formats

### To Enable Default-Off Mode

1. Set environment variable:
   ```bash
   LLM_CACHE_MODE=default_off
   ```

2. Update API clients to include `use_cache: true` in requests that should use cache:
   ```json
   {
     "query": "...",
     "cache": {
       "use_cache": true
     }
   }
   ```

### To Restrict Cache Types

Set `LLM_CACHE_SUPPORTED_CALL_TYPES` to comma-separated list:
```bash
LLM_CACHE_SUPPORTED_CALL_TYPES=trace_analysis,relevance_analysis
```

---

## References

- [LiteLLM Caching Documentation](https://docs.litellm.ai/docs/caching/all_caches)
- [LiteLLM Proxy Caching](https://docs.litellm.ai/docs/proxy/caching)
- [LiteLLM All Settings](https://docs.litellm.ai/docs/proxy/config_settings)
- [orjson Documentation](https://github.com/ijl/orjson)
