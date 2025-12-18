<!-- Pack version: 11f3d69cd35f822f62ba5b27519f7bd154f5fb6f -->
<!-- DO NOT EDIT: Run `python scripts/export_ai_pack.py` -->

# AI_PACK

## How an AI agent should use this pack

- Start at `ENTRYPOINT`.
- Use `MODULE_INDEX` to find relevant modules and file paths.
- Use `CONFIG_REFERENCE` to discover config/env keys and defaults (best-effort).
- Use `LOG_CATALOG` to interpret log messages and locate their sources.
- In responses, cite file paths and headings from this pack.

## Table of contents

- [ENTRYPOINT](#entrypoint)
- [ARCHITECTURE](#architecture)
- [MODULE_INDEX](#module-index)
- [CONFIG_REFERENCE](#config-reference)
- [LOG_CATALOG](#log-catalog)
- [GLOSSARY](#glossary)
- [REPO_TREE](#repo-tree)
- [QUALITY_BAR](#quality-bar)
- [ADR-0001](#adr-0001)

<a id="entrypoint"></a>
## ENTRYPOINT (`docs/ai/ENTRYPOINT.md`)

# Entrypoint

Goal: quickly locate the “main loop”, the request flow, and the extension points.

## What this repo is

`agent-loggy` is a Python service for log analysis and verification. It exposes an API and orchestrates multiple LLM-powered agents to:

- extract parameters from user text
- find and collect logs (local files and/or Loki)
- compile traces per trace-id
- generate analysis and verification outputs

## Where to start reading (in order)

1. `docs/ai/ARCHITECTURE.md` for system shape and responsibilities.
2. `docs/ai/MODULE_INDEX.md` for a map of modules and short summaries.
3. `docs/ai/CONFIG_REFERENCE.md` to see env vars / settings.
4. `docs/ai/LOG_CATALOG.md` to interpret emitted logs.

## Primary runtime entrypoints

- FastAPI app: `app/main.py`
- Pipeline orchestrator: `app/orchestrator.py`
- Routers (HTTP surface): `app/routers/`

## Typical dev commands

```bash
uv sync
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
uv run pytest
```

## When implementing features

- Prefer updating docs + indexes with `python scripts/check_docs_fresh.py`.
- When adding new config/env vars, ensure they appear in `docs/ai/CONFIG_REFERENCE.md`.
- When adding or changing log messages, ensure they appear in `docs/ai/LOG_CATALOG.md`.

<a id="architecture"></a>
## ARCHITECTURE (`docs/ai/ARCHITECTURE.md`)

# Architecture

This is a compact, agent-oriented view of the system. For longer notes, see `docs/ARCHITECTURE.md`.

## High-level components

- API layer: FastAPI app in `app/main.py` and routers in `app/routers/`
- Orchestration: `app/orchestrator.py` coordinates the multi-step analysis pipeline
- Agents: `app/agents/` contains LLM-driven steps (parameter extraction, planning, analysis, verification)
- Tools: `app/tools/` provides log search/trace collection primitives (including Loki integration under `app/tools/loki/`)
- Persistence/config: models under `app/models/`, settings in `app/config.py`, services under `app/services/`

## Pipeline sketch

The orchestrator performs a stepwise flow (names may differ; see `docs/ai/MODULE_INDEX.md`):

1. Extract parameters from user text
2. Plan/gate the pipeline (may ask for clarification)
3. Search logs (file-based or Loki-based)
4. Extract trace IDs and compile per-trace logs
5. Generate analysis outputs
6. Run verification and emit summary

## Extension points

- Add new log backends under `app/tools/` and dispatch in `app/orchestrator.py`
- Add new agents under `app/agents/` and wire them into the orchestrator
- Add new API endpoints under `app/routers/`

<a id="module-index"></a>
## MODULE_INDEX (`docs/ai/MODULE_INDEX.md`)

# Module index (generated)

Key files:
- `app/main.py`
- `app/orchestrator.py`
- `app/config.py`
- `app/startup.py`
- `app/routers/chat.py`

Modules:

| Module | Path | Summary | Source |
|---|---|---|---|
| `app` | `app/__init__.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/__init__.py) |
| `app.agents` | `app/agents/__init__.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/__init__.py) |
| `app.agents.analyze_agent` | `app/agents/analyze_agent.py` | agents/analyze_agent.py - Refactored version focusing on analysis generation | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py) |
| `app.agents.file_searcher` | `app/agents/file_searcher.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py) |
| `app.agents.parameter_agent` | `app/agents/parameter_agent.py` | parameters_agent.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py) |
| `app.agents.planning_agent` | `app/agents/planning_agent.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/planning_agent.py) |
| `app.agents.report_writer` | `app/agents/report_writer.py` | agents/report_writer.py - Handles all report generation and file writing | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/report_writer.py) |
| `app.agents.verify_agent` | `app/agents/verify_agent.py` | agents/verify_agent.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py) |
| `app.config` | `app/config.py` | app/core/config.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/config.py) |
| `app.db` | `app/db/__init__.py` | app/db/__init__.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/db/__init__.py) |
| `app.db.base` | `app/db/base.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/db/base.py) |
| `app.db.session` | `app/db/session.py` | SQLAlchemy session factory with FastAPI dependency injection. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/db/session.py) |
| `app.dependencies` | `app/dependencies.py` | Shared dependencies for FastAPI routes. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/dependencies.py) |
| `app.evals` | `app/evals/__init__.py` | Prompt evaluation framework for continuous improvement. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/__init__.py) |
| `app.evals.cli` | `app/evals/cli.py` | CLI for running prompt evaluations. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/cli.py) |
| `app.evals.metrics` | `app/evals/metrics.py` | Metrics calculators for evaluating agent outputs against expected values. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/metrics.py) |
| `app.evals.models` | `app/evals/models.py` | SQLAlchemy models for prompt evaluation results. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/models.py) |
| `app.evals.runner` | `app/evals/runner.py` | Evaluation runner for testing prompts against golden datasets. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/runner.py) |
| `app.evals.storage` | `app/evals/storage.py` | Database storage layer for evaluation results. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/storage.py) |
| `app.main` | `app/main.py` | main.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/main.py) |
| `app.models` | `app/models/__init__.py` | app/models/__init__.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/models/__init__.py) |
| `app.models.context_rule` | `app/models/context_rule.py` | SQLAlchemy models for RAG context rules. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/models/context_rule.py) |
| `app.models.project` | `app/models/project.py` | SQLAlchemy models for project configuration. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/models/project.py) |
| `app.models.prompt` | `app/models/prompt.py` | SQLAlchemy models for versioned prompts with history tracking. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/models/prompt.py) |
| `app.models.settings` | `app/models/settings.py` | SQLAlchemy models for application settings with history tracking. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/models/settings.py) |
| `app.orchestrator` | `app/orchestrator.py` | orchestrator.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py) |
| `app.routers` | `app/routers/__init__.py` | API routers for agent-loggy. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/routers/__init__.py) |
| `app.routers.analysis` | `app/routers/analysis.py` | Analysis API routes for log analysis streaming. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/routers/analysis.py) |
| `app.routers.chat` | `app/routers/chat.py` | Chat API routes for the React ChatInterface. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/routers/chat.py) |
| `app.routers.files` | `app/routers/files.py` | File download API routes. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/routers/files.py) |
| `app.schemas` | `app/schemas/__init__.py` | schemas/__init__.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/schemas/__init__.py) |
| `app.schemas.ChatRequest` | `app/schemas/ChatRequest.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/schemas/ChatRequest.py) |
| `app.schemas.ChatResponse` | `app/schemas/ChatResponse.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/schemas/ChatResponse.py) |
| `app.schemas.StreamRequest` | `app/schemas/StreamRequest.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/schemas/StreamRequest.py) |
| `app.services` | `app/services/__init__.py` | app/services/__init__.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/__init__.py) |
| `app.services.cache` | `app/services/cache.py` | TTL-based caching infrastructure with thread-safe in-memory caching. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/cache.py) |
| `app.services.config_service` | `app/services/config_service.py` | Service layer for application configuration management with caching and fallback defaults. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/config_service.py) |
| `app.services.llm_cache` | `app/services/llm_cache.py` | LLM response caching service for reducing redundant Ollama API calls. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/llm_cache.py) |
| `app.services.project_service` | `app/services/project_service.py` | Service layer for project configuration management with caching and fallback defaults. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/project_service.py) |
| `app.services.prompt_service` | `app/services/prompt_service.py` | Service layer for versioned prompt management with caching and hot-reload support. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/prompt_service.py) |
| `app.startup` | `app/startup.py` | Application startup logic and health checks. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/startup.py) |
| `app.tests` | `app/tests/__init__.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tests/__init__.py) |
| `app.tests.test_cache` | `app/tests/test_cache.py` | Tests for the TTLCache and CacheManager classes. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tests/test_cache.py) |
| `app.tests.test_planning_agent` | `app/tests/test_planning_agent.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tests/test_planning_agent.py) |
| `app.tests.test_trace_id_extractor` | `app/tests/test_trace_id_extractor.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tests/test_trace_id_extractor.py) |
| `app.tools` | `app/tools/__init__.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/__init__.py) |
| `app.tools.full_log_finder` | `app/tools/full_log_finder.py` | tools/full_log_finder.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/full_log_finder.py) |
| `app.tools.log_searcher` | `app/tools/log_searcher.py` | tools/log_searcher.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/log_searcher.py) |
| `app.tools.loki` | `app/tools/loki/__init__.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/loki/__init__.py) |
| `app.tools.loki.loki_log_analyser` | `app/tools/loki/loki_log_analyser.py` | log_compiler.py: Library for compiling Loki and application logs into human-readable timeline reports. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/loki/loki_log_analyser.py) |
| `app.tools.loki.loki_log_report_generator` | `app/tools/loki/loki_log_report_generator.py` | log_compiler.py: Library for compiling Loki and application logs into human-readable comprehensive timeline reports. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/loki/loki_log_report_generator.py) |
| `app.tools.loki.loki_query_builder` | `app/tools/loki/loki_query_builder.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/loki/loki_query_builder.py) |
| `app.tools.loki.loki_trace_id_extractor` | `app/tools/loki/loki_trace_id_extractor.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/loki/loki_trace_id_extractor.py) |
| `app.tools.trace_id_extractor` | `app/tools/trace_id_extractor.py` | tools/trace_id_extractor.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/trace_id_extractor.py) |

<a id="config-reference"></a>
## CONFIG_REFERENCE (`docs/ai/CONFIG_REFERENCE.md`)

# Config reference (generated)

Best-effort discovery of config keys and environment variables.

## CFG-01465D6DE8: `ANALYSIS_DIR`

- Defaults: (not detected)
- References:
  - `app/config.py:11` (BaseSettings field) — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/config.py#L11)

## CFG-3380C1D399: `DATABASE_SCHEMA`

- Defaults: (not detected)
- References:
  - `app/config.py:9` (BaseSettings field) — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/config.py#L9)

## CFG-01D2F16EDF: `DATABASE_URL`

- Defaults: (not detected)
- References:
  - `app/config.py:8` (BaseSettings field) — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/config.py#L8)

## CFG-AAC8C77084: `MODEL`

- Defaults: (not detected)
- References:
  - `app/config.py:12` (BaseSettings field) — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/config.py#L12)

## CFG-939C1EF9F2: `OLLAMA_HOST`

- Defaults: (not detected)
- References:
  - `app/config.py:10` (BaseSettings field) — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/config.py#L10)

## CFG-5E8EAEE750: `USE_DB_PROJECTS`

- Defaults:
  - `False`
- References:
  - `app/config.py:17` (BaseSettings field) — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/config.py#L17)

## CFG-8CC89E6356: `USE_DB_PROMPTS`

- Defaults:
  - `False`
- References:
  - `app/config.py:15` (BaseSettings field) — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/config.py#L15)

## CFG-3F064F9B7A: `USE_DB_SETTINGS`

- Defaults:
  - `False`
- References:
  - `app/config.py:16` (BaseSettings field) — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/config.py#L16)

<a id="log-catalog"></a>
## LOG_CATALOG (`docs/ai/LOG_CATALOG.md`)

# Log catalog (generated)

Best-effort extraction of log message templates from Python logging calls.

## LOG-D633474910

- Level: `debug`
- Message: `Using database prompt for {...}`
- Location: `app/agents/analyze_agent.py:32` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L32)
- Function: `_get_prompt_from_db`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-51B8EC4075

- Level: `warning`
- Message: `Failed to get prompt '{...}' from database: {...}`
- Location: `app/agents/analyze_agent.py:35` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L35)
- Function: `_get_prompt_from_db`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-03ED4C254F

- Level: `info`
- Message: `VerifyAgent initialized with model: {...}, output directory: {...}`
- Location: `app/agents/analyze_agent.py:54` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L54)
- Function: `AnalyzeAgent.__init__`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-6A9DB3F8CB

- Level: `info`
- Message: `Creating comprehensive analysis files for each trace...`
- Location: `app/agents/analyze_agent.py:77` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L77)
- Function: `AnalyzeAgent.analyze_and_create_comprehensive_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-75B5295B22

