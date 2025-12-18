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
2. **File/Log Search** - Either local file search (MMBL/UCB projects) or Loki query (NCC/ABBL projects)
3. **Trace ID Collection** - Extracts unique trace IDs from matching log entries
4. **Log Compilation** - Gathers all log entries per trace ID
5. **Analysis** - `AnalyzeAgent` generates comprehensive analysis files
6. **Verification** - `RelevanceAnalyzerAgent` validates findings and generates reports

### Project-Based Branching
The orchestrator handles two project types differently:
- **MMBL/UCB**: Local file-based log search via `FileSearcher` and `LogSearcher`
- **NCC/ABBL**: Loki-based log querying via `loki_query_builder` and `loki_trace_id_extractor`

### Agent Pattern
All agents in `app/agents/` follow a similar pattern:
- Constructor takes `Client` (Ollama) and `model` name
- Use system prompts to guide LLM behavior
- Return structured data (typically dicts)

### Streaming Architecture
The API uses SSE (Server-Sent Events) for real-time progress updates:
- `POST /api/chat` creates a session and returns a stream URL
- `GET /api/chat/stream/{session_id}` streams orchestrator events
- Events: `Extracted Parameters`, `Found relevant files`, `Found trace id(s)`, `Compiled Request Traces`, `Compiled Summary`, `Verification Results`, `done`

### Key Components
| Component | Location | Purpose |
|-----------|----------|---------|
| Orchestrator | `app/orchestrator.py` | Main analysis pipeline |
| ParametersAgent | `app/agents/parameter_agent.py` | NLP parameter extraction |
| AnalyzeAgent | `app/agents/analyze_agent.py` | Log analysis and report generation |
| RelevanceAnalyzerAgent | `app/agents/verify_agent.py` | Verification and relevance scoring |
| Loki tools | `app/tools/loki/` | Loki log backend integration |

## Configuration

Environment variables (via `.env` file, validated by `app/config.py`):
- `DATABASE_URL` - PostgreSQL connection string
- `DATABASE_SCHEMA` - Database schema name
- `OLLAMA_HOST` - Ollama server URL (e.g., `http://localhost:11434`)
- `MODEL` - LLM model name (e.g., `llama3`)
- `ANALYSIS_DIR` - Output directory for analysis files

## Output Directories
- `app/comprehensive_analysis/` - Generated analysis reports
- `app/verification_reports/` - Verification output files
- `app/loki_logs/` - Downloaded Loki log files (temporary)

## Current Status

Per `docs/specs.md`, the project is in active development with these priorities:
- Tests are minimal (see `app/tests/`)
- Session management is currently in-memory (migration to DB planned)
- Persistence layer is partial (basic Alembic setup exists)
