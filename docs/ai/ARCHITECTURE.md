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
