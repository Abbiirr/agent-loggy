# AI docs

These pages are designed so an AI agent can "research the codebase" without opening the source tree directly.

## Key Features

- **LLM Provider Abstraction** - Ollama + OpenRouter support
- **LLM Response Caching** - L1/L2 with stampede protection
- **Loki Query Caching** - Redis-backed cache
- **DB-backed Configuration** - Prompts, settings, projects

## Start here

- `docs/ai/ENTRYPOINT.md`
- `docs/ai/ARCHITECTURE.md`
- `docs/ai/MODULE_INDEX.md` (generated)

## Generated indexes

- `docs/ai/CONFIG_REFERENCE.md` (generated)
- `docs/ai/LOG_CATALOG.md` (generated)
- `docs/ai/REPO_TREE.md` (generated)

## Export

- `docs/ai/AI_PACK.md` (generated) — single-file bundle for retrieval and offline use.
