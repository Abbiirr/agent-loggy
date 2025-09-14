# Chatbot / Log Analysis System Enhancement Plan (Living Document)

Last Updated: 2025-09-14
Status Legend: ✅ Done | 🟡 In Progress | 🔜 Planned / Not Started | ❗ Issue / Blocking

---
## 1. Executive Summary
A log analysis + conversational assistant currently supports single-shot streaming analysis via an orchestrator and agents. Persistence, conversation continuity, context memory, structured models, error robustness, and routing are absent. This document tracks implementation state, priorities, and acceptance criteria.

---
## 2. Current Working Components (Verified)
| Area | Description | Status | Notes |
|------|-------------|--------|-------|
| Streaming | Basic SSE step updates | ✅ | Single request only, no resume |
| Orchestrator | Coordinates agents for analysis | ✅ | Contains hardcoded test params (remove) |
| Agents | analyze, parameter, planning, verify, report | ✅ | Modular, no persistence hooks |
| File Processing | Log search / parse | ✅ | Works on local JSON/text logs |
| LLM Integration | Ollama client usage | ✅ | No graceful fallback |
| Config | Basic config.py | ✅ | Lacks env validation & pooling |
| Alembic Base | Initial migration file exists | ✅ | Only initial schema present |

---
## 3. Critical Gaps / Issues
| ID | Gap / Issue | Impact | Status | Resolution Path |
|----|-------------|--------|--------|-----------------|
| G1 | Hardcoded test params in orchestrator (lines 89-95) | Skews analysis | ❗ | Remove + integrate real extraction |
| G2 | No DB models for conversations / messages / sessions | No history | 🔜 | Add SQLAlchemy models + migration |
| G3 | No session persistence | Loss on restart | 🔜 | SessionManager + DB / optional Redis cache |
| G4 | No conversation memory / context window | Stateless answers | 🔜 | ContextBuilder + MemoryService |
| G5 | No intent routing (chat vs analysis) | User friction | 🔜 | Lightweight rules -> later ML |
| G6 | Sparse error handling & retries | Poor resilience | 🔜 | Standard error map + retry policy |
| G7 | No structured logging + trace correlation | Hard debugging | 🔜 | Add logger w/ trace_id injection |
| G8 | No rate / size limits | Potential overload | 🔜 | Enforce max log bytes / message length |
| G9 | No tests (unit/integration) | Regression risk | 🔜 | Introduce pytest + minimal coverage |
| G10 | No environment validation | Runtime surprises | 🔜 | Pydantic settings or manual checks |

---
## 4. Target Architecture (Incremental)
Flow: Request -> SessionManager -> (Create/Load Conversation) -> IntentRouter -> (Analysis Path or Chat Path) -> ContextBuilder (bounded window + memory summaries) -> Orchestrator (agents) -> Stream (SSE/WebSocket) -> Persist Results (Messages + AnalysisResult) -> Post-process (verification/report) -> Emit final summary.

---
## 5. Data Model (Proposed)
| Model | Key Fields | Notes |
|-------|------------|-------|
| Conversation | id, created_at, updated_at, title(optional) | Title auto from first user prompt |
| Message | id, conversation_id (fk), role(user|assistant|system), content, token_count, created_at | Indexed (conversation_id, created_at) |
| Session | id, conversation_id, last_active_at, expires_at, state(json) | Stateless fallback if missing |
| AnalysisResult | id, conversation_id, input_hash, summary, raw_parameters(json), created_at | Deduplicate via input_hash |
| MemorySnapshot (later) | id, conversation_id, window_start_id, window_end_id, summary_text, created_at | Optional Phase 3 |

Acceptance: All models migrated, CRUD tested, indices created.

---
## 6. Services (Planned Modules)
| Service | Responsibility | Done? |
|---------|----------------|-------|
| SessionManager | Create / resume / expire sessions | 🔜 |
| ContextBuilder | Retrieve last N messages + summarization fallback | 🔜 |
| ChatService | Orchestrate chat vs analysis path | 🔜 |
| MemoryService | Summarize & compress history beyond window | 🔜 |
| IntentRouter | Rule-based classification (logs attached? keywords?) | 🔜 |
| Persistence Layer (repos) | Encapsulate DB operations | 🔜 |

---
## 7. API Endpoints (Roadmap)
| Endpoint | Purpose | Status | Notes |
|----------|---------|--------|-------|
| POST /api/conversations | Create conversation | 🔜 | Returns conversation_id |
| GET /api/conversations/{id} | Metadata | 🔜 | 404 if missing |
| GET /api/conversations/{id}/messages | Paginated history | 🔜 | ?page & limit |
| POST /api/conversations/{id}/messages | Send new message | 🔜 | Returns streamed response handle |
| DELETE /api/conversations/{id} | Close conversation | 🔜 | Soft delete flag |
| GET /api/health | Basic health & dependencies | 🔜 | DB + LLM status |

---
## 8. Streaming Transport
| Aspect | Current | Target |
|--------|---------|--------|
| Protocol | SSE only | SSE + optional WebSocket (config ENABLE_WEBSOCKET) |
| Resume Support | None | Provide conversation_id + last_message_id (Phase 4) |
| Event Types | step, done | step, token, warning, error, done |

---
## 9. Error Handling & Resilience
| Category | Strategy |
|----------|----------|
| LLM Timeout | Retry (max 2) then partial result with warning |
| Missing Logs | Return structured error code LOG_NOT_FOUND |
| DB Failure | Attempt reconnect once; surface SERVICE_UNAVAILABLE |
| Oversized Input | Reject early (413) + guideline message |
| Unexpected Exception | Capture stack, return GENERIC_ERROR token in stream |

