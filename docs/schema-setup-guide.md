# Database Schema Setup Guide

This guide documents how to set up the PostgreSQL schema and run migrations.

## Quick Start (Recommended)

### First-time Setup

```bash
# 1. Configure .env
DATABASE_URL=postgresql://user:password@host:5432/agent_loggy
DATABASE_SCHEMA=log_chat

# 2. Run migrations manually (once)
uv run alembic upgrade head

# 3. Seed data
uv run python scripts/seed_prompts.py
uv run python scripts/seed_settings.py
uv run python scripts/seed_projects.py

# 4. Start the server
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Subsequent Starts

The server automatically:
1. Creates the schema if missing (for fresh installs)
2. Checks if migrations are up to date
3. Warns if migrations are needed

**Startup logs:**
```
INFO  Initializing database schema: log_chat
INFO  Database schema 'log_chat' exists
INFO  Database migrations up to date
INFO  Ollama is up and running
INFO  Application startup complete.
```

---

## Manual Setup (Alternative)

If you prefer to run setup steps manually before starting the server:

### Step 1: Update Environment Configuration

Edit the `.env` file in the project root:

```bash
DATABASE_URL=postgresql://user:password@host:5432/agent_loggy
DATABASE_SCHEMA=log_chat
```

**What this does:** Sets the target schema name to `log_chat`. All tables will be created within this schema.

---

### Step 2: Create the Schema in PostgreSQL

Run the schema creation script:

```bash
uv run python scripts/create_schema.py
```

**What this does:** Reads `DATABASE_URL` and `DATABASE_SCHEMA` from `.env`, connects to the database, and creates the schema if it doesn't exist.

**Expected output:**
```
Connecting to database...
Target schema: log_chat
Schema 'log_chat' created successfully!
Verified: Schema 'log_chat' exists.
```

If the schema already exists:
```
Connecting to database...
Target schema: log_chat
Schema 'log_chat' already exists.
Verified: Schema 'log_chat' exists.
```

---

### Step 3: Run Database Migrations

Apply all Alembic migrations:

```bash
uv run alembic upgrade head
```

**What this does:** Runs all migrations in sequence:
1. `initial_schema` - Creates base tables and utility functions
2. `add_prompts_versioned` - Creates prompts and prompt_history tables
3. `add_app_settings` - Creates app_settings and settings_history tables
4. `add_projects` - Creates projects, project_settings, and environments tables

**Expected output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 1b671ff38c8c, initial_schema
INFO  [alembic.runtime.migration] Running upgrade 1b671ff38c8c -> add_prompts_versioned, add_prompts_versioned
INFO  [alembic.runtime.migration] Running upgrade add_prompts_versioned -> add_app_settings, add_app_settings
INFO  [alembic.runtime.migration] Running upgrade add_app_settings -> add_projects, add_projects
```

**To verify:**
```bash
uv run alembic current
```

Expected output: `add_projects (head)`

---

### Step 4: Seed Initial Data

Run the seed scripts to populate initial data:

**4a. Seed Prompts (9 prompts for LLM agents):**
```bash
uv run python scripts/seed_prompts.py
```

**Expected output:**
```
Starting prompt seeding...
  Created 'parameter_extraction_system' (version 1)
  Created 'parameter_extraction_user' (version 1)
  ...
Seeding complete! 9 prompts processed.
```

**4b. Seed Settings (14 configuration settings):**
```bash
uv run python scripts/seed_settings.py
```

**Expected output:**
```
Starting settings seeding...
  Created 'ollama.host' = http://10.112.30.10:11434 (string)
  Created 'ollama.timeout' = 30 (int)
  ...
Seeding complete! 14 settings processed.
```

**4c. Seed Projects (4 projects: MMBL, UCB, NCC, ABBL):**
```bash
uv run python scripts/seed_projects.py
```

**Expected output:**
```
Starting project seeding...
  Created project 'MMBL' (id=1, type=file)
    - Environment 'prod' added
    - Environment 'staging' added
  Created project 'UCB' (id=2, type=file)
    ...
Seeding complete! 4 projects processed.
```

---

### Step 5: Enable Feature Flags (Optional)

To use database-backed configurations instead of hardcoded defaults, update `.env`:

```bash
USE_DB_PROMPTS=true
USE_DB_SETTINGS=true
USE_DB_PROJECTS=true
```

**Note:** The application will work without these flags enabled. When disabled, it falls back to hardcoded defaults in the service layer.

---

## Verification

### Check Tables Exist

```bash
uv run python scripts/verify_schema.py
```

**Expected output:**
```
Schema: log_chat
Tables found:
  - alembic_version
  - app_settings
  - environments
  - project_settings
  - projects
  - prompt_history
  - prompts_versioned
  - settings_history

Data counts:
  - prompts_versioned: 9 rows
  - app_settings: 14 rows
  - projects: 4 rows
  - environments: 8 rows
```

---

## Rollback Instructions

If you need to undo the setup:

### Rollback Migrations (keeps schema)
```bash
uv run alembic downgrade base
```

### Drop Schema Entirely (destructive)
```bash
uv run python scripts/drop_schema.py
```

**Warning:** This will delete all tables and data in the schema!

---

## Summary of Commands

### Automatic (Recommended)

| Step | Command |
|------|---------|
| 1. Update .env | Edit `DATABASE_SCHEMA=log_chat` |
| 2. Start server | `uv run uvicorn app.main:app --host 0.0.0.0 --port 8000` |
| 3. Seed prompts | `uv run python scripts/seed_prompts.py` |
| 4. Seed settings | `uv run python scripts/seed_settings.py` |
| 5. Seed projects | `uv run python scripts/seed_projects.py` |
| 6. Enable flags | Edit `.env` with `USE_DB_*=true` |

Schema creation and migrations run automatically on server startup.

### Manual

| Step | Command |
|------|---------|
| 1. Update .env | Edit `DATABASE_SCHEMA=log_chat` |
| 2. Create schema | `uv run python scripts/create_schema.py` |
| 3. Run migrations | `uv run alembic upgrade head` |
| 4a. Seed prompts | `uv run python scripts/seed_prompts.py` |
| 4b. Seed settings | `uv run python scripts/seed_settings.py` |
| 4c. Seed projects | `uv run python scripts/seed_projects.py` |
| 5. Enable flags | Edit `.env` with `USE_DB_*=true` |
