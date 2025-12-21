# Log Analysis Chatbot / Trace Viewer Backend Specification (Living Document)

Version: 0.5.0
Last Updated: 2025-12-19
Status Legend: ✅ Done | 🟡 In Progress | 🔴 Not Started | ❗ Blocking | ⚠ Risky / Needs Decision

Purpose: Provide an authoritative snapshot of current state, target architecture, implementation roadmap, and verifiable acceptance criteria for the conversational log / trace analysis platform.

---
## 1. Project Snapshot (Current Reality)
| Area | Present in Repo | Notes |
|------|-----------------|-------|
| Orchestrator | ✅ (app/orchestrator.py) | Uses ProjectService for branching |
| Agents | ✅ (parameter, planning, analyze, verify, report) | With DB-backed prompts support |
| Streaming | ✅ (SSE via main/orchestrator flow) | Planning step, clarification support |
| Config | ✅ (app/config.py) | Pydantic Settings with validation |
| Persistence Layer | ✅ (app/db/, app/models/) | Prompts, Settings, Projects models |
| Alembic | ✅ (4 migrations) | Schema for prompts, settings, projects |
| Schemas (Pydantic) | ✅ (app/schemas/*.py) | Chat, Stream, CachePolicy schemas |
| Tests | ✅ (app/tests/) | Cache, gateway, planning, Loki, trace ID tests |
| Trace Reports | ✅ (app/comprehensive_analysis, verification_reports) | Generated artifacts |
| Loki Log Assets | ✅ (app/loki_logs/*.json) | With caching layer |
| Context Rules CSV | ✅ (app/app_settings) | Not yet migrated to DB |
| LLM Provider Abstraction | ✅ (app/services/llm_providers/) | Ollama + OpenRouter providers |
| LLM Caching | ✅ (app/services/llm_gateway/) | L1/L2 with stampede protection |
| Loki Caching | ✅ (app/services/loki_redis_cache.py) | With optional Redis persistence |
| Health Endpoint | ✅ (/health) | Non-blocking liveness probe |
| Concurrency | ✅ (app/main.py) | Auto-scaling workers, DEV_MODE support |
| UI-Specific State | 🔴 | No trace context or viewer state persistence |

Recent Progress:
- LLM provider abstraction (Ollama, OpenRouter) with factory pattern
- LLM response caching with L1 (in-memory) and L2 (Redis) layers, stampede protection
- Loki query caching with separate TTLs for general and trace queries
- Planning agent with clarification questions
- Database-backed prompts, settings, projects (phases 1-4 complete)
- Auto-scaling workers with DEV_MODE for development
- Health check endpoint for liveness probes

---
## 2. High-Level Goals
1. Replace single-shot analyzer with session + conversation + trace-aware conversational system.  
2. Persist conversations, messages, analysis results, and trace context for UI continuity.  
3. Provide quick tools (field extraction, masking) on selected trace.  
4. Abstract LLM providers (Ollama baseline, extensible to OpenAI / Anthropic).  
5. Deliver robust streaming protocol (fine-grained tokens + structured errors).  
6. Implement safe limits, metrics, and observability.

---
## 3. Status Matrix (Execution View)
| Component | Current | Target | Status | Blocked By | Risk |
|-----------|---------|--------|--------|-----------|------|
| Parameter Extraction | Agent-driven | Agent-driven parse | ✅ | - | - |
| DB-Backed Prompts | Implemented | DB versioning | ✅ | - | - |
| DB-Backed Settings | Implemented | DB config | ✅ | - | - |
| DB-Backed Projects | Implemented | DB project config | ✅ | - | - |
| LLM Provider Abstraction | Ollama + OpenRouter | Multiple providers | ✅ | - | - |
| LLM Response Caching | L1 + L2 | Caching layer | ✅ | - | - |
| Loki Query Caching | Redis-backed | Cache layer | ✅ | - | - |
| Planning Agent | Implemented | Pipeline planning | ✅ | - | - |
| Conversation Persistence | None | conversations + messages | 🔴 | Models | Medium |
| Sessions | In-memory | DB + optional Redis TTL | 🔴 | Models | Medium |
| Trace Context | Not stored | trace_context table + API | 🔴 | Models | Medium |
| Analysis Results | Files only | DB + hash dedupe | 🔴 | Models | Low |
| Streaming Protocol | step/plan/done | token/step/error/done | 🟡 | - | Low |
| Context Rules DB | CSV files | Database tables | 🔴 | Phase 5 | Low |
| Admin API | None | CRUD endpoints | 🔴 | Phase 6 | Low |
| Quick Tools | Absent | Endpoints (extract, mask) | 🔴 | Trace context | Low |
| Tests | Basic coverage | Full test suite | 🟡 | - | Medium |

---
## 3a. UI-Required Features
| Feature | Backend Need | Status | Notes |
|---------|--------------|--------|-------|
| Persist Active Trace | trace_context model + set API | 🔴 | P0 |
| Trace Summary | Summarization job/API | 🔴 | Auto-trigger on set |
| Quick Tools | Field extraction + masking endpoints | 🔴 | P1 |
| Conversation Titles | Title derivation from first message | 🔴 | P0 |
| Model Selector | Provider abstraction + selected_model field | 🔴 | P1 |
| Viewer State | viewer_state persistence (optional first pass) | 🔴 | Defer if scope tight |

---
## 4. Critical Path (Dependency-Ordered)
1. Remove orchestrator hardcoded params (unblocks correctness validation).  
2. Introduce models + migration (Conversation, Message, Session, TraceContext, AnalysisResult).  
3. Repository & SessionManager services.  
4. Conversation + message APIs (create, post, list).  
5. Trace context set & summary APIs.  
6. Streaming protocol upgrade (event schema + token streaming).  
7. Provider abstraction + selected_model persistence.  
8. Quick tools endpoints (extract-fields, mask-pii).  
9. ContextBuilder + sliding window + (optional) summarization.  
10. Metrics, structured logging, error codes, test coverage baseline.

---
## 5. Data Model (Proposed Detailed)
| Table | Fields (type) | Constraints / Indexes | Notes |
|-------|---------------|-----------------------|-------|
| conversations | id (UUID pk), title (text null), created_at (timestamptz), updated_at, active_trace_id (UUID null), selected_model (varchar 64 null), default_tab (varchar 32 null) | idx: (created_at DESC) | Title auto from first user message trimmed to 80 chars |
| messages | id (UUID pk), conversation_id (fk), role (varchar 16), content (text), token_count (int null), metadata (jsonb), created_at (timestamptz) | idx: (conversation_id, created_at) | role in (user, assistant, system) |
| sessions | id (UUID pk), conversation_id (fk), last_active_at, expires_at, state (jsonb) | idx: (expires_at) | Expired purged via job |
| trace_context | id (UUID pk), conversation_id (fk), trace_id (varchar 128), total_logs (int), parsed_fields (jsonb), summary (text), timeline (jsonb), created_at | unique (conversation_id, trace_id) | Only one active linked in conversations.active_trace_id |
| analysis_results | id (UUID pk), conversation_id (fk), trace_id (varchar 128 null), input_hash (char 64), parameters (jsonb), findings (jsonb), created_at | unique (input_hash) | Hash = sha256(sorted(parameters json)) |
| viewer_state (optional) | id (UUID pk), conversation_id (fk), is_open (bool), sidebar_visible (bool), current_log (varchar 256), created_at | unique (conversation_id) | P2 if needed |

Migration Naming: yyyyMMddHHMM_add_core_models.py

---
## 6. Service Interfaces (Contracts)
Pseudo-interface definitions (Pythonic):

SessionManager:
- create_session(conversation_id: UUID) -> Session
- get_session(session_id: UUID) -> Session | None
- touch(session_id: UUID) -> None (updates last_active_at)
- expire_stale(now: datetime) -> int (rows removed)

ConversationService:
- create_conversation(first_message: str, selected_model: str|None) -> Conversation
- add_message(conversation_id, role, content, metadata) -> Message
- list_messages(conversation_id, limit=50, before_id=None) -> List[Message]

TraceContextService:
- set_active(conversation_id, trace_id) -> TraceContext
- summarize(trace_id) -> str (stores + returns summary)
- get_active(conversation_id) -> TraceContext | None

ProviderAdapter (strategy):
- name() -> str
- generate(messages: List[dict], **opts) -> Iterable[str|TokenChunk]
- extract_parameters(text: str) -> dict

ContextBuilder:
- build(conversation_id, max_messages: int) -> List[Message]
- summarize(messages: List[Message]) -> str (optional Phase 3)

ErrorMapper:
- map(exc: Exception) -> (code: str, http: int, recoverable: bool)

---
## 7. Streaming Protocol (Target)
Transport: SSE (Phase 1+), optional WebSocket (Phase 4).  
Event Types & Payload Schema:
| Event | Payload Fields | Description |
|-------|----------------|-------------|
| token | token, idx | Incremental LLM token stream |
| step | title, detail | High-level pipeline progress |
| warning | code, message | Non-fatal issue |
| error | code, message, recoverable | Terminal for request |
| done | conversation_id, message_id, duration_ms | Completion marker |

JSON Example (SSE data field):
{ "event": "step", "title": "Parameter Extraction", "detail": {"keys": ["bkash"]} }

Resume Strategy (Phase 4): Client supplies last_message_id; server replays context + continues.

---
## 8. Error Codes
| Code | HTTP | Recoverable | Description |
|------|------|------------|-------------|
| PARAM_EXTRACTION_FAILED | 422 | yes | Could not derive parameters |
| TRACE_NOT_FOUND | 404 | no | Trace id missing / stale |
| DB_UNAVAILABLE | 503 | yes | Transient DB outage |
| LLM_TIMEOUT | 504 | yes | LLM exceeded timeout |
| INPUT_TOO_LARGE | 413 | no | Log / message exceeds size limit |
| UNSUPPORTED_MODEL | 400 | no | Model not registered |
| INTERNAL_ERROR | 500 | maybe | Catch-all fallback |

---
## 9. Metrics & Observability
| Metric | Type | Purpose |
|--------|------|---------|
| request_duration_ms | histogram | Latency SLA tracking |
| analysis_duration_ms | histogram | Log analysis performance |
| tokens_generated_total | counter | LLM usage tracking |
| active_sessions | gauge | Ops insight |
| errors_total{code} | counter | Error distribution |
| trace_summary_latency_ms | histogram | Summarization performance |

Structured Logging: JSON lines => fields: timestamp, level, trace_id (if any), conversation_id, event, message.

---
## 10. Provider Abstraction Strategy
Adapter Registry keyed by provider name via `LLM_PROVIDER` environment variable.
Selection Precedence: (LLM_PROVIDER setting) -> Ollama (default).
Factory pattern in `app/services/llm_providers/factory.py`.

Implemented Providers:
- OllamaProvider (✅ default) - Local Ollama server
- OpenRouterProvider (✅) - OpenRouter API with API key auth

Planned Adapters: OpenAIAdapter (🔴), AnthropicAdapter (🔴).

---
## 11. Trace Context Lifecycle
1. User sets a trace (set-trace endpoint).  
2. System checks for existing trace_context (conversation_id, trace_id).  
3. If absent: create row (parsed_fields = {}, summary = null, total_logs=0).  
4. Async summarization job populates summary + timeline; emits step/warning/done events.  
5. On new logs ingested or mismatch: invalidate (mark stale flag OR delete + recreate).  
6. Active trace id stored in conversations.active_trace_id.

Staleness Heuristic: If underlying log asset timestamp > trace_context.created_at => stale.

---
## 12. Security & Limits
| Concern | Control |
|---------|---------|
| Oversized Input | MAX_LOG_BYTES (env) + reject early |
| PII Exposure | mask-pii endpoint (regex rules) + optional hashing |
| Injection | Parameterized queries only (SQLAlchemy) |
| Resource Exhaustion | Session timeout + message count cap (MAX_CONTEXT_MESSAGES) |
| Secret Leakage | Centralized config; no hardcoded secrets |

---
## 13. Testing Roadmap
| Phase | Tests | Tools | Status |
|-------|-------|-------|--------|
| 1 | Unit: cache, LLM gateway, Loki cache | pytest + fixtures | ✅ |
| 1 | Unit: planning agent, trace ID extractor | pytest | ✅ |
| 2 | Integration: conversation CRUD, session expiry | ephemeral test DB | 🔴 |
| 3 | Streaming: SSE event ordering, error events | async test client | 🔴 |
| 4 | Provider fallback, trace context summarization | mock adapters | 🔴 |

Current test files:
- `test_cache.py` - TTLCache, CacheManager, @cached decorator
- `test_llm_gateway.py` - LLM cache gateway
- `test_loki_cache.py` - Loki Redis cache
- `test_planning_agent.py` - Planning agent
- `test_trace_id_extractor.py` - Trace ID extraction

CI Gate: Lint + unit tests must pass before merge.

---
## 14. Configuration & Validation
Required Environment (validated at startup via Pydantic Settings):

**Core Settings:**
| Var | Default | Notes |
|-----|---------|-------|
| DATABASE_URL | (required) | PostgreSQL connection |
| DATABASE_SCHEMA | (required) | Schema name |
| ANALYSIS_DIR | (required) | Output directory |

**LLM Provider Settings:**
| Var | Default | Notes |
|-----|---------|-------|
| LLM_PROVIDER | ollama | "ollama" or "openrouter" |
| OLLAMA_HOST | (required) | Ollama server URL |
| MODEL | (required) | Default model name |
| OPENROUTER_API_KEY | (none) | Required for OpenRouter |
| OPENROUTER_MODEL | (none) | Override model for OpenRouter |

**LLM Caching Settings:**
| Var | Default | Notes |
|-----|---------|-------|
| LLM_CACHE_ENABLED | false | Enable LLM caching |
| LLM_CACHE_L2_ENABLED | false | Enable Redis L2 |
| LLM_CACHE_REDIS_URL | (none) | Redis connection URL |
| LLM_GATEWAY_VERSION | v1 | Bump to invalidate cache |

**Loki Cache Settings:**
| Var | Default | Notes |
|-----|---------|-------|
| LOKI_CACHE_ENABLED | true | Enable Loki caching |
| LOKI_CACHE_REDIS_ENABLED | false | Enable Redis persistence |
| LOKI_CACHE_TTL_SECONDS | 14400 | 4 hours for general queries |
| LOKI_CACHE_TRACE_TTL_SECONDS | 21600 | 6 hours for trace-specific queries |

**Feature Flags:**
| Var | Default | Notes |
|-----|---------|-------|
| USE_DB_PROMPTS | false | DB-backed prompts |
| USE_DB_SETTINGS | false | DB-backed settings |
| USE_DB_PROJECTS | false | DB-backed projects |

Validation Method: Pydantic BaseSettings in `app/config.py`.

---
## 15. Immediate Action Plan (Sprint 1) - Updated

**Completed:**
| Priority | Task | Status | Notes |
|----------|------|--------|-------|
| P0 | Remove hardcoded params (orchestrator) | ✅ | Uses ParametersAgent |
| P0 | Define models + migration (Prompts, Settings, Projects) | ✅ | Phases 1-4 complete |
| P0 | Implement services layer | ✅ | PromptService, ConfigService, ProjectService |
| P2 | ProviderAdapter abstraction | ✅ | Ollama + OpenRouter |
| P2 | LLM response caching | ✅ | L1/L2 gateway |
| P2 | Loki query caching | ✅ | Redis-backed cache |
| - | Planning agent | ✅ | With clarification questions |

**In Progress / Pending:**
| Priority | Task | Status | Notes |
|----------|------|--------|-------|
| P0 | Define models (Conversations, Messages) | 🔴 | Next phase |
| P1 | SessionManager (DB-based) | 🔴 | Expiry logic |
| P1 | TraceContext model + set-trace endpoint | 🔴 | Links active trace |
| P1 | Context rules DB migration | 🔴 | Phase 5 |
| P1 | Admin API endpoints | 🔴 | Phase 6 |
| P2 | Streaming protocol upgrades | 🟡 | token events |
| P2 | Quick tools endpoints | 🔴 | extract-fields/mask-pii |

Dependency Note: Conversation models -> Session persistence -> Trace context.

---
## 16. Acceptance Criteria (Phase 1 & 2)
| Criterion | Verification Procedure | Phase |
|-----------|------------------------|-------|
| Real parameter extraction (no stub) | Log shows extracted keys; no hardcoded dict present | 1 |
| Conversation persisted | Restart server; GET shows same conversation id | 1 |
| Message history retrieval | POST 2 messages; list returns both chronologically | 1 |
| Session timeout enforced | Simulate expiry; stale session returns 404 / new session created | 2 |
| Active trace persisted | Set trace; conversation.active_trace_id matches; row exists trace_context | 2 |
| Trace summary generated async | After set-trace, summary field populated within SLA (<5s small logs) | 2 |
| Error code mapping works | Force LLM timeout; receive LLM_TIMEOUT in error event | 2 |
| Model selection stored | Create conv with selected_model; retrieval shows same | 2 |

---
## 17. Risks & Mitigations
| Risk | Probability | Impact | Mitigation | Trigger Point |
|------|-------------|--------|------------|---------------|
| Delay modeling -> API slip | Medium | High | Start models Day 1 | If day 2 no PR |
| LLM latency spikes | High | Medium | Timeout + partial summary | >95th > threshold |
| Scope creep (viewer state early) | Medium | Medium | Defer viewer_state to P2 | PR review |
| Large log ingestion memory spike | Medium | High | Stream parse + size cap | OOM warning |
| Multi-provider complexity | Low | Medium | Stub interface early | Adapter design |

---
## 18. Streaming Event Examples
Step Event: {"event":"step","title":"Trace Summary","detail":{"trace_id":"abc123"}}  
Token Event: {"event":"token","token":"The","idx":0}  
Error Event: {"event":"error","code":"LLM_TIMEOUT","message":"Model timed out","recoverable":true}

---
## 19. Developer Workflow (Updated Quick Start)
1. Remove stub in orchestrator (uncomment param_agent.run, delete hardcoded dict).  
2. Add models file(s) under app/models + repositories under app/db/repositories.py.  
3. Generate migration: alembic revision --autogenerate -m "add_core_models"  
4. Apply: alembic upgrade head  
5. Implement endpoints (conversation create, message post, set-trace).  
6. Add error_codes.py + middleware/utility for mapping exceptions.  
7. Add basic tests (repositories + conversation flow).  
8. Upgrade streaming events to include error + token types.  
9. Introduce ProviderAdapter scaffolding (OllamaAdapter only).  
10. Add metrics counters (simple wrapper).  

---
## 20. Change Log
| Date | Version | Change |
|------|---------|--------|
| 2025-12-19 | 0.5.0 | Updated status matrix, added LLM caching/providers, updated testing roadmap |
| 2025-09-14 | 0.4.0 | Added interfaces, metrics, error codes, streaming protocol, lifecycle & refined roadmap |
| 2025-09-14 | 0.3.0 | UI feature integration draft (superseded) |
| 2025-01-14 | 0.2.0 | Combined specs with UI requirements |
| 2024-12-?? | 0.1.0 | Initial planning draft |

---
## 21. Appendix A: Future / Deferred (Post-Phase 4)
- Embedding-based semantic memory & retrieval augmentation.
- Automatic timeline visualization service.
- WebSocket duplex transport with cancel event.
- Background summarization scheduler / housekeeping cron.
- Export analysis bundle (JSON + HTML report).
- Multi-tenant isolation (org_id scoping) if required.

---
## 22. Appendix B: Open Questions
| Question | Decision Needed By | Notes |
|----------|--------------------|-------|
| Sync vs Async SQLAlchemy first? | Before model impl | Recommend sync first for speed |
| Include viewer_state in Phase 1? | After trace APIs | Likely defer |
| Summarization: LLM vs heuristic fallback? | Before Phase 2 | Provide simple stats fallback |

---
## 23. Requirements Coverage Summary
| Requirement | Covered Section |
|------------|-----------------|
| Persistence & Models | 5, 15 | 
| Streaming Protocol | 7, 18 |
| Error Handling | 8 |
| Provider Abstraction | 10 |
| Trace Context | 11 |
| Security & Limits | 12 |
| Testing Roadmap | 13 |
| Acceptance Criteria | 16 |
| Metrics & Observability | 9 |

End of specification.
