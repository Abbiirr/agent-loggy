# Database Configuration Migration Plan

## Overview

Migrate 50+ hardcoded configurations from code to PostgreSQL with versioning, TTL caching, and hot-reload support.

### User Requirements
- DB-configurable project logic (add new projects without code changes)
- Versioned prompts with rollback capability
- Hot-reload with TTL cache
- Priority: Prompts first

---

## Phase 1: Infrastructure Setup

### 1.1 Create Cache Infrastructure

**New file:** `app/services/cache.py`
- TTLCache class with thread-safe in-memory caching
- CacheManager for centralized cache management
- Default TTL: 5 minutes for prompts, 10 minutes for settings

### 1.2 Database Session Management

**New file:** `app/db/session.py`
- SQLAlchemy session factory with dependency injection for FastAPI

---

## Phase 2: Prompt Management System (Priority)

### 2.1 Database Schema

**Migration:** `alembic/versions/xxxx_add_prompts_versioned.py`

```sql
CREATE TABLE agent_loggy.prompts_versioned (
    id              SERIAL PRIMARY KEY,
    prompt_name     VARCHAR(255) NOT NULL,
    version         INTEGER NOT NULL DEFAULT 1,
    prompt_content  TEXT NOT NULL,
    variables       JSONB DEFAULT '{}',
    agent_name      VARCHAR(100),
    prompt_type     VARCHAR(50),  -- 'system', 'user'
    is_active       BOOLEAN DEFAULT TRUE,
    created_by      VARCHAR(100),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deactivated_at  TIMESTAMP NULL,
    CONSTRAINT uq_prompt_name_version UNIQUE(prompt_name, version)
);

CREATE TABLE agent_loggy.prompt_history (
    id              SERIAL PRIMARY KEY,
    prompt_id       INTEGER REFERENCES agent_loggy.prompts_versioned(id),
    action          VARCHAR(20) NOT NULL,
    old_content     TEXT,
    new_content     TEXT,
    changed_by      VARCHAR(100),
    changed_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 Models

**New file:** `app/models/prompt.py`
- PromptVersioned model
- PromptHistory model

### 2.3 Service Layer

**New file:** `app/services/prompt_service.py`
- `get_active_prompt(prompt_name)` - Get active version with caching
- `render_prompt(prompt_name, variables)` - Template rendering
- `create_version(prompt_name, content)` - Create new version, deactivate old
- `rollback_to_version(prompt_name, version)` - Rollback capability
- `get_version_history(prompt_name)` - List all versions

### 2.4 Prompts to Migrate

| Prompt Name                 | Agent           | File:Lines                 |
|-----------------------------|-----------------|----------------------------|
| parameter_extraction_system | parameter_agent | parameter_agent.py:166-193 |
| trace_analysis_system       | analyze_agent   | analyze_agent.py:293-294   |
| trace_analysis_user         | analyze_agent   | analyze_agent.py:235-286   |
| entries_analysis_system     | analyze_agent   | analyze_agent.py:370       |
| entries_analysis_user       | analyze_agent   | analyze_agent.py:335-362   |
| quality_assessment_system   | analyze_agent   | analyze_agent.py:422       |
| quality_assessment_user     | analyze_agent   | analyze_agent.py:396-416   |
| relevance_analysis_system   | verify_agent    | verify_agent.py:485-486    |
| relevance_analysis_user     | verify_agent    | verify_agent.py:425-478    |

### 2.5 Agent Modifications

**Files to modify:**
- `app/agents/parameter_agent.py` - Replace `_build_system_prompt()` to use PromptService
- `app/agents/analyze_agent.py` - Replace hardcoded prompts in `_analyze_single_trace()`, etc.
- `app/agents/verify_agent.py` - Replace prompts in `_analyze_relevance_with_rag()`

---

## Phase 3: Settings/Config System

### 3.1 Database Schema

**Migration:** `alembic/versions/xxxx_add_app_settings.py`

```sql
CREATE TABLE agent_loggy.app_settings (
    id              SERIAL PRIMARY KEY,
    category        VARCHAR(100) NOT NULL,
    setting_key     VARCHAR(255) NOT NULL,
    setting_value   TEXT NOT NULL,
    value_type      VARCHAR(50) NOT NULL,
    description     TEXT,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_category_key UNIQUE(category, setting_key)
);

