# Architecture Overview

This document describes the system architecture of agent-loggy, an automated log analysis platform for banking and financial applications.

## System Design

```
                                    +------------------+
                                    |   Frontend       |
                                    |   (React UI)     |
                                    +--------+---------+
                                             |
                                             | HTTP/SSE
                                             v
+-----------------------------------------------------------------------------------+
|                              FastAPI Application                                   |
|                                                                                   |
|  +-------------+     +----------------+     +------------------+                  |
|  | /api/chat   |     | /stream-analysis|    | /download        |                  |
|  | (POST/GET)  |     | (POST)         |     | (GET)            |                  |
|  +------+------+     +-------+--------+     +--------+---------+                  |
|         |                    |                       |                            |
|         +--------------------+-----------------------+                            |
|                              |                                                    |
|                              v                                                    |
|                    +------------------+                                           |
|                    |   Orchestrator   |  <-- Main Pipeline Controller             |
|                    +--------+---------+                                           |
|                             |                                                     |
|         +-------------------+-------------------+                                 |
|         |                   |                   |                                 |
|         v                   v                   v                                 |
|  +-------------+    +-------------+    +------------------+                       |
|  | Parameters  |    | File/Loki   |    | Analyze/Verify   |                       |
|  | Agent       |    | Search      |    | Agents           |                       |
|  +------+------+    +------+------+    +--------+---------+                       |
|         |                  |                    |                                 |
|         v                  v                    v                                 |
|  +-------------+    +-------------+    +------------------+                       |
|  | Ollama LLM  |    | Log Files / |    | Report Generator |                       |
|  |             |    | Loki API    |    |                  |                       |
|  +-------------+    +-------------+    +------------------+                       |
|                                                                                   |
+-----------------------------------------------------------------------------------+
                              |
                              v
                    +------------------+
                    |   PostgreSQL     |
                    |   (Persistence)  |
                    +------------------+
```

## Core Components

### 1. FastAPI Application (`app/main.py`)

The entry point that:
- Initializes the FastAPI app with lifespan management
- Configures CORS middleware for frontend communication
- Registers all API routers (chat, analysis, files, cache admin)

### 2. Orchestrator (`app/orchestrator.py`)

The central pipeline controller that coordinates the entire analysis workflow. It implements a 7-step streaming pipeline:

| Step | Name | Description |
|------|------|-------------|
| 1 | Parameter Extraction | Uses LLM to extract time_frame, domain, query_keys from natural language |
| 2 | Planning | Produces execution plan and may ask clarifying questions |
| 3 | Log Search | Searches logs via local files (MMBL/UCB) or Loki API (NCC/ABBL) |
| 4 | Trace ID Collection | Extracts unique trace IDs from matching log entries |
| 5 | Log Compilation | Gathers all log entries for each trace ID |
| 6 | Analysis | Generates comprehensive analysis files using LLM |
| 7 | Verification | Validates findings and generates relevance scores |

### 3. Agents (`app/agents/`)

LLM-powered agents that follow a consistent pattern:

```python
from app.services.llm_providers.base import LLMProvider

class Agent:
    def __init__(self, client: LLMProvider, model: str):
        self.client = client  # LLM provider (Ollama, OpenRouter, etc.)
        self.model = model    # Model name (e.g., "llama3")

    def run(self, input: str) -> dict:
        # Uses system prompt + user input
        # Returns structured data
```

| Agent | File | Purpose |
|-------|------|---------|
| ParametersAgent | `parameter_agent.py` | Extracts structured parameters from user queries |
| PlanningAgent | `planning_agent.py` | Produces execution plan and clarifying questions |
| FileSearcher | `file_searcher.py` | Finds relevant log files for file-based projects |
| AnalyzeAgent | `analyze_agent.py` | Generates analysis reports from log data |
| RelevanceAnalyzerAgent | `verify_agent.py` | Scores relevance and validates findings |

### 4. Services (`app/services/`)

Business logic layer providing:

| Service | Purpose |
|---------|---------|
| `PromptService` | Manages versioned prompts with database persistence |
| `ConfigService` | Handles application configuration with caching |
| `ProjectService` | Determines project type (file-based vs Loki-based) |
| `CacheManager` | TTL-based in-memory caching infrastructure |
| `LLMCacheGateway` | L1/L2 LLM response caching with stampede protection |
| `LLMProviders` | Provider abstraction for Ollama and OpenRouter |
| `LokiRedisCache` | Loki query result caching with optional Redis |

### 5. Tools (`app/tools/`)

Utility components for log processing:

**Local file tools:**
- `LogSearcher` - Pattern matching in local log files
- `FullLogFinder` - Retrieves complete logs for trace IDs
- `TraceIdExtractor` - Extracts trace IDs from log entries

**Loki integration (`app/tools/loki/`):**
- `loki_query_builder.py` - Builds and executes Loki queries
- `loki_trace_id_extractor.py` - Extracts trace IDs from Loki results
- `loki_log_analyser.py` - Analyzes downloaded Loki logs

