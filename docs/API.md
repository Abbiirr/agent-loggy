# API Reference

This document describes the REST API endpoints provided by agent-loggy.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently no authentication is required. CORS is enabled for all origins in development.

---

## Chat API

### Create Chat Session

Creates a new analysis session and returns a streaming URL.

```
POST /api/chat
```

**Request Body:**

```json
{
  "prompt": "string",
  "project": "string",
  "env": "string",
  "domain": "string",
  "cache": {
    "enabled": true,
    "no_cache": false,
    "no_store": false,
    "ttl_seconds": null,
    "s_maxage_seconds": null,
    "namespace": null
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `prompt` | string | Yes | Natural language query describing the log analysis request |
| `project` | string | Yes | Project code: `MMBL`, `UCB`, `NCC`, or `ABBL` |
| `env` | string | Yes | Environment: `prod`, `staging`, etc. |
| `domain` | string | Yes | Domain context: `transactions`, `auth`, etc. |
| `cache` | object | No | Cache policy for this request (see Cache Policy below) |

**Cache Policy Object:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | true | Whether caching is enabled for this request |
| `no_cache` | bool | false | Skip reading from cache (force fresh computation) |
| `no_store` | bool | false | Don't store result in cache |
| `ttl_seconds` | int | null | Override L1 cache TTL |
| `s_maxage_seconds` | int | null | Override L2 (Redis) cache TTL |
| `namespace` | string | null | Cache namespace override |

**Response:**

```json
{
  "streamUrl": "/api/chat/stream/{session_id}"
}
```

**Example:**

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Show me failed NPSB transactions from yesterday",
    "project": "MMBL",
    "env": "prod",
    "domain": "transactions"
  }'
```

---

### Stream Analysis Results

Streams analysis progress and results via Server-Sent Events (SSE).

```
GET /api/chat/stream/{session_id}
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string | UUID returned from `POST /api/chat` |

**Response:**

SSE stream with the following event types:

| Event | Payload | Description |
|-------|---------|-------------|
| `Extracted Parameters` | `{"parameters": {...}}` | Extracted search parameters |
| `Planned Steps` | `{"plan": {...}}` | Execution plan for the pipeline |
| `Need Clarification` | `{"questions": [...], "plan": {...}}` | Missing inputs; client should ask user and re-run |
| `Found relevant files` | `{"total_files": N}` | Number of matching log files (file-based) |
| `Downloaded logs in file` | `{}` | Loki logs downloaded (Loki-based) |
| `Found trace id(s)` | `{"count": N}` | Number of trace IDs found |
| `Compiled Request Traces` | `{"traces_compiled": N}` | Traces compiled |
| `Compiled Summary` | `{"created_files": [...]}` | Analysis files created |
| `Verification Results` | `{...}` | Verification summary |
| `done` | `{"status": "complete\|needs_input\|error"}` | Analysis complete or stopped early |
| `error` | `{"error": "message"}` | Error occurred |

**Example:**

```bash
curl -N http://localhost:8000/api/chat/stream/550e8400-e29b-41d4-a716-446655440000
```

**SSE Response Example:**

```
event: Extracted Parameters
data: {"parameters": {"time_frame": "2024-01-15", "query_keys": ["NPSB", "failed"]}}

event: Found trace id(s)
data: {"count": 5}

event: Compiled Summary
data: {"created_files": ["analysis_001.txt", "analysis_002.txt"]}

