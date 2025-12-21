# Repository Guidelines

## Project Structure & Module Organization
- API entrypoint `app/main.py`; pipeline + SSE in `app/orchestrator.py`.
- Agents in `app/agents/`; log tools in `app/tools/`; outputs in `app/comprehensive_analysis/`, `app/verification_reports/`, `app/loki_logs/` (gitignored).
- Schemas/config/migrations: `app/schemas/`, `app/config.py`, `alembic/`; tests in `app/tests/`; docs in `docs/` (specs, memory, session, enhancement plans).

## Build, Test, and Development Commands
- Install: `pip install -r requirements.txt`.
- Run API: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` (requires reachable `OLLAMA_HOST`).
- Docker: `docker compose up --build` for API + Postgres.
- Migrations: `alembic revision --autogenerate -m "short-desc"` then `alembic upgrade head`.
- Tests: `pytest app/tests` or `pytest app/tests/test_trace_id_extractor.py -v`.

## Architecture & Roadmap
- Orchestrator: params → file/Loki search → trace IDs → compilation → analysis → verification → SSE events; keep names/order stable.
- Near-term (specs): drop hardcoded params, add conversation/session/trace-context models + migrations, persist sessions (replace in-memory dict).
- Memory/session: follow three-tier memory plan; move sessions to DB + Redis with expiry/cleanup.
- RAG/config: dynamic configs, hybrid BM25+vector + rerankers, context-preserving chunking.

## Coding Style & Naming Conventions
- Python 3.11, PEP8, 4-space indents; use type hints and `Path`/`Dict`.
- `snake_case` for modules/functions/vars, `PascalCase` for classes, `test_*` files for pytest.
- Use `logging.getLogger(__name__)`; keep SSE payloads JSON-serializable and event names unchanged. Pull config from `app.config.settings`/.env, not literals.

## Testing Guidelines
- Add pytest near code; cover edge cases with deterministic fixtures (no live network).
- For DB changes, ship the migration plus a smoke test after `alembic upgrade head`.
- When touching streaming/memory/sessions, test SSE ordering and session persistence; keep artifacts in gitignored dirs.

## Commit & Pull Request Guidelines
- Commits: concise, imperative, <72 chars.
- PRs: describe behavior changes, affected endpoints/agents, and tests run; link issues and call out new env vars or migrations.
- Include screenshots/log snippets only when they clarify UX/SSE behavior or retrieval output.

## Security & Configuration Tips
- Do not commit `.env` or generated logs/reports (`app/loki_logs/`, `app/comprehensive_analysis/`, `trace_logs/`); rotate creds when sharing.
- Verify `OLLAMA_HOST` and DB connectivity before starting the API.
- Keep docker-compose overrides/local mounts free of production data; scrub logs before sharing.

## Architecture at a Glance
- Orchestrator flow: parameter extraction -> log/file search (local for MMBL/UCB, Loki for NCC/ABBL) -> trace ID collection -> full log compilation -> analysis -> relevance verification -> streamed SSE updates.
- Frontend expects SSE events per step; maintain event ordering and payload serializability when extending the pipeline.
