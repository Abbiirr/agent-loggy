# LLM Caching Review (agent-loggy)

This document re-checks the repo's LLM caching against a LiteLLM-proxy-style plan (config-driven, L1+L2, canonical keys, stampede protection, per-request policy, and cache admin endpoints).

Status: implemented with partial LiteLLM parity.

## Executive Summary

The repo now has a LiteLLM-like \"gateway-shaped\" caching layer:

- L1: bounded LRU + TTL in-memory cache (prevents unbounded RAM growth)
- L2 (optional): Redis cache for cross-worker/pod reuse (feature-flagged)
- Stampede protection: in-process single-flight + cross-process Redis lock (token + safe Lua unlock)
- Canonical cache keys: include `cache_type`, `namespace`, `model`, `messages` (normalized), and `options` (timeout excluded)
- Per-request policy: `enabled`, `no_cache`, `no_store`, `ttl_seconds`, `s_maxage_seconds`, and `namespace`
- Admin endpoints: `/cache/ping`, `/cache/stats`, `/cache/delete`, `/cache/clear-l1`

Remaining gaps vs the LiteLLM plan you provided:

- Config is env-driven (Pydantic Settings), not YAML.
- No \"mode: default_off + use_cache opt-in\" semantics yet; caching is enabled-by-default unless disabled per request.
- No `supported_call_types` allowlist; caching is controlled by the call site's `cache_type` and policy.
- `/cache/ping` does not perform a set/get round-trip (ping-only).
- `/cache/delete` deletes one key per call (not a batch of keys).
- No OpenAI-compatible public gateway endpoint (`/v1/chat/completions`) exposed by this app (caching wraps internal agents).
- The plan recommends `orjson` + `cachetools` + async Redis; this repo currently uses stdlib `json`, a custom bounded L1, and a synchronous Redis client (safe here because calls run in the threadpool).

## Current Implementation (what exists in this repo)

### 1) Provider boundary

- LLM calls use the Python `ollama.Client` (`client.chat(...)`), not an OpenAI-compatible HTTP proxy.
- Caching is applied around internal agent calls, not around a public `/v1/*` gateway.

### 2) Cache gateway module

Core implementation:

- `app/services/llm_gateway/gateway.py`
  - `LLMCacheGateway.cached(...)` is the shared entrypoint for cached calls
  - L1 backend: `_LRUTTLCache` (bounded LRU + TTL, stores bytes)
  - L2 backend (optional): `_RedisBackend` (sync `redis` client)
    - cache storage via `SET key value EX <ttl>`
    - stampede lock via `SET lock:{key} token NX PX <ms>` + Lua safe unlock
  - single-flight: `_ThreadSingleFlight` (coalesces concurrent same-key builds)
  - keying: `make_cache_key(...)` + `canonicalize_messages(...)`

### 3) Per-request cache policy (LiteLLM-like controls)

Public request schemas include an optional `cache` object:

- `app/schemas/CachePolicy.py` (`CachePolicyModel`)
- `app/schemas/ChatRequest.py`
- `app/schemas/StreamRequest.py`

Policy semantics:

- `enabled=false`: bypass caching completely for this call
- `no_cache=true`: bypass reads (force refresh) but still write unless `no_store`
- `no_store=true`: do not write to cache
- `ttl_seconds`: per-request TTL override
- `s_maxage_seconds`: accept cached values only if younger than this
- `namespace`: per-request namespace override

Important difference vs LiteLLM `mode: default_off`:

- There is no `use_cache` opt-in field today; caching is enabled-by-default when global `LLM_CACHE_ENABLED=true`.

### 4) What calls are cached (supported call types in practice)

The gateway wraps these internal call types:

- `parameter_extraction`: `app/agents/parameter_agent.py`
- `trace_analysis`, `trace_entries_analysis`, `quality_assessment`: `app/agents/analyze_agent.py`
- `relevance_analysis`: `app/agents/verify_agent.py`
- `planning`: `app/agents/planning_agent.py`

Legacy note:

- `app/services/llm_cache.py` still exists but is no longer referenced by agents (legacy/unused).

### 5) TTL defaults (per call type)

Defaults are applied at each call site (and can be overridden via request `cache.ttl_seconds`):

- `parameter_extraction`: 7200s
- `trace_analysis`: 14400s
- `trace_entries_analysis`: 14400s
- `quality_assessment`: 7200s
- `relevance_analysis`: 14400s
- `planning`: 600s