- Level: `warning`
- Message: `No trace data available for analysis`
- Location: `app/agents/analyze_agent.py:81` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L81)
- Function: `AnalyzeAgent.analyze_and_create_comprehensive_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-8448599856

- Level: `info`
- Message: `Creating comprehensive file for trace: {...}`
- Location: `app/agents/analyze_agent.py:92` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L92)
- Function: `AnalyzeAgent.analyze_and_create_comprehensive_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-EA9806D74C

- Level: `info`
- Message: `✓ Created comprehensive file: {...}`
- Location: `app/agents/analyze_agent.py:108` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L108)
- Function: `AnalyzeAgent.analyze_and_create_comprehensive_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-E8742817B4

- Level: `info`
- Message: `Comprehensive analysis completed for {...} traces`
- Location: `app/agents/analyze_agent.py:135` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L135)
- Function: `AnalyzeAgent.analyze_and_create_comprehensive_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-E43ECD3DDD

- Level: `info`
- Message: `Master summary: {...}`
- Location: `app/agents/analyze_agent.py:136` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L136)
- Function: `AnalyzeAgent.analyze_and_create_comprehensive_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-50CD684FA4

- Level: `info`
- Message: `Starting analysis of {...} log files`
- Location: `app/agents/analyze_agent.py:162` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L162)
- Function: `AnalyzeAgent.analyze_log_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-1F06FC46F4

- Level: `info`
- Message: `Parsed {...} entries from {...}`
- Location: `app/agents/analyze_agent.py:170` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L170)
- Function: `AnalyzeAgent.analyze_log_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-BE3ADC2F3F

- Level: `error`
- Message: `Error parsing {...}: {...}`
- Location: `app/agents/analyze_agent.py:172` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L172)
- Function: `AnalyzeAgent.analyze_log_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-EF1189AC2E

- Level: `info`
- Message: `Found {...} unique traces with {...} total entries`
- Location: `app/agents/analyze_agent.py:179` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L179)
- Function: `AnalyzeAgent.analyze_log_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-94863E093C

- Level: `info`
- Message: `✓ Created report for trace {...}: {...}`
- Location: `app/agents/analyze_agent.py:199` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L199)
- Function: `AnalyzeAgent.analyze_log_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-869B4CACAD

- Level: `error`
- Message: `Error creating report for trace {...}: {...}`
- Location: `app/agents/analyze_agent.py:202` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L202)
- Function: `AnalyzeAgent.analyze_log_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-2CAFF3A895

- Level: `info`
- Message: `✓ Created master summary: {...}`
- Location: `app/agents/analyze_agent.py:210` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L210)
- Function: `AnalyzeAgent.analyze_log_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-668EC7CE7D

- Level: `error`
- Message: `Error creating master summary: {...}`
- Location: `app/agents/analyze_agent.py:213` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L213)
- Function: `AnalyzeAgent.analyze_log_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-981049EA19

- Level: `info`
- Message: `Analysis complete: {...} individual reports + 1 master report`
- Location: `app/agents/analyze_agent.py:228` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L228)
- Function: `AnalyzeAgent.analyze_log_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-1816D324AF

- Level: `info`
- Message: `Using cached trace analysis for {...}`
- Location: `app/agents/analyze_agent.py:325` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L325)
- Function: `AnalyzeAgent._analyze_single_trace`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-200982701E

- Level: `error`
- Message: `Error analyzing trace {...}: {...}`
- Location: `app/agents/analyze_agent.py:349` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L349)
- Function: `AnalyzeAgent._analyze_single_trace`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-BE941B9A4C

- Level: `info`
- Message: `Using cached entries analysis for {...}`
- Location: `app/agents/analyze_agent.py:410` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L410)
- Function: `AnalyzeAgent._analyze_single_trace_from_entries`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-200982701E

- Level: `error`
- Message: `Error analyzing trace {...}: {...}`
- Location: `app/agents/analyze_agent.py:431` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L431)
- Function: `AnalyzeAgent._analyze_single_trace_from_entries`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-DDDF485711

- Level: `info`
- Message: `Using cached quality assessment`
- Location: `app/agents/analyze_agent.py:473` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L473)
- Function: `AnalyzeAgent._assess_overall_quality`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-DB709BD7EC

- Level: `error`
- Message: `Error in overall quality assessment: {...}`
- Location: `app/agents/analyze_agent.py:489` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L489)
- Function: `AnalyzeAgent._assess_overall_quality`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-7D51002A60

- Level: `error`
- Message: `Error parsing log file {...}: {...}`
- Location: `app/agents/analyze_agent.py:551` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py#L551)
- Function: `AnalyzeAgent._parse_log_file`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-EBE65FD7C5

- Level: `error`
- Message: `No time_frame provided in parameters`
- Location: `app/agents/file_searcher.py:52` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L52)
- Function: `FileSearcher.find_and_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-50EDA8E57C

- Level: `error`
- Message: `Failed to parse time_frame '{...}': {...}`
- Location: `app/agents/file_searcher.py:58` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L58)
- Function: `FileSearcher.find_and_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-0DE6D6F747

- Level: `info`
- Message: `Searching for logs with date: {...}`
- Location: `app/agents/file_searcher.py:61` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L61)
- Function: `FileSearcher.find_and_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-812CD85726

- Level: `info`
- Message: `Parameters: {...}`
- Location: `app/agents/file_searcher.py:62` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L62)
- Function: `FileSearcher.find_and_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-C158C1CD29