CREATE TABLE agent_loggy.settings_history (
    id              SERIAL PRIMARY KEY,
    setting_id      INTEGER REFERENCES agent_loggy.app_settings(id),
    old_value       TEXT,
    new_value       TEXT,
    changed_by      VARCHAR(100),
    changed_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 Models & Service

**New files:**
- `app/models/settings.py` - AppSetting, SettingsHistory
- `app/services/config_service.py` - ConfigService with caching and fallback defaults

### 3.3 Settings to Migrate

| Category   | Key                  | Current Value              | File:Line                |
|------------|----------------------|----------------------------|--------------------------|
| ollama     | host                 | http://10.112.30.10:11434  | parameter_agent.py:19    |
| ollama     | timeout              | 30                         | parameter_agent.py:117   |
| ollama     | max_retries          | 3                          | parameter_agent.py:67    |
| loki       | base_url             | https://loki-gateway...    | loki_query_builder.py:8  |
| thresholds | highly_relevant      | 80                         | verify_agent.py:199      |
| thresholds | relevant             | 60                         | verify_agent.py:200      |
| thresholds | potentially_relevant | 40                         | verify_agent.py:201      |
| thresholds | batch_size           | 10                         | verify_agent.py:211      |
| paths      | analysis_output      | app/comprehensive_analysis | orchestrator.py:38       |
| paths      | verification_output  | app/verification_reports   | orchestrator.py:39       |
| agent      | allowed_query_keys   | [list]                     | parameter_agent.py:25-30 |
| agent      | excluded_query_keys  | [list]                     | parameter_agent.py:32-35 |
| agent      | allowed_domains      | [list]                     | parameter_agent.py:37-40 |
| agent      | domain_keywords      | [list]                     | parameter_agent.py:22    |

---

## Phase 4: Project Configuration System

### 4.1 Database Schema

**Migration:** `alembic/versions/xxxx_add_projects.py`

```sql
CREATE TABLE agent_loggy.projects (
    id              SERIAL PRIMARY KEY,
    project_code    VARCHAR(50) NOT NULL UNIQUE,
    project_name    VARCHAR(255) NOT NULL,
    log_source_type VARCHAR(50) NOT NULL,  -- 'file' or 'loki'
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE agent_loggy.project_settings (
    id              SERIAL PRIMARY KEY,
    project_id      INTEGER REFERENCES agent_loggy.projects(id),
    setting_key     VARCHAR(255) NOT NULL,
    setting_value   TEXT NOT NULL,
    value_type      VARCHAR(50) NOT NULL,
    CONSTRAINT uq_project_setting UNIQUE(project_id, setting_key)
);

CREATE TABLE agent_loggy.environments (
    id              SERIAL PRIMARY KEY,
    project_id      INTEGER REFERENCES agent_loggy.projects(id),
    env_code        VARCHAR(50) NOT NULL,
    loki_namespace  VARCHAR(100),
    log_base_path   VARCHAR(500),
    is_active       BOOLEAN DEFAULT TRUE,
    CONSTRAINT uq_project_env UNIQUE(project_id, env_code)
);
```

### 4.2 Models & Service

**New files:**
- `app/models/project.py` - Project, ProjectSetting, Environment
- `app/services/project_service.py` - ProjectService with `is_file_based()`, `is_loki_based()`

### 4.3 Orchestrator Modification

**File:** `app/orchestrator.py`

Replace hardcoded branching (lines 78, 86, 110, 122, 131, 165, 189, 205):

```python
# Before
if project in ("MMBL", "UCB"):
    ...
elif project in ("NCC", "ABBL"):
    ...

# After
if self.project_service.is_file_based(project):
    ...
elif self.project_service.is_loki_based(project):
    ...
```

---

## Phase 5: Context Rules Migration

### 5.1 Database Schema

```sql
CREATE TABLE agent_loggy.context_rules (
    id                  SERIAL PRIMARY KEY,
    context             VARCHAR(100) NOT NULL,
    important_patterns  TEXT[] NOT NULL,
    ignore_patterns     TEXT[] NOT NULL,
    description         TEXT,
    is_active           BOOLEAN DEFAULT TRUE,
    priority            INTEGER DEFAULT 0
);

CREATE TABLE agent_loggy.negate_rules (
    id              SERIAL PRIMARY KEY,
    label           VARCHAR(100) NOT NULL,
    operator        VARCHAR(10) NOT NULL,
    value           VARCHAR(500) NOT NULL,
    is_active       BOOLEAN DEFAULT TRUE
);
```

### 5.2 Files to Modify

- `app/agents/verify_agent.py` - Replace `_load_context_rules()` (lines 68-116)
- `app/orchestrator.py` - Replace CSV reading for negate_keys (lines 42-58)

---

## Phase 6: Admin API Endpoints

**New file:** `app/routers/admin.py`

| Endpoint                                     | Method   | Purpose              |
|----------------------------------------------|----------|----------------------|
| /api/admin/prompts                           | GET      | List all prompts     |
| /api/admin/prompts/{name}/history            | GET      | Get version history  |
| /api/admin/prompts/{name}                    | POST     | Create new version   |
| /api/admin/prompts/{name}/rollback/{version} | POST     | Rollback to version  |
| /api/admin/settings                          | GET      | List settings        |
| /api/admin/settings/{category}/{key}         | PUT      | Update setting       |
| /api/admin/projects                          | GET/POST | List/create projects |
| /api/admin/cache/invalidate                  | POST     | Hot-reload trigger   |

---

## Implementation Order

### Week 1: Infrastructure

1. Create `app/services/cache.py`
2. Create `app/db/session.py`
3. Create base models structure

### Week 2: Prompts (Priority)

1. Run migration for prompts_versioned tables
2. Implement `app/models/prompt.py`
3. Implement `app/services/prompt_service.py`
4. Create data migration script to seed prompts from code
5. Modify `parameter_agent.py` to use PromptService
6. Modify `analyze_agent.py` to use PromptService
7. Modify `verify_agent.py` to use PromptService

### Week 3: Settings

1. Run migration for app_settings tables
2. Implement `app/models/settings.py`
3. Implement `app/services/config_service.py`
4. Seed settings from hardcoded values
5. Modify agents to use ConfigService

### Week 4: Projects

1. Run migration for projects tables
2. Implement `app/models/project.py`
3. Implement `app/services/project_service.py`
4. Seed project data (MMBL, UCB, NCC, ABBL)
5. Modify `orchestrator.py` to use ProjectService

### Week 5: Context Rules & Admin API

1. Run migration for context_rules, negate_rules
2. Migrate CSV data to database
3. Implement admin API endpoints
4. Update `verify_agent.py` to load rules from DB
5. Update `orchestrator.py` to load negate rules from DB

---

## Files to Create

```
app/
├── db/
│   └── session.py              # NEW
├── models/
│   ├── __init__.py             # NEW
│   ├── prompt.py               # NEW
│   ├── settings.py             # NEW
│   ├── project.py              # NEW
│   └── context_rule.py         # NEW
├── services/
│   ├── __init__.py             # NEW
│   ├── cache.py                # NEW
│   ├── prompt_service.py       # NEW
│   ├── config_service.py       # NEW
│   └── project_service.py      # NEW
├── routers/
│   ├── __init__.py             # NEW
│   └── admin.py                # NEW
```

## Files to Modify

| File                                 | Changes                                       |
|--------------------------------------|-----------------------------------------------|
| app/agents/parameter_agent.py        | Use PromptService, ConfigService              |
| app/agents/analyze_agent.py          | Use PromptService                             |
| app/agents/verify_agent.py           | Use PromptService, ConfigService              |
| app/orchestrator.py                  | Use ProjectService, load negate rules from DB |
| app/tools/loki/loki_query_builder.py | Use ConfigService for BASE_URL                |
| app/main.py                          | Add admin router, DB session dependency       |
| app/db/base.py                       | Import new models                             |

---

## Rollback Strategy

- Each phase can be rolled back independently via Alembic downgrade
- Feature flags in `app/config.py` for gradual enablement:
  - `USE_DB_PROMPTS: bool = False`
  - `USE_DB_SETTINGS: bool = False`
  - `USE_DB_PROJECTS: bool = False`
