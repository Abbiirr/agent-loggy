# Codebase + Plans Discussion (2025-12-12)

## Scope
- Reviewed code paths: `app/main.py`, `app/orchestrator.py`, `app/agents/parameter_agent.py`, `app/tools/*`, `app/tests/test_trace_id_extractor.py`.
- Reviewed docs: `docs/project_enhancement_plans.md`, `docs/specs.md`, `docs/memory.md`, `docs/session.md`; `docs/plans` is currently empty.
- Goal: align code reality with the published roadmaps before multi-agent review.

## What works / positives
- End-to-end pipeline exists: parameter extraction -> file/Loki search -> trace compilation -> analysis -> verification with SSE streaming (coarse but functional).
- Agents and tools are modular (ParameterAgent, FileSearcher, AnalyzeAgent, VerifyAgent) with at least one test around trace id extraction.
- Pydantic settings scaffold (`app/config.py`) gives us a starting point for environment-driven configuration.

## Critical gaps (my take)
- Config drift: `ParameterAgent` hardcodes `OLLAMA_HOST` and allow/exclude lists; orchestrator uses `log_base_dir="data"` and `NEGATE_RULES_PATH` without env/config; `main.py` still relies on in-memory sessions and initializes the Ollama client without considering DB/Redis lifecycle.
- Streaming/session fragility: SSE emits only coarse step events, includes odd characters in log strings (e.g., `STEPA` artifacts), and does not follow the `step`/`warning`/`error`/`done` schema in specs. Sessions live in an in-memory dict with no expiry or recovery, and conversation/trace context is not persisted.
- Persistence + models missing: Spec-defined models (conversations, messages, sessions, trace_context, analysis_results) and repositories are absent; Alembic lacks revisions for them.
- Reliability + safety: No request limits, log size caps, or cleanup for `app/loki_logs` / `app/comprehensive_analysis`; negate rules CSV is read without validation. Error handling is ad-hoc logging without error code mapping.
- Config/doc sync: `docs/plans` is empty and the RAG roadmap in `project_enhancement_plans.md` (chunking, hybrid search, feature flags, reranking) is not reflected in code, so expectations need re-scoping.
- Testing + observability: Only `test_trace_id_extractor` exists; no coverage for orchestrator streaming, parameter agent normalization, or file/Loki search utilities. Logging is unstructured; metrics/health checks are minimal beyond Ollama ping.

## Opinion on project_enhancement_plans.md
- Dynamic config + versioned prompts: Agree, but start with the DB schema and Dynaconf/Redis cache; build model/prompt tables with label-based versioning before layering feature flags.
- Chunking/hybrid/rerank stack: Valuable later; for logs start with late chunking and a small BM25/pgvector hybrid, then add contextual chunking only for high-value references to control cost. Keep reranker optional behind a flag/killswitch.
- Feature management/testing: Flagsmith/promptfoo/RAGAS make sense after persistence lands; otherwise rollout and measurement are premature. Bake in a master kill switch and percent rollout fields in config tables to align with the doc.

## Recommended near-term plan (ordered)
1) Clean up orchestrator/main for correctness: remove weird characters and hardcoded stubs, parameterize paths via `settings`, guard file access, and normalize SSE event schema (`step`/`warning`/`error`/`done`) without breaking existing event titles the UI consumes.
2) Implement core models + migrations (conversations, messages, sessions, trace_context, analysis_results) and replace `active_sessions` with DB-backed sessions plus optional Redis cache; add minimal repositories/services.
3) Tighten configuration: enforce required env defaults in `app/config.py`, stop hardcoding `OLLAMA_HOST` in `ParameterAgent`, and move allow/exclude lists or negate rules into config or DB-managed tables with validation.
4) Add resilience: size limits, retention/cleanup for generated logs/reports, structured logging with trace/session ids, and error code mapping from specs.
5) Expand tests: unit tests for ParameterAgent normalization/fallbacks, orchestrator SSE ordering, and file/Loki search utilities; add fixture data for deterministic runs.
6) Only then pilot RAG improvements: introduce dynamic config tables + cache, basic hybrid retrieval, and an optional reranker flag; keep chunking choices simple until telemetry exists.

## Open questions for the group
- Preferred DB/Redis deployment targets and migration cadence? (affects Dynaconf/cache invalidation design)
- Do we need backward compatibility with current SSE event names/payloads for the frontend?
- What log volume/size should we cap per request, and how long should generated artifacts in `app/loki_logs` be retained?
- Which provider targets (Ollama only vs OpenAI/Anthropic) should guide the first adapter abstraction?