- Level: `info`
- Message: `--- Searching for {...} logs ---`
- Location: `app/agents/file_searcher.py:67` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L67)
- Function: `FileSearcher.find_and_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-E9731FB602

- Level: `info`
- Message: `Found {...} candidate {...} files: {...}`
- Location: `app/agents/file_searcher.py:71` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L71)
- Function: `FileSearcher.find_and_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-6D2F14B952

- Level: `info`
- Message: `Checking candidate file: {...}`
- Location: `app/agents/file_searcher.py:75` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L75)
- Function: `FileSearcher.find_and_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-78950B21DA

- Level: `info`
- Message: `✓ Regex verification passed for {...}`
- Location: `app/agents/file_searcher.py:79` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L79)
- Function: `FileSearcher.find_and_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-61498DB29E

- Level: `info`
- Message: `✓ LLM verification passed for {...}`
- Location: `app/agents/file_searcher.py:83` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L83)
- Function: `FileSearcher.find_and_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-8B0DB65B72

- Level: `debug`
- Message: `✗ LLM verification failed for {...}`
- Location: `app/agents/file_searcher.py:86` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L86)
- Function: `FileSearcher.find_and_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-FCE7FF47E9

- Level: `debug`
- Message: `✗ Regex verification failed for {...}`
- Location: `app/agents/file_searcher.py:88` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L88)
- Function: `FileSearcher.find_and_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-0B17002F0A

- Level: `info`
- Message: `No {...} files found for date {...}`
- Location: `app/agents/file_searcher.py:90` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L90)
- Function: `FileSearcher.find_and_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-AB798B9E01

- Level: `info`
- Message: `Total verified log files found: {...}`
- Location: `app/agents/file_searcher.py:93` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L93)
- Function: `FileSearcher.find_and_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-FFE546740F

- Level: `info`
- Message: `  ✓ {...}`
- Location: `app/agents/file_searcher.py:95` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L95)
- Function: `FileSearcher.find_and_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-3E8678B85F

- Level: `warning`
- Message: `No verified log files found for {...}`
- Location: `app/agents/file_searcher.py:97` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L97)
- Function: `FileSearcher.find_and_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-EB673AB6F3

- Level: `info`
- Message: `Searching in directory: {...}`
- Location: `app/agents/file_searcher.py:104` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L104)
- Function: `FileSearcher._list_all_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-B9481CBF25

- Level: `info`
- Message: `Directory exists: {...}`
- Location: `app/agents/file_searcher.py:105` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L105)
- Function: `FileSearcher._list_all_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-916B5BBF62

- Level: `info`
- Message: `Directory is directory: {...}`
- Location: `app/agents/file_searcher.py:106` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L106)
- Function: `FileSearcher._list_all_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-FF405B9BF1

- Level: `error`
- Message: `Base directory does not exist: {...}`
- Location: `app/agents/file_searcher.py:109` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L109)
- Function: `FileSearcher._list_all_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-C109207094

- Level: `info`
- Message: `All files and directories in base directory ({...}):`
- Location: `app/agents/file_searcher.py:114` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L114)
- Function: `FileSearcher._list_all_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-8EB35C512B

- Level: `info`
- Message: `  FILE: {...}`
- Location: `app/agents/file_searcher.py:117` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L117)
- Function: `FileSearcher._list_all_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-176469E36F

- Level: `info`
- Message: `  DIR:  {...}`
- Location: `app/agents/file_searcher.py:119` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L119)
- Function: `FileSearcher._list_all_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-3BA8220C88

- Level: `info`
- Message: `All .xz files in directory and subdirectories ({...}):`
- Location: `app/agents/file_searcher.py:123` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L123)
- Function: `FileSearcher._list_all_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-8DDA0F343F

- Level: `info`
- Message: `  - {...}`
- Location: `app/agents/file_searcher.py:125` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L125)
- Function: `FileSearcher._list_all_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-BD3377E31D

- Level: `error`
- Message: `Error listing files: {...}`
- Location: `app/agents/file_searcher.py:128` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L128)
- Function: `FileSearcher._list_all_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-2AEF3F72F1

- Level: `debug`
- Message: `Found {...} candidates for {...}: {...}`
- Location: `app/agents/file_searcher.py:153` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L153)
- Function: `FileSearcher._find_files_by_prefix_and_date`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-B68E538037

- Level: `debug`
- Message: `Regex verification for {...}`
- Location: `app/agents/file_searcher.py:165` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L165)
- Function: `FileSearcher._regex_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-286ACEB965

- Level: `debug`
- Message: `Found domain keyword '{...}' in filename`
- Location: `app/agents/file_searcher.py:172` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L172)
- Function: `FileSearcher._regex_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-4FA4A735DF

- Level: `debug`
- Message: `Found query key '{...}' in filename`
- Location: `app/agents/file_searcher.py:178` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L178)
- Function: `FileSearcher._regex_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-A3FA0F34E7

- Level: `debug`
- Message: `Found query keys in file content`
- Location: `app/agents/file_searcher.py:185` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L185)
- Function: `FileSearcher._regex_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-33280E4287

- Level: `error`
- Message: `Error reading file {...}: {...}`
- Location: `app/agents/file_searcher.py:188` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L188)
- Function: `FileSearcher._regex_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-384D28FEA8

