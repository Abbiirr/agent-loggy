# Development Guide

This guide covers setting up the development environment, running tests, and contributing to agent-loggy.

## Prerequisites

- **Python 3.11+**
- **PostgreSQL 14+**
- **Ollama** (for LLM inference)
- **uv** (Python package manager)

## Quick Start

### 1. Clone and Install Dependencies

```bash
git clone <repository-url>
cd agent-loggy
uv sync
```

### 2. Configure Environment

Create a `.env` file in the project root:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/agent_loggy
DATABASE_SCHEMA=agent_loggy

# Ollama
OLLAMA_HOST=http://localhost:11434
MODEL=llama3

# Feature flags (optional)
USE_DB_PROMPTS=false
USE_DB_SETTINGS=false
USE_DB_PROJECTS=false

# Output directories
ANALYSIS_DIR=app/comprehensive_analysis
```

### 3. Set Up Database

```bash
# Run migrations
uv run alembic upgrade head

# Seed initial data
uv run python scripts/seed_prompts.py
uv run python scripts/seed_settings.py
uv run python scripts/seed_projects.py
```

See [docs/schema-setup-guide.md](./schema-setup-guide.md) for detailed database setup.

### 4. Start Ollama

```bash
# Pull required model
ollama pull llama3

# Start Ollama server (if not running)
ollama serve
```

### 5. Run Development Server

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API is now available at `http://localhost:8000`.

---

## Project Structure

```
agent-loggy/
├── app/
│   ├── agents/           # LLM-powered agents
│   ├── db/               # Database layer (SQLAlchemy)
│   ├── models/           # ORM models
│   ├── routers/          # FastAPI route handlers
│   ├── schemas/          # Pydantic request/response models
│   ├── services/         # Business logic services
│   ├── tools/            # Utility tools and integrations
│   │   └── loki/         # Loki log backend integration
│   ├── tests/            # Test suite
│   ├── evals/            # Evaluation framework
│   ├── config.py         # Settings management
│   ├── main.py           # FastAPI application
│   ├── orchestrator.py   # Main analysis pipeline
│   └── startup.py        # Application lifespan events
├── alembic/              # Database migrations
│   └── versions/         # Migration scripts
├── scripts/              # Utility scripts
├── docs/                 # Documentation
├── app_settings/         # CSV configuration files
├── pyproject.toml        # Project dependencies
└── .env                  # Environment variables
```

---

## Development Workflow

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest app/tests/test_cache.py

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=app
```

### Database Migrations

```bash
# Check current migration version
uv run alembic current

# Show migration history
uv run alembic history

# Generate new migration (auto-detect model changes)
uv run alembic revision --autogenerate -m "add_new_table"

# Generate empty migration (manual)
uv run alembic revision -m "custom_migration"

# Apply all pending migrations
uv run alembic upgrade head

# Rollback one migration
uv run alembic downgrade -1

# Rollback to specific version
uv run alembic downgrade add_prompts_versioned

# Rollback all migrations
uv run alembic downgrade base
```

### Adding Dependencies

```bash
# Add production dependency
uv add <package>

# Add development dependency
uv add --dev <package>
```

---

## Code Patterns

### Adding a New Agent

1. Create agent file in `app/agents/`:

```python
# app/agents/my_agent.py
from ollama import Client

class MyAgent:
    def __init__(self, client: Client, model: str):
        self.client = client
        self.model = model

    def run(self, input_text: str) -> dict:
        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": "Your system prompt here"},
                {"role": "user", "content": input_text}
            ]
        )
        # Parse and return structured result
        return {"result": response["message"]["content"]}
```

2. Integrate with orchestrator if needed.

### Adding a New Model

1. Create model in `app/models/`:

```python
# app/models/my_model.py
from sqlalchemy import Column, Integer, String, Boolean
from app.db.base import Base
from app.config import settings