Add error map module: error_codes.py.

---
## 10. Configuration & Env
Required Vars (added progressively):
DATABASE_URL
DATABASE_POOL_SIZE=5
SESSION_TIMEOUT_MINUTES=30
MAX_CONTEXT_MESSAGES=20
ENABLE_WEBSOCKET=false
MAX_LOG_BYTES=524288
LOG_LEVEL=INFO

Validation: Fail fast if mandatory values missing.

---
## 11. Dependencies
| Package | Needed For | Status |
|---------|------------|--------|
| sqlalchemy | ORM models | 🔜 |
| alembic | Migrations | ✅ (init only) |
| asyncpg | Async driver (if async path) | 🔜 (decide sync vs async) |
| redis | Session caching (optional) | 🔜 |
| pydantic | Settings / validation | 🔜 |
| pytest | Testing | 🔜 |

Decision Pending: adopt sync SQLAlchemy first (lower complexity), defer async until stability.

---
## 12. Metrics & Observability (Planned)
| Metric | Purpose |
|--------|---------|
| analysis_duration_ms | Performance baseline |
| tokens_generated | LLM usage tracking |
| cache_hit_rate (sessions) | Redis efficiency |
| error_rate_per_min | Stability |
| active_conversations | Capacity planning |

Add structured logging w/ trace_id (already embedded in log artifacts) + optional OpenTelemetry future.

---
## 13. Security & Compliance
| Concern | Mitigation |
|---------|-----------|
| PII in logs | (Phase 3) Optional regex redaction layer |
| Injection via user content | Escape before persistence; no raw SQL |
| Resource exhaustion | Size + timeout limits |
| Credential leakage | Centralize secrets via env only |

---
## 14. Testing Strategy
| Layer | Tests |
|-------|-------|
| Unit | Agents (parameter extraction, verification), orchestrator branches |
| Integration | DB migrations + CRUD, streaming endpoint end-to-end |
| Load (later) | Concurrent conversations (Phase 4) |
| Regression | Fixtures of representative log sets |

Coverage Goal Phase 2: 40% lines core modules. Phase 4: 70%.

---
## 15. Phased Implementation & Status
| Phase | Scope | Deliverables | Status |
|-------|-------|-------------|--------|
| 1 | Database foundation | Models + migration + CRUD tests | 🔜 |
| 2 | Session persistence | SessionManager + replace in-memory | 🔜 |
| 3 | Context & memory | ContextBuilder + window + summarization stub | 🔜 |
| 4 | Enhanced chat & transport | IntentRouter + improved streaming + resume | 🔜 |
| 5 (Optional) | Optimization | Caching, summarization compression, metrics dashboards | 🔜 |

Gate Criteria: Each phase requires passing tests + updated docs before proceeding.

---
## 16. Immediate Action Checklist (Next Sprint)
| Priority | Task | Owner (TBD) | Status |
|----------|------|-------------|--------|
| P0 | Remove hardcoded params in orchestrator |  | ❗ |
| P0 | Decide sync vs async DB approach |  | 🔜 |
| P0 | Add models: Conversation, Message, AnalysisResult, Session |  | 🔜 |
| P0 | Create Alembic migration for models |  | 🔜 |
| P1 | Introduce repository layer (db/repositories.py) |  | 🔜 |
| P1 | Add pydantic settings module |  | 🔜 |
| P1 | Implement SessionManager using DB |  | 🔜 |
| P2 | Basic API endpoints (create conversation, post message) |  | 🔜 |
| P2 | Add error map + consistent JSON error responses |  | 🔜 |
| P2 | Write initial pytest config + first 5 tests |  | 🔜 |
| P3 | ContextBuilder (fetch last N messages) |  | 🔜 |
| P3 | IntentRouter (rule-based) |  | 🔜 |

---
## 17. Risk Register
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|-----------|
| Scope creep (async + Redis early) | Medium | Medium | Freeze core scope until Phase 2 complete |
| LLM instability / latency | High | Medium | Add timeout + fallback partial summary |
| Log size explosion | Medium | High | Enforce MAX_LOG_BYTES + optional sampling |
| DB migration drift | Low | Medium | Versioned Alembic workflow & review |

---
## 18. Acceptance Criteria (Phase 2 Minimal Viable Conversational System)
1. Can create conversation and send at least two sequential messages with prior context included.
2. Hardcoded orchestrator test params removed; real extraction path exercised.
3. Messages persist across process restart (manual restart test).
4. Errors surface structured JSON or streamed error event.
5. Basic unit tests pass in CI command.

---
## 19. Deferred / Future Enhancements
- Semantic search over historical logs
- Embedding-based memory compression
- WebSocket bi-directional incremental token stream
- Admin dashboard (metrics + traces)
- Pluggable LLM provider abstraction

---
## 20. Change Log
| Date | Change |
|------|--------|
| 2025-09-14 | Comprehensive status matrix & phased roadmap added |

---
## 21. Action Summary (TL;DR)
Immediate: (1) Remove hardcoded params, (2) Add core models + migration, (3) Implement SessionManager + persistence, (4) Minimal API endpoints, (5) Introduce tests.

---
## Appendix A: Original High-Level Plan (Archived Reference)
... (Retained conceptually; superseded by sections above.)