- Level: `debug`
- Message: `No specific matches found in regex check, allowing LLM verification`
- Location: `app/agents/file_searcher.py:191` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L191)
- Function: `FileSearcher._regex_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-CAD8A152D6

- Level: `error`
- Message: `Error reading file content: {...}`
- Location: `app/agents/file_searcher.py:208` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L208)
- Function: `FileSearcher._check_file_content`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-CC28208726

- Level: `error`
- Message: `Error checking content: {...}`
- Location: `app/agents/file_searcher.py:221` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L221)
- Function: `FileSearcher._check_content`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-B4524976DF

- Level: `debug`
- Message: `Parsed time frame '{...}' to '{...}'`
- Location: `app/agents/file_searcher.py:281` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L281)
- Function: `FileSearcher._parse_time_frame`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-7F64D272B3

- Level: `error`
- Message: `Error parsing time frame '{...}': {...}`
- Location: `app/agents/file_searcher.py:284` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py#L284)
- Function: `FileSearcher._parse_time_frame`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-5B546861E0

- Level: `warning`
- Message: `Failed to get config {...}.{...}: {...}`
- Location: `app/agents/parameter_agent.py:33` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py#L33)
- Function: `_get_config`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-1AB43F4B6A

- Level: `debug`
- Message: `Ollama health check attempt {...} failed: {...}`
- Location: `app/agents/parameter_agent.py:127` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py#L127)
- Function: `is_ollama_running`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-0B877D6EEB

- Level: `info`
- Message: `ParametersAgent using model: %s`
- Location: `app/agents/parameter_agent.py:147` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py#L147)
- Function: `ParametersAgent.__init__`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-DE7D87E484

- Level: `error`
- Message: `Ollama server is not available. Using fallback extraction.`
- Location: `app/agents/parameter_agent.py:154` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py#L154)
- Function: `ParametersAgent.run`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-38103A2C71

- Level: `info`
- Message: `Using cached parameter extraction response`
- Location: `app/agents/parameter_agent.py:168` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py#L168)
- Function: `ParametersAgent.run`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-775FBE97A3

- Level: `debug`
- Message: `Raw LLM response (length=%d): %s`
- Location: `app/agents/parameter_agent.py:179` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py#L179)
- Function: `ParametersAgent.run`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-9234862093

- Level: `debug`
- Message: `Extracted JSON blob: %s`
- Location: `app/agents/parameter_agent.py:184` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py#L184)
- Function: `ParametersAgent.run`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-7167FC8536

- Level: `debug`
- Message: `Parsed params from LLM: %s`
- Location: `app/agents/parameter_agent.py:186` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py#L186)
- Function: `ParametersAgent.run`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-EF2A8B9BF4

- Level: `error`
- Message: `LLM JSON parse error (%s). Raw response was: %s`
- Location: `app/agents/parameter_agent.py:191` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py#L191)
- Function: `ParametersAgent.run`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-C46541F78A

- Level: `info`
- Message: `Falling back to regex-only extraction.`
- Location: `app/agents/parameter_agent.py:192` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py#L192)
- Function: `ParametersAgent.run`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-A1840A26D6

- Level: `debug`
- Message: `Fallback params: %s`
- Location: `app/agents/parameter_agent.py:194` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py#L194)
- Function: `ParametersAgent.run`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-F93C5FFF11

- Level: `error`
- Message: `Ollama API call failed: {...}. Using fallback extraction.`
- Location: `app/agents/parameter_agent.py:197` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py#L197)
- Function: `ParametersAgent.run`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-44FBE36ACB

- Level: `debug`
- Message: `Using database prompt for parameter_extraction_system`
- Location: `app/agents/parameter_agent.py:255` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py#L255)
- Function: `ParametersAgent._build_system_prompt`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-BCC6D0121A

- Level: `warning`
- Message: `Database prompt not found, falling back to hardcoded prompt`
- Location: `app/agents/parameter_agent.py:257` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py#L257)
- Function: `ParametersAgent._build_system_prompt`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-2D0C5E0075

- Level: `warning`
- Message: `Failed to get prompt from database: {...}, using hardcoded prompt`
- Location: `app/agents/parameter_agent.py:259` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py#L259)
- Function: `ParametersAgent._build_system_prompt`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-03695F11AB

- Level: `debug`
- Message: `After stripping think blocks (length=%d): %s`
- Location: `app/agents/parameter_agent.py:298` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py#L298)
- Function: `ParametersAgent._extract_json_block`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-EFDF3B939E

- Level: `debug`
- Message: `_fallback called with text: %s`
- Location: `app/agents/parameter_agent.py:466` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py#L466)
- Function: `ParametersAgent._fallback`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-58DEC4B626

- Level: `debug`
- Message: `_fallback: normalized date from text = %s`
- Location: `app/agents/parameter_agent.py:468` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py#L468)
- Function: `ParametersAgent._fallback`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-039B95CB0A

- Level: `debug`
- Message: `_fallback: inferred domain = %s`
- Location: `app/agents/parameter_agent.py:470` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py#L470)
- Function: `ParametersAgent._fallback`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-C529A25E48

- Level: `debug`
- Message: `_fallback: sanitized query_keys = %s`
- Location: `app/agents/parameter_agent.py:472` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py#L472)
- Function: `ParametersAgent._fallback`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-2ACE15B7BD

- Level: `warning`
- Message: `PlanningAgent failed; using fallback: %s`
- Location: `app/agents/planning_agent.py:63` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/planning_agent.py#L63)
- Function: `PlanningAgent.run`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-A32490A347

- Level: `info`
- Message: `ReportWriter initialized with output directory: {...}`
- Location: `app/agents/report_writer.py:22` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/report_writer.py#L22)
- Function: `ReportWriter.__init__`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-45C9E1E04B

- Level: `info`
- Message: `Comprehensive trace file created: {...}`
- Location: `app/agents/report_writer.py:50` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/report_writer.py#L50)
- Function: `ReportWriter.create_comprehensive_trace_file`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-4FEB0D1B3B

- Level: `error`
- Message: `Error creating comprehensive file for trace {...}: {...}`
- Location: `app/agents/report_writer.py:54` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/report_writer.py#L54)
- Function: `ReportWriter.create_comprehensive_trace_file`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-AF8A0427AD

- Level: `info`
- Message: `Master summary file created: {...}`
- Location: `app/agents/report_writer.py:81` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/report_writer.py#L81)
- Function: `ReportWriter.create_master_summary_file`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-AEAA42BEAA

- Level: `error`
- Message: `Error creating master summary: {...}`
- Location: `app/agents/report_writer.py:85` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/report_writer.py#L85)
- Function: `ReportWriter.create_master_summary_file`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-11392EF567

- Level: `info`
- Message: `Individual trace report created: {...}`
- Location: `app/agents/report_writer.py:109` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/report_writer.py#L109)
- Function: `ReportWriter.create_individual_trace_report`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-502EF66395

- Level: `error`
- Message: `Error creating individual trace report for {...}: {...}`
- Location: `app/agents/report_writer.py:113` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/report_writer.py#L113)
- Function: `ReportWriter.create_individual_trace_report`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-F6B2A0879D

- Level: `info`
- Message: `Master analysis summary created: {...}`
- Location: `app/agents/report_writer.py:136` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/report_writer.py#L136)
- Function: `ReportWriter.create_master_analysis_summary`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-9CE7140637

- Level: `error`
- Message: `Error creating master analysis summary: {...}`
- Location: `app/agents/report_writer.py:140` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/report_writer.py#L140)
- Function: `ReportWriter.create_master_analysis_summary`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-384732C605

- Level: `debug`
- Message: `Using database prompt for {...}`
- Location: `app/agents/verify_agent.py:35` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L35)
- Function: `_get_prompt_from_db`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-370902654C

- Level: `warning`
- Message: `Failed to get prompt '{...}' from database: {...}`
- Location: `app/agents/verify_agent.py:38` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L38)
- Function: `_get_prompt_from_db`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-ACC354E60B

- Level: `info`
- Message: `Loaded {...} context rules from {...}`
- Location: `app/agents/verify_agent.py:109` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L109)
- Function: `RAGContextManager.load_context_rules`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-B4A8F9A5FC

- Level: `error`
- Message: `Error loading context rules: {...}`
- Location: `app/agents/verify_agent.py:112` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L112)
- Function: `RAGContextManager.load_context_rules`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-6C732E16A0

- Level: `info`
- Message: `Created default context file: {...}`
- Location: `app/agents/verify_agent.py:148` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L148)
- Function: `RAGContextManager.create_default_context_file`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-441D48E1DE

- Level: `error`
- Message: `Error creating default context file: {...}`
- Location: `app/agents/verify_agent.py:151` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L151)
- Function: `RAGContextManager.create_default_context_file`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-38AB59F72C

- Level: `info`
- Message: `RelevanceAnalyzerAgent initialized with model: {...}`
- Location: `app/agents/verify_agent.py:226` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L226)
- Function: `RelevanceAnalyzerAgent.__init__`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-052AA65FB3

- Level: `info`
- Message: `RAG context rules loaded: {...}`
- Location: `app/agents/verify_agent.py:227` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L227)
- Function: `RelevanceAnalyzerAgent.__init__`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-875A4C9C0C

- Level: `info`
- Message: `Starting batch relevance analysis for {...} files`
- Location: `app/agents/verify_agent.py:240` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L240)
- Function: `RelevanceAnalyzerAgent.analyze_batch_relevance`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-95149C5BBF

- Level: `info`
- Message: `Found {...} relevant context rules`
- Location: `app/agents/verify_agent.py:248` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L248)
- Function: `RelevanceAnalyzerAgent.analyze_batch_relevance`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-BF7EAA2029

- Level: `error`
- Message: `Error analyzing file {...}: {...}`
- Location: `app/agents/verify_agent.py:285` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L285)
- Function: `RelevanceAnalyzerAgent.analyze_batch_relevance`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-9A66CECCAE

- Level: `info`
- Message: `Processed batch {...}/{...}`
- Location: `app/agents/verify_agent.py:290` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L290)
- Function: `RelevanceAnalyzerAgent.analyze_batch_relevance`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-5BA7253CF6

- Level: `info`
- Message: `Analyzing relevance for file: {...}`
- Location: `app/agents/verify_agent.py:344` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L344)
- Function: `RelevanceAnalyzerAgent.analyze_single_file_relevance`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-163AC05D31

- Level: `info`
- Message: `Completed analysis for {...}: {...} (score: {...})`
- Location: `app/agents/verify_agent.py:413` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L413)
- Function: `RelevanceAnalyzerAgent.analyze_single_file_relevance`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-8896410743

- Level: `info`
- Message: `Using cached relevance analysis`
- Location: `app/agents/verify_agent.py:516` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L516)
- Function: `RelevanceAnalyzerAgent._analyze_relevance_with_rag`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-FED7DABD82

- Level: `error`
- Message: `Error in relevance analysis: {...}`
- Location: `app/agents/verify_agent.py:535` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L535)
- Function: `RelevanceAnalyzerAgent._analyze_relevance_with_rag`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-98EB00FBD2

- Level: `error`
- Message: `Error extracting trace info: {...}`
- Location: `app/agents/verify_agent.py:612` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L612)
- Function: `RelevanceAnalyzerAgent._extract_trace_info`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-A673E778D6

- Level: `error`
- Message: `Error reading file {...}: {...}`
- Location: `app/agents/verify_agent.py:637` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L637)
- Function: `RelevanceAnalyzerAgent._read_trace_file`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-4BC1D18F9B

- Level: `error`
- Message: `Safe JSON parse error: {...}`
- Location: `app/agents/verify_agent.py:788` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L788)
- Function: `RelevanceAnalyzerAgent._safe_parse_json`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-18B015648A

- Level: `info`
- Message: `Results exported to: {...}`
- Location: `app/agents/verify_agent.py:890` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L890)
- Function: `RelevanceAnalyzerAgent.export_results_to_file`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-9AE925B6DD

- Level: `error`
- Message: `Error exporting results: {...}`
- Location: `app/agents/verify_agent.py:894` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L894)
- Function: `RelevanceAnalyzerAgent.export_results_to_file`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-A98DEC8FC4

- Level: `info`
- Message: `Reloaded {...} context rules`
- Location: `app/agents/verify_agent.py:902` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L902)
- Function: `RelevanceAnalyzerAgent.reload_context_rules`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-ECFD934907

- Level: `info`
- Message: `Added new context rule: {...}`
- Location: `app/agents/verify_agent.py:920` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L920)
- Function: `RelevanceAnalyzerAgent.add_context_rule`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-EE269F5565

- Level: `error`
- Message: `Error adding context rule: {...}`
- Location: `app/agents/verify_agent.py:924` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L924)
- Function: `RelevanceAnalyzerAgent.add_context_rule`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-7796FCD875

- Level: `error`
- Message: `Error generating verification summary string from {...}: {...}`
- Location: `app/agents/verify_agent.py:966` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L966)
- Function: `RelevanceAnalyzerAgent.get_verification_summary_string`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-1043B68532

- Level: `error`
- Message: `Error generating detailed verification summary string from {...}: {...}`
- Location: `app/agents/verify_agent.py:1012` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L1012)
- Function: `RelevanceAnalyzerAgent.get_verification_summary_string_detailed`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-981BBD5231

- Level: `error`
- Message: `Error parsing results summary: {...}`
- Location: `app/agents/verify_agent.py:1077` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py#L1077)
- Function: `RelevanceAnalyzerAgent.parse_results_summary`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-6F1DBF2BED

- Level: `info`
- Message: `Initializing database schema: {...}`
- Location: `app/db/session.py:108` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/db/session.py#L108)
- Function: `init_database`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-1F8D485B34

- Level: `info`
- Message: `Created database schema: {...}`
- Location: `app/db/session.py:122` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/db/session.py#L122)
- Function: `init_database`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-DCCD447668

- Level: `info`
- Message: `Running database migrations...`
- Location: `app/db/session.py:125` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/db/session.py#L125)
- Function: `init_database`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-55ED68E28D

- Level: `info`
- Message: `Database migrations complete`
- Location: `app/db/session.py:128` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/db/session.py#L128)
- Function: `init_database`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-40DE631B12

- Level: `info`
- Message: `Database schema '{...}' exists`
- Location: `app/db/session.py:130` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/db/session.py#L130)
- Function: `init_database`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-8F2C469DE7

- Level: `info`
- Message: `Database migrations up to date`
- Location: `app/db/session.py:139` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/db/session.py#L139)
- Function: `init_database`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-BD3961B2DC

- Level: `warning`
- Message: `Database at version '{...}', run: uv run alembic upgrade head`
- Location: `app/db/session.py:141` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/db/session.py#L141)
- Function: `init_database`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-936E8AAE89

- Level: `warning`
- Message: `Migrations not applied. Run: uv run alembic upgrade head`
- Location: `app/db/session.py:143` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/db/session.py#L143)
- Function: `init_database`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-17245849DB

- Level: `error`
- Message: `Database initialization failed: {...}`
- Location: `app/db/session.py:146` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/db/session.py#L146)
- Function: `init_database`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-ECBCE3E2BF

- Level: `info`
- Message: `Running test case: {...}`
- Location: `app/evals/runner.py:143` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/runner.py#L143)
- Function: `PromptEvaluator._run_eval`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-EE9C4DCD18

- Level: `error`
- Message: `Error running test case {...}: {...}`
- Location: `app/evals/runner.py:164` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/runner.py#L164)
- Function: `PromptEvaluator._run_eval`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-CC05502518

- Level: `warning`
- Message: `Trace analysis eval requires full agent integration - using schema validation only`
- Location: `app/evals/runner.py:214` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/runner.py#L214)
- Function: `PromptEvaluator._run_eval_trace_analysis`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-F8D9A43505

- Level: `warning`
- Message: `Relevance analysis eval requires full agent integration - using schema validation only`
- Location: `app/evals/runner.py:233` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/runner.py#L233)
- Function: `PromptEvaluator._run_eval_relevance`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-6E37BF5D79

- Level: `error`
- Message: `Failed to save eval result: {...}`
- Location: `app/evals/runner.py:332` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/runner.py#L332)
- Function: `PromptEvaluator._save_result`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-EC3845AC70

- Level: `info`
- Message: `Running parameter extraction eval...`
- Location: `app/evals/runner.py:358` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/runner.py#L358)
- Function: `run_all_evals`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-19FD44520D

- Level: `info`
- Message: `Running trace analysis eval...`
- Location: `app/evals/runner.py:361` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/runner.py#L361)
- Function: `run_all_evals`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-B44D21749D

- Level: `info`
- Message: `Running relevance analysis eval...`
- Location: `app/evals/runner.py:364` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/runner.py#L364)
- Function: `run_all_evals`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-7E6D431DB3

- Level: `info`
- Message: `Saved eval run #{...} for {...} v{...}`
- Location: `app/evals/storage.py:65` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/storage.py#L65)
- Function: `EvalStorage.save_run`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-94478E59DA