## LLM Caching Architecture

The system implements a dual-layer caching system for LLM responses:

```
┌─────────────────────────────────────────────────────────────────┐
│                        LLMCacheGateway                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────┐    ┌───────────────┐    ┌────────────────┐  │
│  │  L1 Cache     │    │  L2 Cache     │    │  SingleFlight  │  │
│  │ (LRU+TTL)     │◄──►│  (Redis)      │◄──►│  (Stampede)    │  │
│  │ In-Memory     │    │  Optional     │    │  Protection    │  │
│  └───────────────┘    └───────────────┘    └────────────────┘  │
├─────────────────────────────────────────────────────────────────┤
│  Used by: ParametersAgent, PlanningAgent, AnalyzeAgent, etc.   │
└─────────────────────────────────────────────────────────────────┘
```

**Cache Types and TTLs:**
| Cache Type | Default TTL | Agent |
|------------|-------------|-------|
| `parameter_extraction` | 2 hours | ParametersAgent |
| `planning` | 10 minutes | PlanningAgent |
| `trace_analysis` | 4 hours | AnalyzeAgent |
| `relevance_analysis` | 4 hours | RelevanceAnalyzerAgent |

**Admin Endpoints (`/cache/*`):**
- `GET /cache/ping` - Check L1/L2 connectivity
- `GET /cache/stats` - Cache statistics
- `POST /cache/delete` - Delete cache key
- `POST /cache/clear-l1` - Clear L1 cache

## Loki Query Caching

The system also caches Loki query results to reduce load on the Loki backend:

```
┌─────────────────────────────────────────────────────────────────┐
│                      LokiRedisCache                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌───────────────┐         ┌───────────────┐                    │
│  │  In-Memory    │         │  Redis        │                    │
│  │  Cache        │◄───────►│  (Optional)   │                    │
│  │  (Primary)    │         │  Persistence  │                    │
│  └───────────────┘         └───────────────┘                    │
├─────────────────────────────────────────────────────────────────┤
│  TTL Settings:                                                   │
│  - General queries: 4 hours (LOKI_CACHE_TTL_SECONDS)            │
│  - Trace queries: 6 hours (LOKI_CACHE_TRACE_TTL_SECONDS)        │
└─────────────────────────────────────────────────────────────────┘
```

## LLM Provider Abstraction

The system supports multiple LLM providers through a common interface:

```
┌────────────────────────────────────────────────────┐
│                    LLMProvider                      │
│                   (Base Class)                      │
├────────────────────────────────────────────────────┤
│  + chat(messages, model, **opts) -> response       │
│  + embed(text, model) -> vector                    │
└────────────────────────────────────────────────────┘
           ▲                          ▲
           │                          │
┌──────────────────────┐   ┌──────────────────────┐
│   OllamaProvider     │   │  OpenRouterProvider  │
│   (Default)          │   │  (Alternative)       │
└──────────────────────┘   └──────────────────────┘
```

**Configuration:**
- `LLM_PROVIDER=ollama` - Use local Ollama (default)
- `LLM_PROVIDER=openrouter` - Use OpenRouter API

## Project-Based Routing

The system handles two project types differently:

### File-Based Projects (MMBL, UCB)
- Logs stored as local files
- Direct file system access
- Pattern: `FileSearcher` -> `LogSearcher` -> `FullLogFinder`

### Loki-Based Projects (NCC, ABBL)
- Logs stored in Grafana Loki
- HTTP API queries
- Pattern: `download_logs()` -> `extract_trace_ids()` -> `gather_logs_for_trace_ids()`

```python
# Routing logic in orchestrator
if is_file_based(project):    # MMBL, UCB
    # Use local file search
elif is_loki_based(project):  # NCC, ABBL
    # Use Loki API
```

## Streaming Architecture

The API uses Server-Sent Events (SSE) for real-time progress updates:

```
Client                          Server
  |                               |
  |  POST /api/chat               |
  |  {prompt, project, env}       |
  |------------------------------>|
  |                               |
  |  {streamUrl: "/api/chat/..."}|
  |<------------------------------|
  |                               |
  |  GET /api/chat/stream/{id}    |
  |------------------------------>|
  |                               |
  |  event: Extracted Parameters  |
  |  data: {...}                  |
  |<------------------------------|
  |                               |
  |  event: Found trace id(s)     |
  |  data: {...}                  |
  |<------------------------------|
  |                               |
  |  event: done                  |
  |  data: {...}                  |
  |<------------------------------|
```

### SSE Event Types

