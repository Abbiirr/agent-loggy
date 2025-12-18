<!-- Pack version: 587e82e13aa226d1827d16cbcffa9e92a2ed75d2 -->
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
| `app` | `app/__init__.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/__init__.py) |
| `app.agents` | `app/agents/__init__.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/__init__.py) |
| `app.agents.analyze_agent` | `app/agents/analyze_agent.py` | agents/analyze_agent.py - Refactored version focusing on analysis generation | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py) |
| `app.agents.file_searcher` | `app/agents/file_searcher.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py) |
| `app.agents.parameter_agent` | `app/agents/parameter_agent.py` | parameters_agent.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/parameter_agent.py) |
| `app.agents.planning_agent` | `app/agents/planning_agent.py` | Stubbed PlanningAgent: not used in current orchestration | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/planning_agent.py) |
| `app.agents.report_writer` | `app/agents/report_writer.py` | agents/report_writer.py - Handles all report generation and file writing | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/report_writer.py) |
| `app.agents.verify_agent` | `app/agents/verify_agent.py` | agents/verify_agent.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py) |
| `app.config` | `app/config.py` | app/core/config.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/config.py) |
| `app.db` | `app/db/__init__.py` | app/db/__init__.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/db/__init__.py) |
| `app.db.base` | `app/db/base.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/db/base.py) |
| `app.db.session` | `app/db/session.py` | SQLAlchemy session factory with FastAPI dependency injection. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/db/session.py) |
| `app.dependencies` | `app/dependencies.py` | Shared dependencies for FastAPI routes. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/dependencies.py) |
| `app.main` | `app/main.py` | main.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/main.py) |
| `app.models` | `app/models/__init__.py` | app/models/__init__.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/models/__init__.py) |
| `app.models.project` | `app/models/project.py` | SQLAlchemy models for project configuration. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/models/project.py) |
| `app.models.prompt` | `app/models/prompt.py` | SQLAlchemy models for versioned prompts with history tracking. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/models/prompt.py) |
| `app.models.settings` | `app/models/settings.py` | SQLAlchemy models for application settings with history tracking. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/models/settings.py) |
| `app.orchestrator` | `app/orchestrator.py` | orchestrator.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py) |
| `app.routers` | `app/routers/__init__.py` | API routers for agent-loggy. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/routers/__init__.py) |
| `app.routers.analysis` | `app/routers/analysis.py` | Analysis API routes for log analysis streaming. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/routers/analysis.py) |
| `app.routers.chat` | `app/routers/chat.py` | Chat API routes for the React ChatInterface. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/routers/chat.py) |
| `app.routers.files` | `app/routers/files.py` | File download API routes. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/routers/files.py) |
| `app.schemas` | `app/schemas/__init__.py` | schemas/__init__.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/schemas/__init__.py) |
| `app.schemas.ChatRequest` | `app/schemas/ChatRequest.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/schemas/ChatRequest.py) |
| `app.schemas.ChatResponse` | `app/schemas/ChatResponse.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/schemas/ChatResponse.py) |
| `app.schemas.StreamRequest` | `app/schemas/StreamRequest.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/schemas/StreamRequest.py) |
| `app.services` | `app/services/__init__.py` | app/services/__init__.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/services/__init__.py) |
| `app.services.cache` | `app/services/cache.py` | TTL-based caching infrastructure with thread-safe in-memory caching. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/services/cache.py) |
| `app.services.config_service` | `app/services/config_service.py` | Service layer for application configuration management with caching and fallback defaults. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/services/config_service.py) |
| `app.services.project_service` | `app/services/project_service.py` | Service layer for project configuration management with caching and fallback defaults. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/services/project_service.py) |
| `app.services.prompt_service` | `app/services/prompt_service.py` | Service layer for versioned prompt management with caching and hot-reload support. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/services/prompt_service.py) |
| `app.startup` | `app/startup.py` | Application startup logic and health checks. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/startup.py) |
| `app.tests` | `app/tests/__init__.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tests/__init__.py) |
| `app.tests.test_cache` | `app/tests/test_cache.py` | Tests for the TTLCache and CacheManager classes. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tests/test_cache.py) |
| `app.tests.test_trace_id_extractor` | `app/tests/test_trace_id_extractor.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tests/test_trace_id_extractor.py) |
| `app.tools` | `app/tools/__init__.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tools/__init__.py) |
| `app.tools.full_log_finder` | `app/tools/full_log_finder.py` | tools/full_log_finder.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tools/full_log_finder.py) |
| `app.tools.log_searcher` | `app/tools/log_searcher.py` | tools/log_searcher.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tools/log_searcher.py) |
| `app.tools.loki` | `app/tools/loki/__init__.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tools/loki/__init__.py) |
| `app.tools.loki.loki_log_analyser` | `app/tools/loki/loki_log_analyser.py` | log_compiler.py: Library for compiling Loki and application logs into human-readable timeline reports. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tools/loki/loki_log_analyser.py) |
| `app.tools.loki.loki_log_report_generator` | `app/tools/loki/loki_log_report_generator.py` | log_compiler.py: Library for compiling Loki and application logs into human-readable comprehensive timeline reports. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tools/loki/loki_log_report_generator.py) |
| `app.tools.loki.loki_query_builder` | `app/tools/loki/loki_query_builder.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tools/loki/loki_query_builder.py) |
| `app.tools.loki.loki_trace_id_extractor` | `app/tools/loki/loki_trace_id_extractor.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tools/loki/loki_trace_id_extractor.py) |
| `app.tools.trace_id_extractor` | `app/tools/trace_id_extractor.py` | tools/trace_id_extractor.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tools/trace_id_extractor.py) |

<a id="config-reference"></a>
## CONFIG_REFERENCE (`docs/ai/CONFIG_REFERENCE.md`)

# Config reference (generated)

Best-effort discovery of config keys and environment variables.

## CFG-01465D6DE8: `ANALYSIS_DIR`

- Defaults: (not detected)
- References:
  - `app/config.py:11` (BaseSettings field) — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/config.py#L11)

## CFG-3380C1D399: `DATABASE_SCHEMA`

- Defaults: (not detected)
- References:
  - `app/config.py:9` (BaseSettings field) — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/config.py#L9)

## CFG-01D2F16EDF: `DATABASE_URL`

- Defaults: (not detected)
- References:
  - `app/config.py:8` (BaseSettings field) — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/config.py#L8)

## CFG-AAC8C77084: `MODEL`

- Defaults: (not detected)
- References:
  - `app/config.py:12` (BaseSettings field) — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/config.py#L12)

## CFG-939C1EF9F2: `OLLAMA_HOST`

- Defaults: (not detected)
- References:
  - `app/config.py:10` (BaseSettings field) — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/config.py#L10)

## CFG-5E8EAEE750: `USE_DB_PROJECTS`

- Defaults:
  - `False`
- References:
  - `app/config.py:17` (BaseSettings field) — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/config.py#L17)

## CFG-8CC89E6356: `USE_DB_PROMPTS`

- Defaults:
  - `False`
- References:
  - `app/config.py:15` (BaseSettings field) — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/config.py#L15)

## CFG-3F064F9B7A: `USE_DB_SETTINGS`

- Defaults:
  - `False`
- References:
  - `app/config.py:16` (BaseSettings field) — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/config.py#L16)

<a id="log-catalog"></a>
## LOG_CATALOG (`docs/ai/LOG_CATALOG.md`)

# Log catalog (generated)

Best-effort extraction of log message templates from Python logging calls.

## LOG-D633474910

- Level: `debug`
- Message: `Using database prompt for {...}`
- Location: `app/agents/analyze_agent.py:28` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L28)
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
- Location: `app/agents/analyze_agent.py:31` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L31)
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
- Location: `app/agents/analyze_agent.py:50` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L50)
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
- Location: `app/agents/analyze_agent.py:73` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L73)
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
- Location: `app/agents/analyze_agent.py:77` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L77)
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
- Location: `app/agents/analyze_agent.py:88` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L88)
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
- Location: `app/agents/analyze_agent.py:104` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L104)
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
- Location: `app/agents/analyze_agent.py:131` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L131)
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
- Location: `app/agents/analyze_agent.py:132` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L132)
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
- Location: `app/agents/analyze_agent.py:158` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L158)
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
- Location: `app/agents/analyze_agent.py:166` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L166)
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
- Location: `app/agents/analyze_agent.py:168` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L168)
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
- Location: `app/agents/analyze_agent.py:175` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L175)
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
- Location: `app/agents/analyze_agent.py:195` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L195)
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
- Location: `app/agents/analyze_agent.py:198` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L198)
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
- Location: `app/agents/analyze_agent.py:206` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L206)
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
- Location: `app/agents/analyze_agent.py:209` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L209)
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
- Location: `app/agents/analyze_agent.py:224` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L224)
- Function: `AnalyzeAgent.analyze_log_files`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-200982701E

- Level: `error`
- Message: `Error analyzing trace {...}: {...}`
- Location: `app/agents/analyze_agent.py:340` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L340)
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
- Location: `app/agents/analyze_agent.py:417` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L417)
- Function: `AnalyzeAgent._analyze_single_trace_from_entries`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-DB709BD7EC

- Level: `error`
- Message: `Error in overall quality assessment: {...}`
- Location: `app/agents/analyze_agent.py:463` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L463)
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
- Location: `app/agents/analyze_agent.py:525` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py#L525)
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
- Location: `app/agents/file_searcher.py:52` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L52)
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
- Location: `app/agents/file_searcher.py:58` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L58)
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
- Location: `app/agents/file_searcher.py:61` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L61)
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
- Location: `app/agents/file_searcher.py:62` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L62)
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
- Location: `app/agents/file_searcher.py:67` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L67)
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
- Location: `app/agents/file_searcher.py:71` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L71)
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
- Location: `app/agents/file_searcher.py:75` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L75)
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
- Location: `app/agents/file_searcher.py:79` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L79)
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
- Location: `app/agents/file_searcher.py:83` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L83)
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
- Location: `app/agents/file_searcher.py:86` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L86)
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
- Location: `app/agents/file_searcher.py:88` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L88)
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
- Location: `app/agents/file_searcher.py:90` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L90)
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
- Location: `app/agents/file_searcher.py:93` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L93)
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
- Location: `app/agents/file_searcher.py:95` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L95)
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
- Location: `app/agents/file_searcher.py:97` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L97)
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
- Location: `app/agents/file_searcher.py:104` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L104)
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
- Location: `app/agents/file_searcher.py:105` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L105)
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
- Location: `app/agents/file_searcher.py:106` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L106)
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
- Location: `app/agents/file_searcher.py:109` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L109)
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
- Location: `app/agents/file_searcher.py:114` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L114)
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
- Location: `app/agents/file_searcher.py:117` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L117)
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
- Location: `app/agents/file_searcher.py:119` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L119)
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
- Location: `app/agents/file_searcher.py:123` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L123)
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
- Location: `app/agents/file_searcher.py:125` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L125)
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
- Location: `app/agents/file_searcher.py:128` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L128)
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
- Location: `app/agents/file_searcher.py:153` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L153)
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
- Location: `app/agents/file_searcher.py:165` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L165)
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
- Location: `app/agents/file_searcher.py:172` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L172)
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
- Location: `app/agents/file_searcher.py:178` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L178)
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
- Location: `app/agents/file_searcher.py:185` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L185)
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
- Location: `app/agents/file_searcher.py:188` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L188)
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
- Location: `app/agents/file_searcher.py:191` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L191)
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
- Location: `app/agents/file_searcher.py:208` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L208)
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
- Location: `app/agents/file_searcher.py:221` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L221)
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
- Location: `app/agents/file_searcher.py:281` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L281)
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
- Location: `app/agents/file_searcher.py:284` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py#L284)
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
- Location: `app/agents/parameter_agent.py:29` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/parameter_agent.py#L29)
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
- Location: `app/agents/parameter_agent.py:123` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/parameter_agent.py#L123)
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
- Location: `app/agents/parameter_agent.py:143` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/parameter_agent.py#L143)
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
- Location: `app/agents/parameter_agent.py:150` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/parameter_agent.py#L150)
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
- Location: `app/agents/parameter_agent.py:169` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/parameter_agent.py#L169)
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
- Location: `app/agents/parameter_agent.py:174` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/parameter_agent.py#L174)
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
- Location: `app/agents/parameter_agent.py:176` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/parameter_agent.py#L176)
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
- Location: `app/agents/parameter_agent.py:178` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/parameter_agent.py#L178)
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
- Location: `app/agents/parameter_agent.py:179` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/parameter_agent.py#L179)
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
- Location: `app/agents/parameter_agent.py:181` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/parameter_agent.py#L181)
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
- Location: `app/agents/parameter_agent.py:184` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/parameter_agent.py#L184)
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
- Location: `app/agents/parameter_agent.py:242` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/parameter_agent.py#L242)
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
- Location: `app/agents/parameter_agent.py:244` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/parameter_agent.py#L244)
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
- Location: `app/agents/parameter_agent.py:246` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/parameter_agent.py#L246)
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
- Location: `app/agents/parameter_agent.py:285` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/parameter_agent.py#L285)
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
- Location: `app/agents/parameter_agent.py:453` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/parameter_agent.py#L453)
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
- Location: `app/agents/parameter_agent.py:455` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/parameter_agent.py#L455)
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
- Location: `app/agents/parameter_agent.py:457` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/parameter_agent.py#L457)
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
- Location: `app/agents/parameter_agent.py:459` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/parameter_agent.py#L459)
- Function: `ParametersAgent._fallback`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-A32490A347

- Level: `info`
- Message: `ReportWriter initialized with output directory: {...}`
- Location: `app/agents/report_writer.py:22` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/report_writer.py#L22)
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
- Location: `app/agents/report_writer.py:50` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/report_writer.py#L50)
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
- Location: `app/agents/report_writer.py:54` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/report_writer.py#L54)
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
- Location: `app/agents/report_writer.py:81` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/report_writer.py#L81)
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
- Location: `app/agents/report_writer.py:85` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/report_writer.py#L85)
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
- Location: `app/agents/report_writer.py:109` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/report_writer.py#L109)
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
- Location: `app/agents/report_writer.py:113` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/report_writer.py#L113)
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
- Location: `app/agents/report_writer.py:136` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/report_writer.py#L136)
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
- Location: `app/agents/report_writer.py:140` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/report_writer.py#L140)
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
- Location: `app/agents/verify_agent.py:31` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L31)
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
- Location: `app/agents/verify_agent.py:34` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L34)
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
- Location: `app/agents/verify_agent.py:105` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L105)
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
- Location: `app/agents/verify_agent.py:108` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L108)
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
- Location: `app/agents/verify_agent.py:144` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L144)
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
- Location: `app/agents/verify_agent.py:147` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L147)
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
- Location: `app/agents/verify_agent.py:222` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L222)
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
- Location: `app/agents/verify_agent.py:223` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L223)
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
- Location: `app/agents/verify_agent.py:236` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L236)
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
- Location: `app/agents/verify_agent.py:244` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L244)
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
- Location: `app/agents/verify_agent.py:281` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L281)
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
- Location: `app/agents/verify_agent.py:286` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L286)
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
- Location: `app/agents/verify_agent.py:340` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L340)
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
- Location: `app/agents/verify_agent.py:409` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L409)
- Function: `RelevanceAnalyzerAgent.analyze_single_file_relevance`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-FED7DABD82

- Level: `error`
- Message: `Error in relevance analysis: {...}`
- Location: `app/agents/verify_agent.py:525` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L525)
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
- Location: `app/agents/verify_agent.py:602` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L602)
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
- Location: `app/agents/verify_agent.py:627` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L627)
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
- Location: `app/agents/verify_agent.py:778` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L778)
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
- Location: `app/agents/verify_agent.py:880` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L880)
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
- Location: `app/agents/verify_agent.py:884` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L884)
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
- Location: `app/agents/verify_agent.py:892` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L892)
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
- Location: `app/agents/verify_agent.py:910` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L910)
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
- Location: `app/agents/verify_agent.py:914` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L914)
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
- Location: `app/agents/verify_agent.py:956` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L956)
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
- Location: `app/agents/verify_agent.py:1002` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L1002)
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
- Location: `app/agents/verify_agent.py:1067` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py#L1067)
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
- Location: `app/db/session.py:108` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/db/session.py#L108)
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
- Location: `app/db/session.py:122` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/db/session.py#L122)
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
- Location: `app/db/session.py:125` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/db/session.py#L125)
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
- Location: `app/db/session.py:128` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/db/session.py#L128)
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
- Location: `app/db/session.py:130` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/db/session.py#L130)
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
- Location: `app/db/session.py:139` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/db/session.py#L139)
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
- Location: `app/db/session.py:141` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/db/session.py#L141)
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
- Location: `app/db/session.py:143` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/db/session.py#L143)
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
- Location: `app/db/session.py:146` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/db/session.py#L146)
- Function: `init_database`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-FD8C111B07

- Level: `info`
- Message: `Analysis complete.`
- Location: `app/orchestrator.py:107` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L107)
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
- Location: `app/orchestrator.py:125` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L125)
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
- Location: `app/orchestrator.py:127` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L127)
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
- Location: `app/orchestrator.py:132` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L132)
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
- Location: `app/orchestrator.py:134` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L134)
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
- Location: `app/orchestrator.py:144` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L144)
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
- Location: `app/orchestrator.py:149` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L149)
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
- Location: `app/orchestrator.py:152` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L152)
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
- Location: `app/orchestrator.py:157` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L157)
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
- Location: `app/orchestrator.py:160` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L160)
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
- Location: `app/orchestrator.py:164` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L164)
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
- Location: `app/orchestrator.py:170` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L170)
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
- Location: `app/orchestrator.py:175` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L175)
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
- Location: `app/orchestrator.py:188` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L188)
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
- Location: `app/orchestrator.py:193` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L193)
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
- Location: `app/orchestrator.py:209` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L209)
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
- Location: `app/orchestrator.py:215` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L215)
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
- Location: `app/orchestrator.py:220` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L220)
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
- Location: `app/orchestrator.py:252` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L252)
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
- Location: `app/orchestrator.py:264` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L264)
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
- Location: `app/orchestrator.py:269` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L269)
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
- Location: `app/orchestrator.py:308` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py#L308)
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
- Location: `app/routers/analysis.py:51` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/routers/analysis.py#L51)
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
- Location: `app/routers/chat.py:91` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/routers/chat.py#L91)
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
- Location: `app/routers/chat.py:99` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/routers/chat.py#L99)
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
- Location: `app/services/config_service.py:141` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/services/config_service.py#L141)
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
- Location: `app/services/config_service.py:189` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/services/config_service.py#L189)
- Function: `ConfigService.get_category`

Meaning:
- (fill in)

Causes:
- (fill in)

Next steps:
- (fill in)

## LOG-A0CF99AB10

- Level: `warning`
- Message: `Failed to get project {...} from DB: {...}`
- Location: `app/services/project_service.py:192` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/services/project_service.py#L192)
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
- Location: `app/services/project_service.py:242` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/services/project_service.py#L242)
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
- Location: `app/services/project_service.py:324` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/services/project_service.py#L324)
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
- Location: `app/services/project_service.py:382` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/services/project_service.py#L382)
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
- Location: `app/services/project_service.py:436` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/services/project_service.py#L436)
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
- Location: `app/startup.py:37` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/startup.py#L37)
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
- Location: `app/startup.py:39` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/startup.py#L39)
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
- Location: `app/startup.py:44` — [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/startup.py#L44)
- Function: `lifespan`

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
├── .github/
│   └── workflows/
│       ├── docs-ci.yml
│       └── docs-deploy.yml
├── alembic/
│   ├── versions/
│   │   ├── 1b671ff38c8c_initial_schema.py
│   │   ├── add_app_settings.py
│   │   ├── add_eval_tables.py
│   │   ├── add_projects.py
│   │   ├── add_prompts_versioned.py
│   │   ├── setup_database.sql
│   │   └── update_parameter_extraction_prompt.py
│   ├── env.py
│   ├── README
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
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── session.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── project.py
│   │   ├── prompt.py
│   │   └── settings.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── analysis.py
│   │   ├── chat.py
│   │   └── files.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── ChatRequest.py
│   │   ├── ChatResponse.py
│   │   └── StreamRequest.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── cache.py
│   │   ├── config_service.py
│   │   ├── project_service.py
│   │   └── prompt_service.py
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_cache.py
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
│   │   ├── AI_PACK.md
│   │   ├── ARCHITECTURE.md
│   │   ├── CONFIG_REFERENCE.md
│   │   ├── ENTRYPOINT.md
│   │   ├── GLOSSARY.md
│   │   ├── index.md
│   │   ├── LOG_CATALOG.md
│   │   ├── MODULE_INDEX.md
│   │   ├── QUALITY_BAR.md
│   │   └── REPO_TREE.md
│   ├── reference/
│   │   └── index.md
│   ├── db-config-migration-plan.md
│   ├── db-config-migration-todo.md
│   ├── index.md
│   ├── memory.md
│   ├── README.md
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
├── .gitignore
├── alembic.ini
├── CLAUDE.md
├── context_rules.csv
├── docker-compose.yml
├── Dockerfile
├── meta_postgres_sql.txt
├── mkdocs.yml
├── pyproject.toml
├── README.md
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