- Level: `info`
- Message: `Deleted eval run #{...}`
- Location: `app/evals/storage.py:171` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/storage.py#L171)
- Function: `EvalStorage.delete_run`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-9A0D37E058

- Level: `debug`
- Message: `Generated plan: %s`
- Location: `app/orchestrator.py:88` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L88)
- Function: `Orchestrator.analyze_stream`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-FD8C111B07

- Level: `info`
- Message: `Analysis complete.`
- Location: `app/orchestrator.py:125` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L125)
- Function: `Orchestrator.analyze_stream`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-94C059F305

- Level: `warning`
- Message: `Negation rules file not found at {...}`
- Location: `app/orchestrator.py:143` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L143)
- Function: `Orchestrator._load_negate_keys`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-270112A9FB

- Level: `error`
- Message: `Error reading negate rules: {...}`
- Location: `app/orchestrator.py:145` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L145)
- Function: `Orchestrator._load_negate_keys`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-B661D5F53A

- Level: `info`
- Message: `STEP 1: Parameter extraction…`
- Location: `app/orchestrator.py:150` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L150)
- Function: `Orchestrator._step1_extract_parameters`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-BDC81E6366

- Level: `info`
- Message: `Extracted parameters: %s`
- Location: `app/orchestrator.py:152` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L152)
- Function: `Orchestrator._step1_extract_parameters`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-A9A3F7373E

- Level: `warning`
- Message: `Unknown project type: {...}`
- Location: `app/orchestrator.py:162` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L162)
- Function: `Orchestrator._step2_search_logs`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-647C42081C

- Level: `info`
- Message: `STEP 2: File search…`
- Location: `app/orchestrator.py:167` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L167)
- Function: `Orchestrator._step2_search_logs_file_based`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-0BE9EB66AD

- Level: `info`
- Message: `<dynamic message>`
- Location: `app/orchestrator.py:170` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L170)
- Function: `Orchestrator._step2_search_logs_file_based`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-ABC3283B7F

- Level: `info`
- Message: `STEP 2: Loki search…`
- Location: `app/orchestrator.py:175` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L175)
- Function: `Orchestrator._step2_search_logs_loki`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-BCC7090A22

- Level: `debug`
- Message: `Loki search: query_keys=%s, search_date=%s`
- Location: `app/orchestrator.py:178` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L178)
- Function: `Orchestrator._step2_search_logs_loki`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-A2E9E43605

- Level: `error`
- Message: `time_frame is None or empty - cannot proceed with Loki search without a date`
- Location: `app/orchestrator.py:182` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L182)
- Function: `Orchestrator._step2_search_logs_loki`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-DB09E9EE0A

- Level: `error`
- Message: `Failed to parse time_frame '%s': %s`
- Location: `app/orchestrator.py:188` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L188)
- Function: `Orchestrator._step2_search_logs_loki`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-B325D6CEAD

- Level: `debug`
- Message: `Loki search date range: %s to %s`
- Location: `app/orchestrator.py:193` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L193)
- Function: `Orchestrator._step2_search_logs_loki`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-DD44BCAEC3

- Level: `info`
- Message: `Downloaded logs to {...}`
- Location: `app/orchestrator.py:210` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L210)
- Function: `Orchestrator._step2_search_logs_loki`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-AF5963C026

- Level: `info`
- Message: `STEP 3: Trace ID collection…`
- Location: `app/orchestrator.py:215` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L215)
- Function: `Orchestrator._step3_collect_trace_ids`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-0BE9EB66AD

- Level: `info`
- Message: `<dynamic message>`
- Location: `app/orchestrator.py:231` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L231)
- Function: `Orchestrator._step3_collect_trace_ids_file_based`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-0BE9EB66AD

- Level: `info`
- Message: `<dynamic message>`
- Location: `app/orchestrator.py:237` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L237)
- Function: `Orchestrator._step3_collect_trace_ids_loki`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-151CB6F2F9

- Level: `info`
- Message: `STEP 4: Compiling full logs…`
- Location: `app/orchestrator.py:242` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L242)
- Function: `Orchestrator._step4_compile_logs`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-0BE9EB66AD

- Level: `info`
- Message: `<dynamic message>`
- Location: `app/orchestrator.py:274` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L274)
- Function: `Orchestrator._step4_compile_logs_file_based`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-0BE9EB66AD

- Level: `info`
- Message: `<dynamic message>`
- Location: `app/orchestrator.py:286` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L286)
- Function: `Orchestrator._step4_compile_logs_loki`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-F1A82D4CB4

- Level: `info`
- Message: `STEP 5: Verification & file gen…`
- Location: `app/orchestrator.py:291` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L291)
- Function: `Orchestrator._step5_analyze_and_generate_reports`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-ED9508CCBC

- Level: `info`
- Message: `STEP 6: Running verify agents with parameters and original text…`
- Location: `app/orchestrator.py:330` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py#L330)
- Function: `Orchestrator._step6_verify`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-FE96B5172C

- Level: `error`
- Message: `Error serializing payload for step {...}: {...}`
- Location: `app/routers/analysis.py:51` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/routers/analysis.py#L51)
- Function: `stream_analysis.event_generator`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-EAC270CEEA

- Level: `error`
- Message: `Error serializing payload for step {...}: {...}`
- Location: `app/routers/chat.py:97` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/routers/chat.py#L97)
- Function: `chat_stream.event_generator`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-F88B9A9A3F