class MyModel(Base):
    __tablename__ = "my_table"
    __table_args__ = {"schema": settings.DATABASE_SCHEMA}

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
```

2. Import in `app/models/__init__.py`:

```python
from app.models.my_model import MyModel
```

3. Generate migration:

```bash
uv run alembic revision --autogenerate -m "add_my_table"
```

4. Apply migration:

```bash
uv run alembic upgrade head
```

### Adding a New API Endpoint

1. Create router in `app/routers/`:

```python
# app/routers/my_router.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/my-resource", tags=["my-resource"])

@router.get("")
async def list_items():
    return {"items": []}

@router.post("")
async def create_item(data: dict):
    return {"created": data}
```

2. Register in `app/main.py`:

```python
from app.routers.my_router import router as my_router
app.include_router(my_router)
```

### Adding a New Service

1. Create service in `app/services/`:

```python
# app/services/my_service.py
from sqlalchemy.orm import Session
from app.services.cache import cached

class MyService:
    def __init__(self, db: Session):
        self.db = db

    @cached(ttl=300)  # Cache for 5 minutes
    def get_item(self, item_id: int):
        # Fetch from database
        pass
```

2. Export in `app/services/__init__.py`.

---

## Docker Development

### Using Docker Compose

```bash
# Start all services
docker compose up

# Start with auto-rebuild on changes
docker compose up --watch

# Rebuild images
docker compose build

# Stop services
docker compose down
```

### Docker Compose Services

| Service | Port | Description |
|---------|------|-------------|
| `app` | 8000 | FastAPI application |
| `postgres` | 5432 | PostgreSQL database |

---

## Debugging

### Logging

The application uses Python's standard logging:

```python
import logging
logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

Log level is set to `INFO` by default. Configure in `app/main.py`.

### Database Debugging

Enable SQLAlchemy query logging:

```python
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)
```

### API Debugging

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Testing

### Test Structure

```
app/tests/
├── __init__.py
├── test_cache.py           # Cache service tests
└── test_trace_id_extractor.py  # Trace ID extraction tests
```

### Writing Tests

```python
# app/tests/test_my_feature.py
import pytest

def test_basic_functionality():
    result = my_function()
    assert result == expected_value

@pytest.mark.asyncio
async def test_async_functionality():
    result = await my_async_function()
    assert result is not None
```

### Test Fixtures

Common fixtures are defined in `conftest.py` (create if needed).

---

## Evaluation Framework

The `app/evals/` directory contains an evaluation framework for testing agent performance:

```bash
# Run evaluations
uv run python -m app.evals.cli
```

### Evaluation Datasets

Located in `app/evals/datasets/`:
- `parameter_extraction.json` - Test cases for parameter extraction
- `relevance_analysis.json` - Test cases for relevance analysis
- `trace_analysis.json` - Test cases for trace analysis

---

## Common Issues

### Database Connection Errors

**Error**: `could not connect to server`

**Solution**: Ensure PostgreSQL is running and `DATABASE_URL` is correct.

### Ollama Connection Errors

**Error**: `Connection refused to Ollama`

**Solution**:
1. Ensure Ollama is running: `ollama serve`
2. Check `OLLAMA_HOST` in `.env`

### Migration Errors

**Error**: `Target database is not up to date`

**Solution**: Run `uv run alembic upgrade head`

### Import Errors

**Error**: `ModuleNotFoundError`

**Solution**:
1. Ensure virtual environment is active
2. Run `uv sync` to install dependencies

---

## Code Style

- **Formatting**: Use black or ruff for code formatting
- **Imports**: Group by standard library, third-party, local
- **Type hints**: Use type annotations for function signatures
- **Docstrings**: Use docstrings for public functions and classes

```bash
# Format code
uv run ruff format app/

# Check linting
uv run ruff check app/
```

---

## Contributing

1. Create a feature branch from `main`
2. Make changes and add tests
3. Run tests: `uv run pytest`
4. Submit a pull request

### Commit Message Format

```
<type>: <description>

Types:
- FEAT: New feature
- FIX: Bug fix
- DOCS: Documentation changes
- REFACTOR: Code refactoring
- TEST: Test additions/changes
- CHORE: Maintenance tasks
```