event: done
data: {"status": "complete"}
```

---

## Analysis API

### Stream Analysis (Direct)

Alternative endpoint for direct analysis streaming without session management.

```
POST /stream-analysis
```

**Request Body:**

```json
{
  "text": "string",
  "project": "string",
  "env": "string",
  "domain": "string",
  "cache": {
    "enabled": true,
    "no_cache": false,
    "no_store": false,
    "ttl_seconds": null,
    "s_maxage_seconds": null,
    "namespace": null
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | string | Yes | Natural language query |
| `project` | string | Yes | Project code |
| `env` | string | Yes | Environment |
| `domain` | string | Yes | Domain context |
| `cache` | object | No | Cache policy (same as Chat API) |

**Response:**

SSE stream (same events as `/api/chat/stream/{session_id}`)

**Example:**

```bash
curl -X POST -N http://localhost:8000/stream-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Find timeout errors in bKash transactions",
    "project": "NCC",
    "env": "prod",
    "domain": "transactions"
  }'
```

---

## Files API

### Download Analysis File

Downloads a generated analysis or report file.

```
GET /download/?filename={filename}
```

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `filename` | string | Yes | Name of the file to download |

**Response:**

Binary file download with `application/octet-stream` content type.

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | Invalid filename (path traversal attempt) |
| 404 | File not found |

**Example:**

```bash
curl -O http://localhost:8000/download/?filename=banking_analysis_001.txt
```

---

## Health API

### Health Check

Lightweight health check endpoint that returns immediately without blocking operations.

```
GET /health
```

**Response:**

```json
{
  "status": "ok"
}
```

Use this endpoint for liveness probes and to verify the server is responsive during heavy processing.

---

## SSE Client Examples

### JavaScript (Browser)

```javascript
const startAnalysis = async (prompt, project, env, domain) => {
  // 1. Create session
  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, project, env, domain })
  });
  const { streamUrl } = await response.json();

  // 2. Connect to SSE stream
  const eventSource = new EventSource(streamUrl);

  eventSource.addEventListener('Extracted Parameters', (e) => {
    console.log('Parameters:', JSON.parse(e.data));
  });

  eventSource.addEventListener('Found trace id(s)', (e) => {
    console.log('Traces:', JSON.parse(e.data));
  });

  eventSource.addEventListener('Verification Results', (e) => {
    console.log('Results:', JSON.parse(e.data));
  });

  eventSource.addEventListener('done', () => {
    console.log('Analysis complete');
    eventSource.close();
  });

  eventSource.addEventListener('error', (e) => {
    console.error('Error:', e);
    eventSource.close();
  });
};
```

### Python

```python
import requests
import sseclient

# 1. Create session
response = requests.post('http://localhost:8000/api/chat', json={
    'prompt': 'Show failed transactions from yesterday',
    'project': 'MMBL',
    'env': 'prod',
    'domain': 'transactions'
})
stream_url = response.json()['streamUrl']

# 2. Connect to SSE stream
response = requests.get(
    f'http://localhost:8000{stream_url}',
    stream=True
)
client = sseclient.SSEClient(response)

for event in client.events():
    print(f'{event.event}: {event.data}')
    if event.event == 'done':
        break
```

---

## Error Handling

All endpoints return standard HTTP error codes:

| Status | Description |
|--------|-------------|
| 200 | Success |
| 400 | Bad request (invalid input) |
| 404 | Resource not found |
| 422 | Validation error |
| 500 | Internal server error |

**Error Response Format:**

```json
{
  "detail": "Error message describing the issue"
}
```

**SSE Error Event:**

```
event: error
data: {"error": "Error message"}
```

---

## Cache Admin API

Cache management endpoints for the LLM caching layer.

### Ping Cache

Check cache connectivity and health.

```
GET /cache/ping
```

**Response:**

```json
{
  "l1": {"ok": true},
  "l2": {"healthy": true, "latency_ms": 1.23}
}
```

If L2 (Redis) is not configured:
```json
{
  "l1": {"ok": true},
  "l2": null
}
```

---

### Get Cache Statistics

Returns comprehensive cache statistics.

```
GET /cache/stats
```

**Response:**

```json
{
  "enabled": true,
  "calls": 100,
  "hits_l1": 45,
  "hits_l2": 20,
  "misses": 30,
  "bypasses": 5,
  "l1": {
    "entries": 150,
    "max_entries": 10000,
    "evictions": 10
  },
  "l2": {
    "connected": true,
    "keys": 500
  }
}
```

---

### Delete Cache Key

Delete a cache key from both L1 and L2 caches.

```
POST /cache/delete
```

**Request Body:**

```json
{
  "key": "llm:trace_analysis:abc123..."
}
```

**Response:**

Returns the result of the delete operation from the gateway.

---

### Clear L1 Cache

Clear the entire in-memory L1 cache for this worker.

```
POST /cache/clear-l1
```

**Response:**

```json
{
  "ok": true
}
```

**Note:** This only clears L1 for the current worker. Other workers/pods are not affected.

---

## Rate Limiting

No rate limiting is currently implemented. Consider adding rate limiting for production deployments.

---

## OpenAPI Documentation

Interactive API documentation is available at:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`
