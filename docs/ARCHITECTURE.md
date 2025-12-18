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
- Registers all API routers (chat, analysis, files)

### 2. Orchestrator (`app/orchestrator.py`)

The central pipeline controller that coordinates the entire analysis workflow. It implements a 6-step streaming pipeline:

| Step | Name | Description |
|------|------|-------------|
| 1 | Parameter Extraction | Uses LLM to extract time_frame, domain, query_keys from natural language |
| 2 | Log Search | Searches logs via local files (MMBL/UCB) or Loki API (NCC/ABBL) |
| 3 | Trace ID Collection | Extracts unique trace IDs from matching log entries |
| 4 | Log Compilation | Gathers all log entries for each trace ID |
| 5 | Analysis | Generates comprehensive analysis files using LLM |
| 6 | Verification | Validates findings and generates relevance scores |

### 3. Agents (`app/agents/`)

LLM-powered agents that follow a consistent pattern:

```python
class Agent:
    def __init__(self, client: Client, model: str):
        self.client = client  # Ollama client
        self.model = model    # Model name (e.g., "llama3")

    def run(self, input: str) -> dict:
        # Uses system prompt + user input
        # Returns structured data
```

| Agent | File | Purpose |
|-------|------|---------|
| ParametersAgent | `parameter_agent.py` | Extracts structured parameters from user queries |
| PlanningAgent | `planning_agent.py` | Produces a step-by-step plan and any blocking questions |
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
| `Planned Steps` | `{"plan": {...}}` | Execution plan for the pipeline and any blocking questions |
| `Need Clarification` | `{"questions": [...], "plan": {...}}` | Missing required inputs; client should ask user and re-run |
| `Found relevant files` | `{total_files: N}` | File search results (file-based) |
| `Downloaded logs in file` | `{}` | Loki download complete |
| `Found trace id(s)` | `{count: N}` | Trace IDs extracted |
| `Compiled Request Traces` | `{traces_compiled: N}` | Logs gathered per trace |
| `Compiled Summary` | `{created_files: [...]}` | Analysis reports generated |
| `Verification Results` | `{...}` | Final verification summary |
| `done` | `{"status": "complete|needs_input|error"}` | Pipeline complete (or stopped early awaiting user input) |
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

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `DATABASE_SCHEMA` | Yes | Schema name (default: `agent_loggy`) |
| `OLLAMA_HOST` | Yes | Ollama server URL |
| `MODEL` | Yes | LLM model name (e.g., `llama3`) |
| `ANALYSIS_DIR` | No | Output directory for reports |

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
