<!-- Generated on commit: 587e82e13aa226d1827d16cbcffa9e92a2ed75d2 -->
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
| `app` | `app/__init__.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/__init__.py) |
| `app.agents` | `app/agents/__init__.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/__init__.py) |
| `app.agents.analyze_agent` | `app/agents/analyze_agent.py` | agents/analyze_agent.py - Refactored version focusing on analysis generation | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/analyze_agent.py) |
| `app.agents.file_searcher` | `app/agents/file_searcher.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/file_searcher.py) |
| `app.agents.parameter_agent` | `app/agents/parameter_agent.py` | parameters_agent.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/parameter_agent.py) |
| `app.agents.planning_agent` | `app/agents/planning_agent.py` | Stubbed PlanningAgent: not used in current orchestration | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/planning_agent.py) |
| `app.agents.report_writer` | `app/agents/report_writer.py` | agents/report_writer.py - Handles all report generation and file writing | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/report_writer.py) |
| `app.agents.verify_agent` | `app/agents/verify_agent.py` | agents/verify_agent.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/agents/verify_agent.py) |
| `app.config` | `app/config.py` | app/core/config.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/config.py) |
| `app.db` | `app/db/__init__.py` | app/db/__init__.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/db/__init__.py) |
| `app.db.base` | `app/db/base.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/db/base.py) |
| `app.db.session` | `app/db/session.py` | SQLAlchemy session factory with FastAPI dependency injection. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/db/session.py) |
| `app.dependencies` | `app/dependencies.py` | Shared dependencies for FastAPI routes. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/dependencies.py) |
| `app.main` | `app/main.py` | main.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/main.py) |
| `app.models` | `app/models/__init__.py` | app/models/__init__.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/models/__init__.py) |
| `app.models.project` | `app/models/project.py` | SQLAlchemy models for project configuration. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/models/project.py) |
| `app.models.prompt` | `app/models/prompt.py` | SQLAlchemy models for versioned prompts with history tracking. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/models/prompt.py) |
| `app.models.settings` | `app/models/settings.py` | SQLAlchemy models for application settings with history tracking. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/models/settings.py) |
| `app.orchestrator` | `app/orchestrator.py` | orchestrator.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/orchestrator.py) |
| `app.routers` | `app/routers/__init__.py` | API routers for agent-loggy. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/routers/__init__.py) |
| `app.routers.analysis` | `app/routers/analysis.py` | Analysis API routes for log analysis streaming. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/routers/analysis.py) |
| `app.routers.chat` | `app/routers/chat.py` | Chat API routes for the React ChatInterface. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/routers/chat.py) |
| `app.routers.files` | `app/routers/files.py` | File download API routes. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/routers/files.py) |
| `app.schemas` | `app/schemas/__init__.py` | schemas/__init__.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/schemas/__init__.py) |
| `app.schemas.ChatRequest` | `app/schemas/ChatRequest.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/schemas/ChatRequest.py) |
| `app.schemas.ChatResponse` | `app/schemas/ChatResponse.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/schemas/ChatResponse.py) |
| `app.schemas.StreamRequest` | `app/schemas/StreamRequest.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/schemas/StreamRequest.py) |
| `app.services` | `app/services/__init__.py` | app/services/__init__.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/services/__init__.py) |
| `app.services.cache` | `app/services/cache.py` | TTL-based caching infrastructure with thread-safe in-memory caching. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/services/cache.py) |
| `app.services.config_service` | `app/services/config_service.py` | Service layer for application configuration management with caching and fallback defaults. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/services/config_service.py) |
| `app.services.project_service` | `app/services/project_service.py` | Service layer for project configuration management with caching and fallback defaults. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/services/project_service.py) |
| `app.services.prompt_service` | `app/services/prompt_service.py` | Service layer for versioned prompt management with caching and hot-reload support. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/services/prompt_service.py) |
| `app.startup` | `app/startup.py` | Application startup logic and health checks. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/startup.py) |
| `app.tests` | `app/tests/__init__.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tests/__init__.py) |
| `app.tests.test_cache` | `app/tests/test_cache.py` | Tests for the TTLCache and CacheManager classes. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tests/test_cache.py) |
| `app.tests.test_trace_id_extractor` | `app/tests/test_trace_id_extractor.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tests/test_trace_id_extractor.py) |
| `app.tools` | `app/tools/__init__.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tools/__init__.py) |
| `app.tools.full_log_finder` | `app/tools/full_log_finder.py` | tools/full_log_finder.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tools/full_log_finder.py) |
| `app.tools.log_searcher` | `app/tools/log_searcher.py` | tools/log_searcher.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tools/log_searcher.py) |
| `app.tools.loki` | `app/tools/loki/__init__.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tools/loki/__init__.py) |
| `app.tools.loki.loki_log_analyser` | `app/tools/loki/loki_log_analyser.py` | log_compiler.py: Library for compiling Loki and application logs into human-readable timeline reports. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tools/loki/loki_log_analyser.py) |
| `app.tools.loki.loki_log_report_generator` | `app/tools/loki/loki_log_report_generator.py` | log_compiler.py: Library for compiling Loki and application logs into human-readable comprehensive timeline reports. | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tools/loki/loki_log_report_generator.py) |
| `app.tools.loki.loki_query_builder` | `app/tools/loki/loki_query_builder.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tools/loki/loki_query_builder.py) |
| `app.tools.loki.loki_trace_id_extractor` | `app/tools/loki/loki_trace_id_extractor.py` |  | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tools/loki/loki_trace_id_extractor.py) |
| `app.tools.trace_id_extractor` | `app/tools/trace_id_extractor.py` | tools/trace_id_extractor.py | [link](https://github.com/Abbiirr/agent-loggy/blob/main/app/tools/trace_id_extractor.py) |
