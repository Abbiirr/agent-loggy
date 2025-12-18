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
