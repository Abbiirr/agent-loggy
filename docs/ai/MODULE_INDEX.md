<!-- Generated on commit: 11f3d69cd35f822f62ba5b27519f7bd154f5fb6f -->
<!-- DO NOT EDIT: Run `python scripts/build_agent_docs.py` -->

# Module index (generated)

Key files:
- `app/main.py`
- `app/orchestrator.py`
- `app/config.py`
- `app/startup.py`
- `app/routers/chat.py`

Modules:

| Module | Path | Summary | Source |
|---|---|---|---|
| `app` | `app/__init__.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/__init__.py) |
| `app.agents` | `app/agents/__init__.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/__init__.py) |
| `app.agents.analyze_agent` | `app/agents/analyze_agent.py` | agents/analyze_agent.py - Refactored version focusing on analysis generation | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/analyze_agent.py) |
| `app.agents.file_searcher` | `app/agents/file_searcher.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/file_searcher.py) |
| `app.agents.parameter_agent` | `app/agents/parameter_agent.py` | parameters_agent.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/parameter_agent.py) |
| `app.agents.planning_agent` | `app/agents/planning_agent.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/planning_agent.py) |
| `app.agents.report_writer` | `app/agents/report_writer.py` | agents/report_writer.py - Handles all report generation and file writing | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/report_writer.py) |
| `app.agents.verify_agent` | `app/agents/verify_agent.py` | agents/verify_agent.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/agents/verify_agent.py) |
| `app.config` | `app/config.py` | app/core/config.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/config.py) |
| `app.db` | `app/db/__init__.py` | app/db/__init__.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/db/__init__.py) |
| `app.db.base` | `app/db/base.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/db/base.py) |
| `app.db.session` | `app/db/session.py` | SQLAlchemy session factory with FastAPI dependency injection. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/db/session.py) |
| `app.dependencies` | `app/dependencies.py` | Shared dependencies for FastAPI routes. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/dependencies.py) |
| `app.evals` | `app/evals/__init__.py` | Prompt evaluation framework for continuous improvement. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/__init__.py) |
| `app.evals.cli` | `app/evals/cli.py` | CLI for running prompt evaluations. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/cli.py) |
| `app.evals.metrics` | `app/evals/metrics.py` | Metrics calculators for evaluating agent outputs against expected values. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/metrics.py) |
| `app.evals.models` | `app/evals/models.py` | SQLAlchemy models for prompt evaluation results. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/models.py) |
| `app.evals.runner` | `app/evals/runner.py` | Evaluation runner for testing prompts against golden datasets. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/runner.py) |
| `app.evals.storage` | `app/evals/storage.py` | Database storage layer for evaluation results. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/evals/storage.py) |
| `app.main` | `app/main.py` | main.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/main.py) |
| `app.models` | `app/models/__init__.py` | app/models/__init__.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/models/__init__.py) |
| `app.models.context_rule` | `app/models/context_rule.py` | SQLAlchemy models for RAG context rules. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/models/context_rule.py) |
| `app.models.project` | `app/models/project.py` | SQLAlchemy models for project configuration. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/models/project.py) |
| `app.models.prompt` | `app/models/prompt.py` | SQLAlchemy models for versioned prompts with history tracking. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/models/prompt.py) |
| `app.models.settings` | `app/models/settings.py` | SQLAlchemy models for application settings with history tracking. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/models/settings.py) |
| `app.orchestrator` | `app/orchestrator.py` | orchestrator.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/orchestrator.py) |
| `app.routers` | `app/routers/__init__.py` | API routers for agent-loggy. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/routers/__init__.py) |
| `app.routers.analysis` | `app/routers/analysis.py` | Analysis API routes for log analysis streaming. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/routers/analysis.py) |
| `app.routers.chat` | `app/routers/chat.py` | Chat API routes for the React ChatInterface. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/routers/chat.py) |
| `app.routers.files` | `app/routers/files.py` | File download API routes. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/routers/files.py) |
| `app.schemas` | `app/schemas/__init__.py` | schemas/__init__.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/schemas/__init__.py) |
| `app.schemas.ChatRequest` | `app/schemas/ChatRequest.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/schemas/ChatRequest.py) |
| `app.schemas.ChatResponse` | `app/schemas/ChatResponse.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/schemas/ChatResponse.py) |
| `app.schemas.StreamRequest` | `app/schemas/StreamRequest.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/schemas/StreamRequest.py) |
| `app.services` | `app/services/__init__.py` | app/services/__init__.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/__init__.py) |
| `app.services.cache` | `app/services/cache.py` | TTL-based caching infrastructure with thread-safe in-memory caching. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/cache.py) |
| `app.services.config_service` | `app/services/config_service.py` | Service layer for application configuration management with caching and fallback defaults. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/config_service.py) |
| `app.services.llm_cache` | `app/services/llm_cache.py` | LLM response caching service for reducing redundant Ollama API calls. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/llm_cache.py) |
| `app.services.project_service` | `app/services/project_service.py` | Service layer for project configuration management with caching and fallback defaults. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/project_service.py) |
| `app.services.prompt_service` | `app/services/prompt_service.py` | Service layer for versioned prompt management with caching and hot-reload support. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/services/prompt_service.py) |
| `app.startup` | `app/startup.py` | Application startup logic and health checks. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/startup.py) |
| `app.tests` | `app/tests/__init__.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tests/__init__.py) |
| `app.tests.test_cache` | `app/tests/test_cache.py` | Tests for the TTLCache and CacheManager classes. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tests/test_cache.py) |
| `app.tests.test_planning_agent` | `app/tests/test_planning_agent.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tests/test_planning_agent.py) |
| `app.tests.test_trace_id_extractor` | `app/tests/test_trace_id_extractor.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tests/test_trace_id_extractor.py) |
| `app.tools` | `app/tools/__init__.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/__init__.py) |
| `app.tools.full_log_finder` | `app/tools/full_log_finder.py` | tools/full_log_finder.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/full_log_finder.py) |
| `app.tools.log_searcher` | `app/tools/log_searcher.py` | tools/log_searcher.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/log_searcher.py) |
| `app.tools.loki` | `app/tools/loki/__init__.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/loki/__init__.py) |
| `app.tools.loki.loki_log_analyser` | `app/tools/loki/loki_log_analyser.py` | log_compiler.py: Library for compiling Loki and application logs into human-readable timeline reports. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/loki/loki_log_analyser.py) |
| `app.tools.loki.loki_log_report_generator` | `app/tools/loki/loki_log_report_generator.py` | log_compiler.py: Library for compiling Loki and application logs into human-readable comprehensive timeline reports. | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/loki/loki_log_report_generator.py) |
| `app.tools.loki.loki_query_builder` | `app/tools/loki/loki_query_builder.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/loki/loki_query_builder.py) |
| `app.tools.loki.loki_trace_id_extractor` | `app/tools/loki/loki_trace_id_extractor.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/loki/loki_trace_id_extractor.py) |
| `app.tools.trace_id_extractor` | `app/tools/trace_id_extractor.py` | tools/trace_id_extractor.py | [link](https://github.com/Abbiirr/agent-loggy/blob/11f3d69cd35f822f62ba5b27519f7bd154f5fb6f/app/tools/trace_id_extractor.py) |
