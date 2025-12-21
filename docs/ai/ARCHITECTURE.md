# Architecture

This is a compact, agent-oriented view of the system. For longer notes, see `docs/ARCHITECTURE.md`.

## High-level components

- **API layer**: FastAPI app in `app/main.py` and routers in `app/routers/`
- **Orchestration**: `app/orchestrator.py` coordinates the multi-step analysis pipeline
- **Agents**: `app/agents/` contains LLM-driven steps (parameter extraction, planning, analysis, verification)
- **Tools**: `app/tools/` provides log search/trace collection primitives (including Loki integration under `app/tools/loki/`)
- **LLM Gateway**: `app/services/llm_gateway/` provides L1/L2 caching with stampede protection
- **LLM Providers**: `app/services/llm_providers/` provides provider abstraction (Ollama, OpenRouter)
- **Persistence/config**: models under `app/models/`, settings in `app/config.py`, services under `app/services/`

## Pipeline sketch

The orchestrator performs a stepwise flow:

1. Extract parameters from user text (`ParametersAgent`)
2. Plan/gate the pipeline (`PlanningAgent` - may ask for clarification)
3. Search logs (file-based or Loki-based)
4. Extract trace IDs and compile per-trace logs
5. Generate analysis outputs (`AnalyzeAgent`)
6. Run verification and emit summary (`RelevanceAnalyzerAgent`)

## Caching layers

- **LLM Response Caching**: L1 (in-memory LRU+TTL) + L2 (Redis) via `LLMCacheGateway`
- **Loki Query Caching**: In-memory + optional Redis via `LokiRedisCache`

## Extension points

- Add new LLM providers under `app/services/llm_providers/` and register in factory
- Add new log backends under `app/tools/` and dispatch in `app/orchestrator.py`
- Add new agents under `app/agents/` and wire them into the orchestrator
- Add new API endpoints under `app/routers/`