| Event | Payload | Description |
|-------|---------|-------------|
| `Extracted Parameters` | `{parameters: {...}}` | LLM extracted search parameters |
| `Planned Steps` | `{plan: {...}}` | Execution plan for the pipeline |
| `Need Clarification` | `{questions: [...], plan: {...}}` | Missing required inputs; client should ask user and re-run |
| `Found relevant files` | `{total_files: N}` | File search results (file-based) |
| `Downloaded logs in file` | `{}` | Loki download complete |
| `Found trace id(s)` | `{count: N}` | Trace IDs extracted |
| `Compiled Request Traces` | `{traces_compiled: N}` | Logs gathered per trace |
| `Compiled Summary` | `{created_files: [...]}` | Analysis reports generated |
| `Verification Results` | `{...}` | Final verification summary |
| `done` | `{status: "complete\|needs_input\|error"}` | Pipeline complete (or stopped early) |
| `error` | `{error: "..."}` | Error occurred |

## Database Layer

### SQLAlchemy Models (`app/models/`)

```
prompts_versioned          app_settings              projects
+------------------+       +------------------+       +------------------+
| id (PK)          |       | id (PK)          |       | id (PK)          |
| prompt_name      |       | category         |       | project_code     |
| version          |       | setting_key      |       | project_name     |
| prompt_content   |       | setting_value    |       | log_source_type  |
| variables (JSON) |       | value_type       |       | is_active        |
| agent_name       |       | is_active        |       +------------------+
| is_active        |       +------------------+              |
+------------------+                                         |
        |                                              +-----+-----+
        v                                              |           |
prompt_history                                   project_settings  environments
+------------------+                             +-------------+   +-------------+
| id (PK)          |                             | project_id  |   | project_id  |
| prompt_id (FK)   |                             | setting_key |   | env_code    |
| action           |                             | value       |   | namespace   |
| old_content      |                             +-------------+   +-------------+
| new_content      |
+------------------+
```

### Feature Flags

Database-backed features can be toggled:

```bash
USE_DB_PROMPTS=true    # Use prompts from database
USE_DB_SETTINGS=true   # Use settings from database
USE_DB_PROJECTS=true   # Use project config from database
```

When disabled, the system falls back to hardcoded defaults.

## Configuration

Environment variables (`.env`):

**Core Settings:**
| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `DATABASE_SCHEMA` | Yes | Schema name (default: `agent_loggy`) |
| `OLLAMA_HOST` | Yes | Ollama server URL |
| `MODEL` | Yes | LLM model name (e.g., `llama3`) |
| `ANALYSIS_DIR` | Yes | Output directory for reports |

**LLM Provider Settings:**
| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `ollama` | Provider: `ollama` or `openrouter` |
| `OPENROUTER_API_KEY` | - | API key for OpenRouter |
| `OPENROUTER_MODEL` | - | Model override for OpenRouter |

**LLM Caching Settings:**
| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_CACHE_ENABLED` | `false` | Enable LLM response caching |
| `LLM_CACHE_NAMESPACE` | `default` | Cache namespace |
| `LLM_CACHE_L1_MAX_ENTRIES` | `10000` | Max L1 cache entries |
| `LLM_CACHE_L1_TTL_SECONDS` | `60` | L1 cache TTL |
| `LLM_CACHE_L2_ENABLED` | `false` | Enable Redis L2 cache |
| `LLM_CACHE_REDIS_URL` | - | Redis connection URL |
| `LLM_GATEWAY_VERSION` | `v1` | Bump to invalidate cache |
| `PROMPT_VERSION` | `v1` | Bump to invalidate prompt cache |

**Loki Cache Settings:**
| Variable | Default | Description |
|----------|---------|-------------|
| `LOKI_CACHE_ENABLED` | `true` | Enable Loki query caching |
| `LOKI_CACHE_REDIS_ENABLED` | `false` | Enable Redis persistence |
| `LOKI_CACHE_TTL_SECONDS` | `14400` | General query TTL (4 hours) |
| `LOKI_CACHE_TRACE_TTL_SECONDS` | `21600` | Trace query TTL (6 hours) |

**Feature Flags:**
| Variable | Default | Description |
|----------|---------|-------------|
| `USE_DB_PROMPTS` | `false` | Use prompts from database |
| `USE_DB_SETTINGS` | `false` | Use settings from database |
| `USE_DB_PROJECTS` | `false` | Use project config from database |

**Runtime Settings:**
| Variable | Default | Description |
|----------|---------|-------------|
| `DEV_MODE` | `false` | Enable hot reload (single worker) |
| `WORKERS` | `(2*CPU)+1` | Number of uvicorn workers |

## Output Directories

| Directory | Purpose |
|-----------|---------|
| `app/comprehensive_analysis/` | Generated analysis reports |
| `app/verification_reports/` | Verification output files |
| `app/loki_logs/` | Downloaded Loki log files (temporary) |
| `app/trace_logs/` | Local trace log files |

## Error Handling

Errors are streamed as SSE events:

```json
{
  "event": "error",
  "data": {"error": "Error message"}
}
```

Pipeline errors are logged and the stream is terminated gracefully.

## Security Considerations

- **Input Validation**: All API inputs validated via Pydantic schemas
- **Path Traversal Prevention**: File download endpoint sanitizes filenames
- **SQL Injection Prevention**: SQLAlchemy ORM with parameterized queries
- **CORS Configuration**: Configurable origins (currently `*` for development)