- Level: `error`
- Message: `Error in chat stream: {...}`
- Location: `app/routers/chat.py:107` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/routers/chat.py#L107)
- Function: `chat_stream.event_generator`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-CE1A3F0F82

- Level: `warning`
- Message: `Failed to get setting {...}.{...} from DB: {...}`
- Location: `app/services/config_service.py:141` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/config_service.py#L141)
- Function: `ConfigService.get`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-42B49CEA96

- Level: `warning`
- Message: `Failed to get category {...} from DB: {...}`
- Location: `app/services/config_service.py:189` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/config_service.py#L189)
- Function: `ConfigService.get_category`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-F65DC2A712

- Level: `debug`
- Message: `LLM cache hit for {...}: {...}...`
- Location: `app/services/llm_cache.py:79` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/llm_cache.py#L79)
- Function: `get_cached_llm_response`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-F04446A060

- Level: `debug`
- Message: `LLM cache miss for {...}: {...}...`
- Location: `app/services/llm_cache.py:82` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/llm_cache.py#L82)
- Function: `get_cached_llm_response`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-604ADB7B0A

- Level: `debug`
- Message: `LLM response cached for {...}: {...}... (TTL: {...}s)`
- Location: `app/services/llm_cache.py:108` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/llm_cache.py#L108)
- Function: `cache_llm_response`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-6C422EF8F3

- Level: `info`
- Message: `All LLM caches invalidated`
- Location: `app/services/llm_cache.py:128` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/llm_cache.py#L128)
- Function: `invalidate_all_llm_caches`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-A0CF99AB10

- Level: `warning`
- Message: `Failed to get project {...} from DB: {...}`
- Location: `app/services/project_service.py:192` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/project_service.py#L192)
- Function: `ProjectService.get_project`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-AD953A0926

- Level: `warning`
- Message: `Failed to get environment {...}/{...} from DB: {...}`
- Location: `app/services/project_service.py:242` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/project_service.py#L242)
- Function: `ProjectService.get_environment`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-7DFEDA6DDF

- Level: `warning`
- Message: `Failed to list projects from DB: {...}`
- Location: `app/services/project_service.py:324` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/project_service.py#L324)
- Function: `ProjectService.list_projects`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-1EAF0F1275

- Level: `warning`
- Message: `Failed to list environments for {...} from DB: {...}`
- Location: `app/services/project_service.py:382` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/project_service.py#L382)
- Function: `ProjectService.list_environments`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-5DF19BBD93

- Level: `warning`
- Message: `Failed to get project setting {...}.{...} from DB: {...}`
- Location: `app/services/project_service.py:436` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/project_service.py#L436)
- Function: `ProjectService.get_project_setting`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-5623121AD0

- Level: `critical`
- Message: `Ollama not running; start with 'ollama serve'.`
- Location: `app/startup.py:37` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/startup.py#L37)
- Function: `lifespan`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-631F85833C

- Level: `info`
- Message: `Ollama is up and running`
- Location: `app/startup.py:39` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/startup.py#L39)
- Function: `lifespan`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-26E5BFEB3B

- Level: `info`
- Message: `Application shutting down`
- Location: `app/startup.py:44` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/startup.py#L44)
- Function: `lifespan`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-55819EEAD5

- Level: `info`
- Message: `Loki cache hit: {...}... -> {...}`
- Location: `app/tools/loki/loki_query_builder.py:274` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/loki/loki_query_builder.py#L274)
- Function: `download_logs_cached`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-09E9DDA765

- Level: `debug`
- Message: `Downloading Loki logs: {...}`
- Location: `app/tools/loki/loki_query_builder.py:312` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/loki/loki_query_builder.py#L312)
- Function: `download_logs_cached`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-37733BBFB4

- Level: `info`
- Message: `Loki logs cached: {...}... -> {...} (TTL: {...}s)`
- Location: `app/tools/loki/loki_query_builder.py:322` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/loki/loki_query_builder.py#L322)
- Function: `download_logs_cached`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-6F5D894BF3

- Level: `warning`
- Message: `Downloaded file is empty or missing: {...}`
- Location: `app/tools/loki/loki_query_builder.py:325` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/loki/loki_query_builder.py#L325)
- Function: `download_logs_cached`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-659220B7C9

- Level: `error`
- Message: `Error downloading Loki logs: {...}`
- Location: `app/tools/loki/loki_query_builder.py:329` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/loki/loki_query_builder.py#L329)
- Function: `download_logs_cached`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-67B00CB9C5

- Level: `error`
- Message: `Unexpected error in download_logs_cached: {...}`
- Location: `app/tools/loki/loki_query_builder.py:333` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/loki/loki_query_builder.py#L333)
- Function: `download_logs_cached`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-62846E631A

- Level: `debug`
- Message: `Removed cache file: {...}`
- Location: `app/tools/loki/loki_query_builder.py:364` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/loki/loki_query_builder.py#L364)
- Function: `clear_loki_cache`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-A266079379

- Level: `warning`
- Message: `Failed to remove cache file {...}: {...}`
- Location: `app/tools/loki/loki_query_builder.py:366` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/loki/loki_query_builder.py#L366)
- Function: `clear_loki_cache`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-C25D6B4D3D

