# Glossary

- **Trace ID**: Identifier used to correlate related log lines across services and files.
- **Loki**: Grafana Loki log backend; used here as an optional log source.
- **Orchestrator**: The pipeline coordinator that calls agents/tools and streams progress events.
- **Agent**: An LLM-powered component that produces structured output (parameters, plan, analysis, verification).
- **Generated docs**: Files under `docs/ai/` produced by `python scripts/build_agent_docs.py`.
- **AI pack**: Single-file export `docs/ai/AI_PACK.md` built by `python scripts/export_ai_pack.py`.
