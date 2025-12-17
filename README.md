# agent-loggy

## Overview

**agent-loggy** is a Python tool for automated log analysis and verification, designed to process banking or financial logs. It extracts parameters, searches log files, identifies unique trace IDs, compiles comprehensive trace data, and generates detailed analysis reports.

## Features

- Parameter extraction from user input using an LLM agent
- Log file searching and verification
- Trace ID extraction across multiple log files
- Compilation of comprehensive trace data per trace ID
- Automated creation of analysis and summary files
- Confidence scoring and summary reporting

## Project Structure

```
agent-loggy/
├── app/
│   ├── agents/                 # LLM-powered agents
│   │   ├── parameter_agent.py  # Extracts parameters from input text
│   │   ├── file_searcher.py    # Finds and verifies relevant log files
│   │   ├── analyze_agent.py    # Generates analysis reports
│   │   └── verify_agent.py     # Verification and relevance scoring
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── prompt.py           # Prompt versioning models
│   │   ├── settings.py         # App settings models
│   │   └── project.py          # Project configuration models
│   ├── services/               # Business logic layer
│   │   ├── cache.py            # TTL caching infrastructure
│   │   ├── prompt_service.py   # Prompt management with versioning
│   │   ├── config_service.py   # Configuration management
│   │   └── project_service.py  # Project configuration service
│   ├── tools/                  # Utility tools
│   │   ├── log_searcher.py     # Searches logs for patterns
│   │   ├── trace_id_extractor.py
│   │   ├── full_log_finder.py
│   │   └── loki/               # Loki log backend integration
│   ├── db/                     # Database utilities
│   │   ├── base.py             # SQLAlchemy Base class
│   │   └── session.py          # Session factory
│   └── orchestrator.py         # Main analysis pipeline
├── alembic/                    # Database migrations
│   ├── env.py
│   └── versions/
├── scripts/                    # Data seeding scripts
│   ├── seed_prompts.py
│   ├── seed_settings.py
│   └── seed_projects.py
└── app_settings/               # CSV-based configuration files
```

## Usage

### Installation

```bash
uv sync
```

### Running the Server

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Running Tests

```bash
uv run pytest
```

### Docker

```bash
docker compose up              # Run with PostgreSQL
docker compose up --watch      # Auto-rebuild on changes
```

## Database Migrations

This project uses **SQLAlchemy** for ORM and **Alembic** for schema migrations.

### How It Works

1. **Models** in `app/models/` define database tables as Python classes
2. **Migrations** in `alembic/versions/` track schema changes over time
3. **Seed scripts** in `scripts/` populate initial data

### Migration Chain

Migrations form a linked list via `revision` and `down_revision`:

```
initial_schema → add_prompts_versioned → add_app_settings → add_projects
```

### Common Commands

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# Rollback to specific revision
uv run alembic downgrade add_prompts_versioned

# Rollback everything
uv run alembic downgrade base

# Check current version
uv run alembic current

# Show migration history
uv run alembic history

# Generate new migration (auto-detect model changes)
uv run alembic revision --autogenerate -m "description"

# Create empty migration (manual)
uv run alembic revision -m "description"
```

### Seeding Data

After running migrations, seed initial data:

```bash
uv run python scripts/seed_prompts.py   # 9 prompts
uv run python scripts/seed_settings.py  # 14 settings
uv run python scripts/seed_projects.py  # 4 projects (MMBL, UCB, NCC, ABBL)
```

### Adding a New Model

1. Create model in `app/models/your_model.py`:
   ```python
   from app.db.base import Base
   from app.config import settings as app_settings

   class YourModel(Base):
       __tablename__ = "your_table"
       __table_args__ = {"schema": app_settings.DATABASE_SCHEMA}

       id = Column(Integer, primary_key=True)
       # ... other columns
   ```

2. Import in `app/models/__init__.py`:
   ```python
   from app.models.your_model import YourModel
   ```

3. Generate migration:
   ```bash
   uv run alembic revision --autogenerate -m "add your_table"
   ```

4. Review the generated migration in `alembic/versions/`

5. Apply migration:
   ```bash
   uv run alembic upgrade head
   ```

### Schema Configuration

This project uses a custom PostgreSQL schema (`agent_loggy`) configured via `DATABASE_SCHEMA` in `.env`. All tables are created within this schema rather than the default `public` schema.

### Feature Flags

Database-backed features can be toggled via environment variables:

```bash
USE_DB_PROMPTS=true    # Use prompts from database
USE_DB_SETTINGS=true   # Use settings from database
USE_DB_PROJECTS=true   # Use project config from database
```

When disabled, the system falls back to hardcoded defaults in the service layer.

## Configuration

Environment variables (via `.env` file):

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string |
| `DATABASE_SCHEMA` | Database schema name (default: `agent_loggy`) |
| `OLLAMA_HOST` | Ollama server URL |
| `MODEL` | LLM model name |
| `USE_DB_PROMPTS` | Enable database-backed prompts |
| `USE_DB_SETTINGS` | Enable database-backed settings |
| `USE_DB_PROJECTS` | Enable database-backed project config |

## Output Directories

- `app/comprehensive_analysis/` - Generated analysis reports
- `app/verification_reports/` - Verification output files
- `app/loki_logs/` - Downloaded Loki log files (temporary)