- Level: `info`
- Message: `Cleared {...} Loki cache files`
- Location: `app/tools/loki/loki_query_builder.py:372` — [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/loki/loki_query_builder.py#L372)
- Function: `clear_loki_cache`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

<a id="glossary"></a>
## GLOSSARY (`docs/ai/GLOSSARY.md`)

# Glossary

- **Trace ID**: Identifier used to correlate related log lines across services and files.
- **Loki**: Grafana Loki log backend; used here as an optional log source.
- **Orchestrator**: The pipeline coordinator that calls agents/tools and streams progress events.
- **Agent**: An LLM-powered component that produces structured output (parameters, plan, analysis, verification).
- **Generated docs**: Files under `docs/ai/` produced by `python scripts/build_agent_docs.py`.
- **AI pack**: Single-file export `docs/ai/AI_PACK.md` built by `python scripts/export_ai_pack.py`.

<a id="repo-tree"></a>
## REPO_TREE (`docs/ai/REPO_TREE.md`)

# Repo tree (generated)

Excludes:
- `.git/`
- `.mypy_cache/`
- `.pytest_cache/`
- `.ruff_cache/`
- `.venv/`
- `__pycache__/`
- `build/`
- `dist/`
- `node_modules/`
- `site/`

```text
.
├── .claude/
│   └── settings.local.json
├── .github/
│   └── workflows/
│       ├── docs-ci.yml
│       └── docs-deploy.yml
├── .idea/
│   ├── dataSources/
│   │   ├── 562deee0-fd19-4a67-97cb-8e140a74b037/
│   │   │   └── storage_v2/
│   │   │       └── _src_/
│   │   │           └── database/
│   │   │               ├── agent_loggy.fH2Kdg/
│   │   │               │   └── schema/
│   │   │               │       ├── information_schema.FNRwLQ.meta
│   │   │               │       ├── log_chat.cxP_dw.meta
│   │   │               │       ├── log_chat.cxP_dw.zip
│   │   │               │       ├── pg_catalog.0S1ZNQ.meta
│   │   │               │       └── public.abK9xQ.meta
│   │   │               ├── postgres.edMnLQ/
│   │   │               │   └── schema/
│   │   │               │       ├── information_schema.FNRwLQ.meta
│   │   │               │       └── pg_catalog.0S1ZNQ.meta
│   │   │               ├── agent_loggy.fH2Kdg.meta
│   │   │               └── postgres.edMnLQ.meta
│   │   └── 562deee0-fd19-4a67-97cb-8e140a74b037.xml
│   ├── inspectionProfiles/
│   │   └── profiles_settings.xml
│   ├── queries/
│   │   └── Query.sql
│   ├── .gitignore
│   ├── agent-loggy.iml
│   ├── copilot.data.migration.ask2agent.xml
│   ├── dataSources.local.xml
│   ├── dataSources.xml
│   ├── data_source_mapping.xml
│   ├── misc.xml
│   ├── modules.xml
│   ├── sqldialects.xml
│   ├── vcs.xml
│   └── workspace.xml
├── alembic/
│   ├── versions/
│   │   ├── 1b671ff38c8c_initial_schema.py
│   │   ├── add_app_settings.py
│   │   ├── add_context_rules.py
│   │   ├── add_eval_tables.py
│   │   ├── add_projects.py
│   │   ├── add_prompts_versioned.py
│   │   ├── seed_initial_prompts.py
│   │   ├── setup_database.sql
│   │   └── update_parameter_extraction_prompt.py
│   ├── README
│   ├── env.py
│   └── script.py.mako
├── app/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── analyze_agent.py
│   │   ├── file_searcher.py
│   │   ├── parameter_agent.py
│   │   ├── planning_agent.py
│   │   ├── report_writer.py
│   │   └── verify_agent.py
│   ├── app_settings/
│   │   ├── context_rules.csv
│   │   └── negate_keys.csv
│   ├── comprehensive_analysis/
│   │   ├── master_summary_20251217_160732.txt
│   │   ├── master_summary_20251217_163119.txt
│   │   ├── master_summary_20251217_172315.txt
│   │   ├── master_summary_20251218_114607.txt
│   │   ├── trace_report_00aafe6e50eb_20251217_172315.txt
│   │   ├── trace_report_06015867d591_20251218_114344.txt
│   │   ├── trace_report_0991068ded60_20251218_114244.txt
│   │   ├── trace_report_0991068ded60_20251218_115804.txt
│   │   ├── trace_report_15ed3d710a80_20251217_162255.txt
│   │   ├── trace_report_1a2229ba0f20_20251217_160703.txt
│   │   ├── trace_report_1cc0772b748b_20251217_163105.txt
│   │   ├── trace_report_2297105debc3_20251217_160714.txt
│   │   ├── trace_report_242933b667dc_20251217_171557.txt
│   │   ├── trace_report_258a3f847f9f_20251217_162327.txt
│   │   ├── trace_report_324a29d1c936_20251218_114045.txt
│   │   ├── trace_report_324a29d1c936_20251218_115607.txt
│   │   ├── trace_report_32e404fafd83_20251217_162518.txt
│   │   ├── trace_report_34c66eab50b7_20251217_160711.txt
│   │   ├── trace_report_351a4864f120_20251218_113900.txt
│   │   ├── trace_report_351a4864f120_20251218_115500.txt
│   │   ├── trace_report_360ece980348_20251217_160651.txt
│   │   ├── trace_report_3b38dfb10d91_20251218_114311.txt
│   │   ├── trace_report_3b38dfb10d91_20251218_115815.txt
│   │   ├── trace_report_513185e23875_20251218_114139.txt
│   │   ├── trace_report_513185e23875_20251218_115653.txt
│   │   ├── trace_report_562100c36c53_20251217_171353.txt
│   │   ├── trace_report_5a28cbc40558_20251217_162003.txt
│   │   ├── trace_report_5f19919f259a_20251217_171613.txt
│   │   ├── trace_report_6141096fa86c_20251217_163047.txt
│   │   ├── trace_report_62800ceb2993_20251217_172029.txt
│   │   ├── trace_report_632768eabcfe_20251217_162121.txt
│   │   ├── trace_report_69d9136bec43_20251217_171433.txt
│   │   ├── trace_report_6c432ae6c8aa_20251217_160047.txt
│   │   ├── trace_report_6ca1a0a8ad7d_20251218_114607.txt
│   │   ├── trace_report_71e304d315f7_20251218_114420.txt
│   │   ├── trace_report_750dfff180ae_20251217_162226.txt
│   │   ├── trace_report_763cb3a0917c_20251217_162036.txt
│   │   ├── trace_report_77bfbfd5380c_20251218_114534.txt
│   │   ├── trace_report_7a5f52d68878_20251217_160732.txt
│   │   ├── trace_report_7b7e077b0758_20251217_160308.txt
│   │   ├── trace_report_7bdd113de360_20251218_114155.txt
│   │   ├── trace_report_7bdd113de360_20251218_115709.txt
│   │   ├── trace_report_849b16095de0_20251218_114111.txt
│   │   ├── trace_report_849b16095de0_20251218_115636.txt
│   │   ├── trace_report_85d94059a1dc_20251217_160658.txt
│   │   ├── trace_report_86f781ed8092_20251217_163050.txt
│   │   ├── trace_report_8d6656894c25_20251217_171305.txt
│   │   ├── trace_report_9b96eaa6008c_20251217_162054.txt
│   │   ├── trace_report_9c0f956cea60_20251217_163119.txt
│   │   ├── trace_report_9f5f71789e11_20251217_162107.txt
│   │   ├── trace_report_a0f54b817cd1_20251217_160730.txt
│   │   ├── trace_report_a4c2daf751c1_20251218_114403.txt
│   │   ├── trace_report_a53f3a128295_20251218_114056.txt
│   │   ├── trace_report_a53f3a128295_20251218_115623.txt
│   │   ├── trace_report_aa3b0cf97478_20251217_171715.txt
│   │   ├── trace_report_ad959b92516d_20251217_171542.txt
│   │   ├── trace_report_b0d0100b0e67_20251217_171649.txt
│   │   ├── trace_report_b30e20f27beb_20251217_160726.txt
│   │   ├── trace_report_b39327c7d191_20251217_160712.txt
│   │   ├── trace_report_b5734b92bbc1_20251217_160716.txt
│   │   ├── trace_report_b7d1ffa3416f_20251218_114459.txt
│   │   ├── trace_report_b810ebd2afeb_20251217_163112.txt
│   │   ├── trace_report_b923067cbb63_20251217_172032.txt
│   │   ├── trace_report_ba189bd71319_20251217_171631.txt
│   │   ├── trace_report_c1b9c7a808de_20251217_162015.txt
│   │   ├── trace_report_c5e85dbfe220_20251217_162310.txt
│   │   ├── trace_report_c6b16718f881_20251217_172026.txt
│   │   ├── trace_report_c79f021d2bc3_20251217_162435.txt
│   │   ├── trace_report_ca8608a5b4dc_20251218_114516.txt
│   │   ├── trace_report_ca9360501db8_20251217_162146.txt
│   │   ├── trace_report_d41a1fd5e96a_20251217_160722.txt
│   │   ├── trace_report_d7cea32cbd13_20251217_160107.txt
│   │   ├── trace_report_dc65cf904b19_20251218_114442.txt
│   │   ├── trace_report_de0530e5a12e_20251217_163115.txt
│   │   ├── trace_report_e01e9e3f8014_20251217_172035.txt
│   │   ├── trace_report_e0201d6e1e20_20251218_114322.txt
│   │   ├── trace_report_e3760e7423f1_20251217_160656.txt
│   │   ├── trace_report_e4c89fef519e_20251218_114223.txt
│   │   ├── trace_report_e4c89fef519e_20251218_115751.txt
│   │   ├── trace_report_e50a248cb0a4_20251217_171152.txt
│   │   ├── trace_report_ea91ed0ca093_20251218_113957.txt
│   │   ├── trace_report_ea91ed0ca093_20251218_115553.txt
│   │   ├── trace_report_edbcb71553cc_20251218_113920.txt
│   │   ├── trace_report_edbcb71553cc_20251218_115516.txt
│   │   ├── trace_report_eebdd2958400_20251218_113938.txt
│   │   ├── trace_report_eebdd2958400_20251218_115528.txt
│   │   ├── trace_report_f0a7a7c8b0d0_20251217_163058.txt
│   │   ├── trace_report_fe6e71546cf4_20251217_162134.txt
│   │   ├── trace_report_ffd4bca1acdb_20251218_114206.txt
│   │   └── trace_report_ffd4bca1acdb_20251218_115739.txt
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── session.py
│   ├── evals/
│   │   ├── datasets/
│   │   │   ├── parameter_extraction.json
│   │   │   ├── relevance_analysis.json
│   │   │   └── trace_analysis.json
│   │   ├── __init__.py
│   │   ├── cli.py
│   │   ├── metrics.py
│   │   ├── models.py
│   │   ├── runner.py
│   │   └── storage.py
│   ├── loki_logs/
│   │   ├── NCCDEV_2025-12-17_10842cf5364a4ee18524d493fd589fbe.json
│   │   ├── NCCDEV_2025-12-17_66db4ce52bcb4416a793c511b6fb93ec.json
│   │   ├── NCCDEV_2025-12-17_9b8cb3b119404f7c9253938ff0dd94c4.json
│   │   ├── NCCDEV_2025-12-17_e9c81da6d2004c61ab8dcd859315c26c.json
│   │   └── NCCDEV_2025-12-17_fd962ee7f1f34e9ab2e14909e9a74526.json
│   ├── models/
│   │   ├── __init__.py
│   │   ├── context_rule.py
│   │   ├── project.py
│   │   ├── prompt.py
│   │   └── settings.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── analysis.py
│   │   ├── chat.py
│   │   └── files.py
│   ├── schemas/
│   │   ├── ChatRequest.py
│   │   ├── ChatResponse.py
│   │   ├── StreamRequest.py
│   │   └── __init__.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── cache.py
│   │   ├── config_service.py
│   │   ├── llm_cache.py
│   │   ├── project_service.py
│   │   └── prompt_service.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_cache.py
│   │   ├── test_planning_agent.py
│   │   └── test_trace_id_extractor.py
│   ├── tools/
│   │   ├── loki/
│   │   │   ├── __init__.py
│   │   │   ├── loki_log_analyser.py
│   │   │   ├── loki_log_report_generator.py
│   │   │   ├── loki_query_builder.py
│   │   │   └── loki_trace_id_extractor.py
│   │   ├── __init__.py
│   │   ├── full_log_finder.py
│   │   ├── log_searcher.py
│   │   └── trace_id_extractor.py
│   ├── trace_logs/
│   │   ├── trace_00aafe6e50eb23a057665e8ab8f7233f.json
│   │   ├── trace_06015867d5910b3594044ca6bc319e05.json
│   │   ├── trace_0991068ded600215196d6d0a305e8281.json
│   │   ├── trace_15ed3d710a8080644106297304eeed4e.json
│   │   ├── trace_1a2229ba0f2048266e82d0eb1722e1cb.json
│   │   ├── trace_1cc0772b748bac5d1ec82bd8e7abdd15.json
│   │   ├── trace_2297105debc32fdb65edea9e93c0e4cf.json
│   │   ├── trace_242933b667dcc8f61f814d756799022c.json
│   │   ├── trace_258a3f847f9fdfa543f3d0001fa867ec.json
│   │   ├── trace_324a29d1c9367c0b54a401bbd9788ed3.json
│   │   ├── trace_32e404fafd83cf127f47a2984359d147.json
│   │   ├── trace_34c66eab50b7e2813c867606b1f2099f.json
│   │   ├── trace_351a4864f120a26fe0bb85c584d7af02.json
│   │   ├── trace_360ece980348b9f226aec90007f8085d.json
│   │   ├── trace_3b38dfb10d919627cd9e240f7a8348e5.json
│   │   ├── trace_513185e23875e313025e5af6bac79c3d.json
│   │   ├── trace_562100c36c53f205df6a06cb6980c604.json
│   │   ├── trace_5a28cbc405585c5abe383ecc11d00572.json
│   │   ├── trace_5f19919f259a1cf3db3bcb0431e54e35.json
│   │   ├── trace_6141096fa86ce7d3d72f15d62f5e231d.json
│   │   ├── trace_62800ceb2993b389dab37ae33999b678.json
│   │   ├── trace_632768eabcfeb79b00fe712d247d7446.json
│   │   ├── trace_69d9136bec433f69dd7724913aa2c972.json
│   │   ├── trace_6c432ae6c8aaa04d73a0346efd786d09.json
│   │   ├── trace_6ca1a0a8ad7d897422525b17b063bba3.json
│   │   ├── trace_71e304d315f7781b3340773f50d007f5.json
│   │   ├── trace_750dfff180aec28cd1c8cdf46e6f83e4.json
│   │   ├── trace_763cb3a0917c3594c1a6eacde4db12d6.json
│   │   ├── trace_77bfbfd5380c8f0ab9d9b44ccd1408b7.json
│   │   ├── trace_7a5f52d6887868eda0fc1771340f8626.json
│   │   ├── trace_7b7e077b07585dfbf5166c133afed6b6.json
│   │   ├── trace_7bdd113de360951356da69f67102986c.json
│   │   ├── trace_849b16095de0ccc4f8101c9cfd1dc9f3.json
│   │   ├── trace_85d94059a1dcb04195e1144085562101.json
│   │   ├── trace_86f781ed809219f76144d0da04339db9.json
│   │   ├── trace_8d6656894c252464133db3c1a958a986.json
│   │   ├── trace_9b96eaa6008c64c99ac30ba516833d0c.json
│   │   ├── trace_9c0f956cea607e25f40c06f53c846bb0.json
│   │   ├── trace_9f5f71789e11ed02ef98f5e3154b02b6.json
│   │   ├── trace_a0f54b817cd1a2f728b83b3be70e9132.json
│   │   ├── trace_a4c2daf751c1043b973975b822f3a5bd.json
│   │   ├── trace_a53f3a128295f1edbf7149dba7edfaec.json
│   │   ├── trace_aa3b0cf9747856bccee5ff94a1473ecd.json
│   │   ├── trace_ad959b92516d48e634d903070277e1c0.json
│   │   ├── trace_b0d0100b0e67920b8c05debbfc7b3155.json
│   │   ├── trace_b30e20f27beb79adaf3cd4175cf205e5.json
│   │   ├── trace_b39327c7d19154f7f0bab66a73dd751b.json
│   │   ├── trace_b5734b92bbc188039aaef2c176cd2455.json
│   │   ├── trace_b7d1ffa3416f5c45898204d98ce36951.json
│   │   ├── trace_b810ebd2afeb5e8ca45af5a2b2a7f26b.json
│   │   ├── trace_b923067cbb6344e7ddbc8ebb8326a115.json
│   │   ├── trace_ba189bd713192d9be2da5bdb1a8795c5.json
│   │   ├── trace_c1b9c7a808de3e8b245f94aa81a949fa.json
│   │   ├── trace_c5e85dbfe220fc976d17948ea13803a0.json
│   │   ├── trace_c6b16718f881e387950cc5f930bb8500.json
│   │   ├── trace_c79f021d2bc3bc43248d3a3536875cf5.json
│   │   ├── trace_ca8608a5b4dc0cd559636e85a65ce3e5.json
│   │   ├── trace_ca9360501db8ac2d73750925666aee64.json
│   │   ├── trace_d41a1fd5e96a799bb7f7d4f2e016eedc.json
│   │   ├── trace_d7cea32cbd1331b8677d3b8fafe1ddb8.json
│   │   ├── trace_dc65cf904b19d650ad33f07f4e27a943.json
│   │   ├── trace_de0530e5a12e8759955590dbff7bca5a.json
│   │   ├── trace_e01e9e3f8014126c54299aad1645527b.json
│   │   ├── trace_e0201d6e1e2037758e30f83e45f365d6.json
│   │   ├── trace_e3760e7423f1bcad0517bbf73145aba4.json
│   │   ├── trace_e4c89fef519eca2ccda1bd377a1c6e40.json
│   │   ├── trace_e50a248cb0a4069a528ce8970e3d1963.json
│   │   ├── trace_ea91ed0ca09347226d41d3d4637438b3.json
│   │   ├── trace_edbcb71553ccb15e6fd1afc56ff50b17.json
│   │   ├── trace_eebdd2958400732475b1292f28e5ab03.json
│   │   ├── trace_f0a7a7c8b0d0f7184283856b1d06e868.json
│   │   ├── trace_fe6e71546cf4ed5ac42fe3dfceaf10be.json
│   │   └── trace_ffd4bca1acdb7fe9a3e04196d4578c83.json
│   ├── verification_reports/
│   │   ├── relevance_analysis_20251217_161002.json
│   │   ├── relevance_analysis_20251217_163235.json
│   │   └── relevance_analysis_20251217_172407.json
│   ├── __init__.py
│   ├── config.py
│   ├── dependencies.py
│   ├── main.py
│   ├── orchestrator.py
│   └── startup.py
├── docs/
│   ├── ai/
│   │   ├── DECISIONS/
│   │   │   └── ADR-0001-docs-and-agent-pack.md
│   │   ├── ARCHITECTURE.md
│   │   ├── ENTRYPOINT.md
│   │   ├── GLOSSARY.md
│   │   ├── QUALITY_BAR.md
│   │   └── index.md
│   ├── reference/
│   │   └── index.md
│   ├── API.md
│   ├── ARCHITECTURE.md
│   ├── DEVELOPMENT.md
│   ├── README.md
│   ├── db-config-migration-plan.md
│   ├── db-config-migration-todo.md
│   ├── index.md
│   ├── memory.md
│   ├── rag-implementation-plan.md
│   ├── schema-setup-guide.md
│   ├── session.md
│   └── specs.md
├── scripts/
│   ├── build_agent_docs.py
│   ├── check_docs_fresh.py
│   ├── create_schema.py
│   ├── drop_schema.py
│   ├── export_ai_pack.py
│   ├── seed_projects.py
│   ├── seed_prompts.py
│   ├── seed_settings.py
│   └── verify_schema.py
├── .env
├── .gitignore
├── CLAUDE.md
├── Dockerfile
├── README.md
├── alembic.ini
├── context_rules.csv
├── docker-compose.yml
├── meta_postgres_sql.txt
├── mkdocs.yml
├── pyproject.toml
├── requirements-docs.txt
└── uv.lock
```

<a id="quality-bar"></a>
## QUALITY_BAR (`docs/ai/QUALITY_BAR.md`)

# Quality bar (agent docs)

These docs are considered “good” when an AI agent can locate code responsibilities quickly and answer “where should this change go?” without opening the source tree.

## Acceptance checks

- `mkdocs build --strict` passes.
- `python scripts/check_docs_fresh.py` exits 0 in CI.
- `docs/ai/MODULE_INDEX.md` contains:
  - stable module list (sorted)
  - brief summaries derived from docstrings/file headers (best-effort)
- `docs/ai/CONFIG_REFERENCE.md` contains:
  - stable IDs (`CFG-...`)
  - keys, defaults (best-effort), and file references
- `docs/ai/LOG_CATALOG.md` contains:
  - stable IDs (`LOG-...`)
  - message templates and file references
- `docs/ai/REPO_TREE.md` is readable and excludes large build/cache directories.

## Change discipline

- Keep hand-authored docs short and link-heavy.
- Prefer stable headings and sorted lists to keep diffs small.

<a id="adr-0001"></a>
## ADR-0001 (`docs/ai/DECISIONS/ADR-0001-docs-and-agent-pack.md`)

# ADR-0001: Docs and AI research pack

## Status

Accepted

## Context

AI agents working on this repo need a fast way to understand structure, config surface, and log semantics without crawling the entire source tree.

We also want CI to enforce that these agent docs are always up to date.

## Decision

We maintain:

- A MkDocs (Material) site for humans + agents.
- A small set of hand-authored “entry” docs (Entrypoint/Architecture/Glossary/Quality bar/ADRs).
- A deterministic generator that produces:
  - repo tree
  - module index (from docstrings/file headers)
  - config reference (env var discovery)
  - log catalog (logging call discovery)
- A single-file export (`docs/ai/AI_PACK.md`) for retrieval and offline use.

CI fails if any generated artifact is stale.

## Consequences

- Any change that affects modules/config/logging should be accompanied by regenerated agent docs.
- Generated files should remain stable (sorted, deterministic) to keep diffs small.
