# Repository Guidelines

## Project Structure & Module Organization
- API entrypoint `app/main.py`; pipeline + SSE in `app/orchestrator.py`.
- Agents in `app/agents/`; log tools in `app/tools/`; outputs in `app/comprehensive_analysis/`, `app/verification_reports/`, `app/loki_logs/` (gitignored).
- Schemas/config/migrations: `app/schemas/`, `app/config.py`, `alembic/`; tests in `app/tests/`; docs in `docs/` (specs, memory, session, enhancement plans).

## Build, Test, and Development Commands
- Install: `uv sync`.
- Run API: `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` (requires reachable `OLLAMA_HOST` or `OPENROUTER_API_KEY`).
- Docker: `docker compose up --build` for API + Postgres.
- Migrations: `uv run alembic revision --autogenerate -m "short-desc"` then `uv run alembic upgrade head`.
- Tests: `uv run pytest app/tests` or `uv run pytest app/tests/test_trace_id_extractor.py -v`.
- Docs: `python scripts/build_agent_docs.py` to regenerate agent docs, `python scripts/check_docs_fresh.py` to verify.

## Architecture & Roadmap
- Orchestrator: params -> planning -> file/Loki search -> trace IDs -> compilation -> analysis -> verification -> SSE events; keep names/order stable.
- LLM providers: Ollama (default) or OpenRouter; configured via `LLM_PROVIDER` env var.
- Caching: L1 (in-memory LRU+TTL) and L2 (Redis) with stampede protection for LLM calls; Loki queries cached separately.
- Persistent conversations: Phase 1-6 complete (full implementation with SSE streaming); enable with `USE_PERSISTENT_CONVERSATIONS=true`.
- Near-term: context rules migration (phase 5), admin API endpoints.
- Knowledge base: pgvector-based semantic search for codebase docs; tables `kb_services`, `kb_elements`, `kb_ingestion_runs`.
- RAG/config: dynamic configs from DB, context-aware relevance scoring with ignore/important patterns.

## Coding Style & Naming Conventions
- Python 3.11, PEP8, 4-space indents; use type hints and `Path`/`Dict`.
- `snake_case` for modules/functions/vars, `PascalCase` for classes, `test_*` files for pytest.
- Use `logging.getLogger(__name__)`; keep SSE payloads JSON-serializable and event names unchanged. Pull config from `app.config.settings`/.env, not literals.

## Testing Guidelines
- **Test-first development**: Write tests before/alongside implementation for all phases.
- Add pytest in `app/tests/`; cover edge cases with deterministic fixtures (no live network).
- For DB changes, ship the migration plus tests verifying model behavior after `alembic upgrade head`.
- When touching streaming/memory/sessions, test SSE ordering and session persistence; keep artifacts in gitignored dirs.
- Run `uv run pytest app/tests/test_<feature>.py -v` to verify each phase before moving on.

## Commit & Pull Request Guidelines
- Commits: concise, imperative, <72 chars.
- PRs: describe behavior changes, affected endpoints/agents, and tests run; link issues and call out new env vars or migrations.
- Include screenshots/log snippets only when they clarify UX/SSE behavior or retrieval output.

## Security & Configuration Tips
- Do not commit `.env` or generated logs/reports (`app/loki_logs/`, `app/comprehensive_analysis/`, `trace_logs/`); rotate creds when sharing.
- Verify `OLLAMA_HOST` and DB connectivity before starting the API.
- Keep docker-compose overrides/local mounts free of production data; scrub logs before sharing.

## Architecture at a Glance
- Orchestrator flow: parameter extraction -> planning (with clarification) -> log/file search (local for MMBL/UCB, Loki for NCC/ABBL) -> trace ID collection -> full log compilation -> analysis -> relevance verification (with RAG context rules) -> streamed SSE updates.
- LLM Gateway: wraps providers with L1/L2 caching, stampede protection, and cache versioning; bump `LLM_GATEWAY_VERSION` or `PROMPT_VERSION` to invalidate.
- Frontend expects SSE events per step; maintain event ordering and payload serializability when extending the pipeline.
- Key SSE events: `Extracted Parameters`, `Planned Steps`, `Need Clarification`, `Found relevant files`, `Found trace id(s)`, `Compiled Request Traces`, `Compiled Summary`, `Verification Results`, `done`.
