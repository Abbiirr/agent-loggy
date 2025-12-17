# Database Configuration Migration - Implementation TODO

## Phase 0: Pre-requisites
- [x] Create `app/models/` directory with `__init__.py`
- [x] Create `app/services/` directory with `__init__.py`
- [x] Create `app/routers/` directory with `__init__.py`

## Phase 1: Infrastructure Setup
- [x] Create `app/services/cache.py` - TTLCache class with thread-safe caching
- [x] Create `app/db/session.py` - SQLAlchemy session factory with FastAPI DI

## Phase 2: Prompt Management System (Priority) ✅ COMPLETE
- [x] Create Alembic migration for `prompts_versioned` and `prompt_history` tables
- [x] Create `app/models/prompt.py` - PromptVersioned, PromptHistory models
- [x] Create `app/services/prompt_service.py` - PromptService with caching
- [x] Create data migration script to seed prompts from code (`scripts/seed_prompts.py`)
- [x] Modify `app/agents/parameter_agent.py` to use PromptService
- [x] Modify `app/agents/analyze_agent.py` to use PromptService
- [x] Modify `app/agents/verify_agent.py` to use PromptService

## Phase 3: Settings/Config System ✅ COMPLETE
- [x] Create Alembic migration for `app_settings` and `settings_history` tables
- [x] Create `app/models/settings.py` - AppSetting, SettingsHistory models
- [x] Create `app/services/config_service.py` - ConfigService with caching
- [x] Create data migration script to seed settings from hardcoded values (`scripts/seed_settings.py`)
- [x] Modify `app/agents/parameter_agent.py` to use ConfigService

## Phase 4: Project Configuration System ✅ COMPLETE
- [x] Create Alembic migration for `projects`, `project_settings`, `environments` tables
- [x] Create `app/models/project.py` - Project, ProjectSetting, Environment models
- [x] Create `app/services/project_service.py` - ProjectService
- [x] Create seed script for project data (`scripts/seed_projects.py`)
- [x] Modify `app/orchestrator.py` to use ProjectService (8 branching points)

## Phase 5: Context Rules Migration
- [ ] Create Alembic migration for `context_rules` and `negate_rules` tables
- [ ] Create `app/models/context_rule.py` - ContextRule, NegateRule models
- [ ] Migrate CSV data to database
- [ ] Update `app/agents/verify_agent.py` to load rules from DB
- [ ] Update `app/orchestrator.py` to load negate rules from DB

## Phase 6: Admin API Endpoints
- [ ] Create `app/routers/admin.py` with endpoints:
  - [ ] GET /api/admin/prompts - List all prompts
  - [ ] GET /api/admin/prompts/{name}/history - Get version history
  - [ ] POST /api/admin/prompts/{name} - Create new version
  - [ ] POST /api/admin/prompts/{name}/rollback/{version} - Rollback
  - [ ] GET /api/admin/settings - List settings
  - [ ] PUT /api/admin/settings/{category}/{key} - Update setting
  - [ ] GET/POST /api/admin/projects - List/create projects
  - [ ] POST /api/admin/cache/invalidate - Hot-reload trigger
- [ ] Add admin router to `app/main.py`

## Rollback Feature Flags (in app/config.py)
- [x] Add `USE_DB_PROMPTS: bool = False`
- [x] Add `USE_DB_SETTINGS: bool = False`
- [x] Add `USE_DB_PROJECTS: bool = False`

---

## Files Created

| File | Purpose |
|------|---------|
| `app/models/__init__.py` | Models package initialization |
| `app/models/prompt.py` | PromptVersioned, PromptHistory SQLAlchemy models |
| `app/models/settings.py` | AppSetting, SettingsHistory SQLAlchemy models |
| `app/models/project.py` | Project, ProjectSetting, Environment SQLAlchemy models |
| `app/services/__init__.py` | Services package initialization |
| `app/services/cache.py` | TTLCache, CacheManager for caching |
| `app/services/prompt_service.py` | PromptService with versioning & caching |
| `app/services/config_service.py` | ConfigService with caching & fallback defaults |
| `app/services/project_service.py` | ProjectService with is_file_based/is_loki_based helpers |
| `app/routers/__init__.py` | Routers package initialization |
| `app/db/__init__.py` | Database module exports |
| `app/db/session.py` | SQLAlchemy session factory & FastAPI DI |
| `alembic/versions/add_prompts_versioned.py` | Migration for prompts tables |
| `alembic/versions/add_app_settings.py` | Migration for settings tables |
| `alembic/versions/add_projects.py` | Migration for projects, project_settings, environments tables |
| `scripts/seed_prompts.py` | Data migration script for prompts (9 prompts) |
| `scripts/seed_settings.py` | Data migration script for settings (14 settings) |
| `scripts/seed_projects.py` | Data migration script for projects (4 projects: MMBL, UCB, NCC, ABBL) |
| `app/tests/test_cache.py` | Unit tests for cache infrastructure |

## Files Modified

| File | Changes |
|------|---------|
| `app/config.py` | Added feature flags (USE_DB_PROMPTS, USE_DB_SETTINGS, USE_DB_PROJECTS) |
| `alembic/env.py` | Import models for autogenerate |
| `app/agents/parameter_agent.py` | Added PromptService + ConfigService integration with fallback |
| `app/agents/analyze_agent.py` | Added PromptService integration with fallback |
| `app/agents/verify_agent.py` | Added PromptService integration with fallback |
| `app/orchestrator.py` | Replaced 8 hardcoded project checks with `is_file_based()` / `is_loki_based()` |

## Test Results

All 28 tests passing:
- 16 cache tests (TTLCache, CacheManager, @cached decorator)
- 12 trace ID extractor tests

## Next Steps

1. Run migrations: `uv run alembic upgrade head`
2. Seed data:
   - `uv run python scripts/seed_prompts.py`
   - `uv run python scripts/seed_settings.py`
   - `uv run python scripts/seed_projects.py`
3. Enable feature flags in `.env`:
   - `USE_DB_PROMPTS=true`
   - `USE_DB_SETTINGS=true`
   - `USE_DB_PROJECTS=true`
4. Continue with Phase 5 (Context Rules Migration)
