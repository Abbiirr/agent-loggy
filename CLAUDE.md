# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

agent-loggy is a Python FastAPI backend for automated log analysis and verification, targeting banking/financial logs. It uses LLM agents (via Ollama) to extract parameters from user queries, search logs, identify trace IDs, and generate analysis reports.

## Commands

### Development
```bash
uv sync                                           # Install dependencies
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload  # Dev server (hot reload, single worker)
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4  # Production (multi-worker, concurrent)
```

**Concurrency Note:** The server uses `starlette.concurrency.run_in_threadpool` to offload blocking LLM/IO operations. Default is 4 workers for concurrent request handling. Set `DEV_MODE=true` for hot reload during development (single worker). Hot reload and workers are mutually exclusive.

### Testing
```bash
uv run pytest                                     # Run all tests
uv run pytest app/tests/test_trace_id_extractor.py  # Run specific test
```

### Database Migrations
```bash
uv run alembic revision --autogenerate -m "description"  # Generate migration
uv run alembic upgrade head                              # Apply migrations
```

**Full schema setup guide:** See `docs/schema-setup-guide.md` for step-by-step instructions on:
- Creating a new PostgreSQL schema
- Running all migrations
- Seeding initial data (prompts, settings, projects)
- Enabling feature flags

### Adding Dependencies
```bash
uv add <package>                          # Add a production dependency
uv add --dev <package>                    # Add a dev dependency
```

### Docker
```bash
docker compose up                         # Run with PostgreSQL
docker compose up --watch                 # Auto-rebuild on changes
```

## Architecture

### Core Flow (Orchestrator Pipeline)
The `app/orchestrator.py` `Orchestrator.analyze_stream()` method is the main pipeline:
1. **Parameter Extraction** - `ParametersAgent` extracts time_frame, domain, query_keys from natural language
2. **Planning** - `PlanningAgent` produces execution plan and may ask clarifying questions
3. **File/Log Search** - Either local file search (MMBL/UCB projects) or Loki query (NCC/ABBL projects)
4. **Trace ID Collection** - Extracts unique trace IDs from matching log entries
5. **Log Compilation** - Gathers all log entries per trace ID
6. **Analysis** - `AnalyzeAgent` generates comprehensive analysis files
7. **Verification** - `RelevanceAnalyzerAgent` validates findings and generates reports

### Project-Based Branching
The orchestrator handles two project types differently:
- **MMBL/UCB**: Local file-based log search via `FileSearcher` and `LogSearcher`
- **NCC/ABBL**: Loki-based log querying via `loki_query_builder` and `loki_trace_id_extractor`

### Agent Pattern
All agents in `app/agents/` follow a similar pattern:
- Constructor takes `LLMProvider` (Ollama, OpenRouter, etc.) and `model` name
- Use system prompts to guide LLM behavior
- Return structured data (typically dicts)

### Streaming Architecture
The API uses SSE (Server-Sent Events) for real-time progress updates:
- `POST /api/chat` creates a session and returns a stream URL
- `GET /api/chat/stream/{session_id}` streams orchestrator events
- Events: `Extracted Parameters`, `Planned Steps`, `Need Clarification`, `Found relevant files`, `Found trace id(s)`, `Compiled Request Traces`, `Compiled Summary`, `Verification Results`, `done`

### Key Components
| Component | Location | Purpose |
|-----------|----------|---------|
| Orchestrator | `app/orchestrator.py` | Main analysis pipeline |
| ParametersAgent | `app/agents/parameter_agent.py` | NLP parameter extraction |
| PlanningAgent | `app/agents/planning_agent.py` | Pipeline planning and clarification |
| AnalyzeAgent | `app/agents/analyze_agent.py` | Log analysis and report generation |
| RelevanceAnalyzerAgent | `app/agents/verify_agent.py` | Verification and relevance scoring |
| LLM Gateway | `app/services/llm_gateway/gateway.py` | L1/L2 caching with stampede protection |
| LLM Providers | `app/services/llm_providers/` | Provider abstraction (Ollama, OpenRouter) |
| Loki Redis Cache | `app/services/loki_redis_cache.py` | Loki query caching with Redis |
| Loki tools | `app/tools/loki/` | Loki log backend integration |
| Health Check | `GET /health` | Non-blocking liveness probe |

## Configuration

Environment variables (via `.env` file, validated by `app/config.py`):

### Core Settings
- `DATABASE_URL` - PostgreSQL connection string
- `DATABASE_SCHEMA` - Database schema name
- `ANALYSIS_DIR` - Output directory for analysis files

### LLM Provider Settings
- `LLM_PROVIDER` - Provider to use: `ollama` (default) or `openrouter`
- `OLLAMA_HOST` - Ollama server URL (e.g., `http://localhost:11434`)
- `MODEL` - LLM model name (e.g., `llama3`)
- `OPENROUTER_API_KEY` - API key for OpenRouter (required if using OpenRouter)
- `OPENROUTER_MODEL` - Model override for OpenRouter (optional)

### LLM Caching Settings
- `LLM_CACHE_ENABLED` - Enable LLM response caching (default: `false`)
- `LLM_CACHE_NAMESPACE` - Cache namespace (default: `default`)
- `LLM_CACHE_L1_MAX_ENTRIES` - Max L1 in-memory cache entries (default: `10000`)
- `LLM_CACHE_L1_TTL_SECONDS` - L1 cache TTL (default: `60`)
- `LLM_CACHE_L2_ENABLED` - Enable Redis L2 cache (default: `false`)
- `LLM_CACHE_REDIS_URL` - Redis connection URL for L2 cache
- `LLM_GATEWAY_VERSION` / `PROMPT_VERSION` - Bump to invalidate cache

### Loki Cache Settings
- `LOKI_CACHE_ENABLED` - Enable Loki query caching (default: `true`)
- `LOKI_CACHE_REDIS_ENABLED` - Enable Redis persistence for Loki cache
- `LOKI_CACHE_TTL_SECONDS` - General query TTL (default: `14400` / 4 hours)
- `LOKI_CACHE_TRACE_TTL_SECONDS` - Trace query TTL (default: `21600` / 6 hours)

### Feature Flags
- `USE_DB_PROMPTS` - Use prompts from database (default: `false`)
- `USE_DB_SETTINGS` - Use settings from database (default: `false`)
- `USE_DB_PROJECTS` - Use project config from database (default: `false`)

## Output Directories
- `app/comprehensive_analysis/` - Generated analysis reports
- `app/verification_reports/` - Verification output files
- `app/loki_logs/` - Downloaded Loki log files (temporary)

## Current Status

The project is in active development. Key implemented features:
- **LLM Provider Abstraction** - Supports Ollama and OpenRouter providers
- **LLM Caching** - L1 (in-memory LRU+TTL) and L2 (Redis) with stampede protection
- **Loki Caching** - Query result caching with optional Redis persistence
- **Database Configuration** - Prompts, settings, and projects can be DB-backed (phases 1-4 complete)
- **Planning Agent** - Pipeline planning with clarification questions

In progress:
- Session management is currently in-memory (migration to DB planned)
- Context rules migration (phase 5) pending
- Admin API endpoints (phase 6) pending
- Tests are expanding (see `app/tests/`)
