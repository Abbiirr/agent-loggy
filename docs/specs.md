# Log Analysis Chatbot / Trace Viewer Backend Specification (Living Document)

Version: 0.4.0  
Last Updated: 2025-09-14  
Status Legend: ✅ Done | 🟡 In Progress | 🔴 Not Started | ❗ Blocking | ⚠ Risky / Needs Decision

Purpose: Provide an authoritative snapshot of current state, target architecture, implementation roadmap, and verifiable acceptance criteria for the conversational log / trace analysis platform.

---
## 1. Project Snapshot (Current Reality)
| Area | Present in Repo | Notes |
|------|-----------------|-------|
| Orchestrator | ✅ (app/orchestrator.py) | Hardcoded parameter dict (must remove) |
| Agents | ✅ (parameter, analyze, verify, planning, report) | Stateless; no persistence hooks |
| Streaming | ✅ (SSE via main/orchestrator flow) | No resume, no tokens, only coarse steps |
| Config | ✅ (app/config.py) | No env validation / defaults enforcement |
| Persistence Layer | ⚠ Partial (app/db/base.py) | No domain models / repositories |
| Alembic | ✅ (initial revision) | Schema incomplete (no conversation/message/etc.) |
| Schemas (Pydantic) | ✅ (app/schemas/*.py) | Limited to chat request/response; not aligned with planned models |
| Tests | 🔴 (empty app/tests) | Framework absent |
| Trace Reports | ✅ (app/comprehensive_analysis, verification_reports) | Generated artifacts not indexed |
| Loki Log Assets | ✅ (app/loki_logs/*.json) | No retention / cleanup policy |
| Context Rules CSV | ✅ (app/app_settings) | Not integrated via documented algorithm |
| Multi-model Support | 🔴 | Only Ollama client used |
| UI-Specific State | 🔴 | No trace context or viewer state persistence |

Critical Blocker: Hardcoded parameter extraction stub in orchestrator prevents real flow validation.

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
| Parameter Extraction | Hardcoded dict | Agent-driven parse | ❗ | Remove stub | Low |
| Conversation Persistence | None | conversations + messages tables | 🔴 | Models | Medium |
| Sessions | In-memory | DB + optional Redis TTL | 🔴 | Models | Medium |
| Trace Context | Not stored | trace_context table + API | 🔴 | Models | Medium |
| Analysis Results | Files only | DB + hash dedupe | 🔴 | Models | Low |
| Streaming Protocol | step/done | token/step/warning/error/done | 🔴 | None | Low |
| Provider Abstraction | Direct Ollama | Strategy + adapters | 🔴 | Refactor orchestrator | Medium |
| Quick Tools | Absent | Endpoints (extract, mask) | 🔴 | Trace context | Low |
| Error Handling | Ad-hoc logging | Unified codes + mapping | 🔴 | Error module | Low |
| Metrics | None | Basic counters/timers | 🔴 | Instrumentation | Low |
| Tests | None | Unit + integration baseline | 🔴 | Harness | High |
| Logging | print/logger mix | Structured + trace_id | 🔴 | Logger setup | Low |

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
Adapter Registry keyed by provider name.  
Selection Precedence: (conversation.selected_model) -> default (config DEFAULT_MODEL).  
Fallback Policy: On UNSUPPORTED_MODEL -> fallback to default + warning event.  
Planned Adapters: OllamaAdapter (✅ baseline), OpenAIAdapter (🔴), AnthropicAdapter (🔴).

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
| Phase | Tests | Tools |
|-------|-------|-------|
| 1 | Unit: parameter extraction, repositories | pytest + fixtures |
| 2 | Integration: conversation CRUD, session expiry | ephemeral test DB |
| 3 | Streaming: SSE event ordering, error events | async test client |
| 4 | Provider fallback, trace context summarization | mock adapters |

Coverage Targets: 40% (Phase 2), 55% (Phase 3), 70% (Phase 4).  
CI Gate: Lint + unit tests must pass before merge (pre-commit hooks optional).

---
## 14. Configuration & Validation
Required Environment (validated at startup):
| Var | Default | Notes |
|-----|---------|-------|
| DATABASE_URL | (none) | Required Phase 1 |
| SESSION_TIMEOUT_MINUTES | 30 | Minutes to expiry |
| MAX_CONTEXT_MESSAGES | 20 | Sliding window size |
| MAX_LOG_BYTES | 524288 | ~512 KB cap per request |
| DEFAULT_MODEL | ollama:llama3 | Example value |
| ENABLE_WEBSOCKET | false | Future transport |
| LOG_LEVEL | INFO | Logging granularity |

Validation Method: pydantic BaseSettings (config module refactor P1).

---
## 15. Immediate Action Plan (Sprint 1)
| Priority | Task | Owner | Status | Notes |
|----------|------|-------|--------|-------|
| P0 | Remove hardcoded params (orchestrator) | TBD | ❗ | Switch back to param_agent.run |
| P0 | Define models + migration | TBD | 🔴 | Conversations, Messages, etc. |
| P0 | Implement repositories layer | TBD | 🔴 | CRUD isolation |
| P0 | Conversation create + message post endpoints | TBD | 🔴 | Minimal API |
| P1 | SessionManager (DB-based) | TBD | 🔴 | Expiry logic |
| P1 | TraceContext model + set-trace endpoint | TBD | 🔴 | Links active trace |
| P1 | Trace summary generation | TBD | 🔴 | Async step events |
| P1 | Error code module + mapping | TBD | 🔴 | Standard responses |
| P2 | ProviderAdapter abstraction | TBD | 🔴 | Begin with OllamaAdapter |
| P2 | Streaming protocol upgrades | TBD | 🔴 | token events |
| P2 | Quick tools endpoints | TBD | 🔴 | extract-fields/mask-pii |

Dependency Note: Models -> Repositories -> Services -> Endpoints -> Streaming upgrades.

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