L1 uses its own shorter default TTL for fast \"hot\" reuse; L2 stores for the per-call TTL if enabled.

### 6) Canonical cache keys (correctness)

`make_cache_key(...)` hashes a canonical payload containing:

- `cache_type`
- `namespace`
- `gateway_version` + `prompt_version` (explicit invalidation knobs)
- `model`
- `messages` (normalized)
- `options` (includes generation params; excludes timeout)

Volatility handling:

- For `relevance_analysis`, message normalization strips common volatile report lines like `Generated: ...`, `Analysis completed: ...`, and `- Timestamp: ...` to prevent cache misses caused by report generation time.

### 7) Stampede protection

- In-process: `_ThreadSingleFlight` ensures one compute per key per process; others await the same result.
- Cross-process: Redis lock prevents multi-worker/pod stampede on cold keys when L2 is enabled and Redis is available.

Operational note:

- This app runs LLM work in a threadpool (`run_in_threadpool`), so using the synchronous Redis client is acceptable (it runs off the event loop).

### 8) Streaming + cache diagnostics

The app still streams pipeline steps via SSE:

- `POST /api/chat` then `GET /api/chat/stream/{session_id}` (React UI flow): `app/routers/chat.py`
- `POST /stream-analysis`: `app/routers/analysis.py`

Cache diagnostics are included on the \"Extracted Parameters\" step payload (parameter extraction cache status).

## Configuration (env-driven)

All cache settings load via `app/config.py`:

- `LLM_CACHE_ENABLED` (default `true`)
- `LLM_CACHE_NAMESPACE` (default `default`)
- `LLM_CACHE_L1_MAX_ENTRIES` (default `10000`)
- `LLM_CACHE_L1_TTL_SECONDS` (default `60`)
- `LLM_CACHE_L2_ENABLED` (default `false`)
- `LLM_CACHE_REDIS_URL` (default empty/none)
- `LLM_CACHE_L2_AUTO_ENABLE` (default `true`; enables L2 automatically when Redis is reachable)
- `LLM_GATEWAY_VERSION` + `PROMPT_VERSION` (both default `v1`)

Dependency note:

- `redis` is included in `pyproject.toml` so enabling L2 doesn't require additional installs.
- `docker-compose.yml` does not currently define a Redis service; to use L2 you need a Redis instance running and reachable at `LLM_CACHE_REDIS_URL`.

## Cache Admin Endpoints (LiteLLM parity)

Implemented:

- `GET /cache/ping`: reports L2 ping status if enabled (no set/get test today)
- `GET /cache/stats`: gateway counters + L1/L2 stats
- `POST /cache/delete`: deletes one key; body is `{ "key": "..." }`
- `POST /cache/clear-l1`

## LiteLLM Plan Alignment (feature-by-feature)

- Backends + config: partial (L1 + Redis L2 implemented; env-driven, not YAML; disk/semantic not implemented)
- Supported call types: partial (implicit via `cache_type`; no global `supported_call_types` list)
- Default-off / opt-in: not implemented (currently enabled-by-default)
- Cache admin endpoints: mostly implemented (endpoints exist; ping/delete semantics differ slightly)
- Key correctness: improved (includes versions + options; relevance prompt volatility normalized)
- Stampede protection: implemented (single-flight + Redis lock + safe unlock)

## Validation Checklist (how to prove it works)

1. Enable Redis L2 and run multiple workers:
   - set `LLM_CACHE_L2_ENABLED=true`
   - set `LLM_CACHE_REDIS_URL=redis://localhost:6379/0`
   - run `uvicorn app.main:app --workers 4`
2. Run the same request twice and confirm:
   - `GET /cache/stats` shows `l2_hits` increasing on the second run (even if it lands on a different worker)
3. Stress-test stampede:
   - fire 10-20 identical requests concurrently and confirm fewer provider calls per key (watch Ollama logs + `coalesced`/`l2_hits` counters)
4. Invalidate via versions:
   - bump `PROMPT_VERSION` or `LLM_GATEWAY_VERSION` and verify cache misses.

## Appendix: Where to Look in Code

- Gateway + keying + locks: `app/services/llm_gateway/gateway.py`
- Cache policy request schema: `app/schemas/CachePolicy.py`
- Cache admin endpoints: `app/routers/cache_admin.py`
- Orchestrator + SSE wiring: `app/orchestrator.py`, `app/routers/chat.py`, `app/routers/analysis.py`
- Legacy cache (not used by agents): `app/services/llm_cache.py`
