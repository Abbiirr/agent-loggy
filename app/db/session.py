# app/db/session.py
"""
SQLAlchemy session factory with FastAPI dependency injection.
Provides database session management for the application.
"""

import logging
from typing import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from alembic.config import Config
from alembic import command

from app.config import settings

logger = logging.getLogger(__name__)


# Create engine with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Enable connection health checks
    pool_recycle=3600,   # Recycle connections after 1 hour
)


# Set schema search path on connection
@event.listens_for(engine, "connect")
def set_search_path(dbapi_connection, connection_record):
    """Set the schema search path when a connection is established."""
    cursor = dbapi_connection.cursor()
    cursor.execute(f"SET search_path TO {settings.DATABASE_SCHEMA}, public")
    cursor.close()
    dbapi_connection.commit()


# Session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database session.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            return db.query(Item).all()

    Yields:
        SQLAlchemy Session instance
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database session (for use outside FastAPI routes).

    Usage:
        with get_db_session() as db:
            result = db.query(Model).all()

    Yields:
        SQLAlchemy Session instance
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def get_session() -> Session:
    """
    Get a new database session (caller is responsible for closing).

    Returns:
        SQLAlchemy Session instance
    """
    return SessionLocal()


def init_database():
    """Initialize database: create schema if needed and check migrations."""
    schema_name = settings.DATABASE_SCHEMA
    database_url = settings.DATABASE_URL

    logger.info(f"Initializing database schema: {schema_name}")

    init_engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with init_engine.connect() as conn:
            # Check if schema exists
            result = conn.execute(text(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"
            ), {"schema": schema_name})
            exists = result.fetchone() is not None

            if not exists:
                conn.execute(text(f'CREATE SCHEMA "{schema_name}"'))
                conn.commit()
                logger.info(f"Created database schema: {schema_name}")

                # Run migrations for fresh schema
                logger.info("Running database migrations...")
                alembic_cfg = Config("alembic.ini")
                command.upgrade(alembic_cfg, "head")
                logger.info("Database migrations complete")
            else:
                logger.info(f"Database schema '{schema_name}' exists")

                # Check migration version
                try:
                    result = conn.execute(text(
                        f'SELECT version_num FROM "{schema_name}".alembic_version'
                    ))
                    current_version = result.scalar()
                    if current_version == "add_projects":
                        logger.info("Database migrations up to date")
                    else:
                        logger.warning(f"Database at version '{current_version}', run: uv run alembic upgrade head")
                except Exception:
                    logger.warning("Migrations not applied. Run: uv run alembic upgrade head")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    finally:
        init_engine.dispose()
