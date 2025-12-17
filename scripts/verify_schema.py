#!/usr/bin/env python
"""
Verify the database schema setup - check tables exist and data counts.

Run this script after migrations and seeding:
    uv run python scripts/verify_schema.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from app.config import settings


def verify_schema():
    """Verify the database schema setup."""
    schema_name = settings.DATABASE_SCHEMA
    database_url = settings.DATABASE_URL

    print(f"Schema: {schema_name}")

    engine = create_engine(database_url)

    try:
        with engine.connect() as conn:
            # Check if schema exists
            result = conn.execute(text(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"
            ), {"schema": schema_name})
            if not result.fetchone():
                print(f"ERROR: Schema '{schema_name}' does not exist!")
                sys.exit(1)

            # List tables
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = :schema
                ORDER BY table_name
            """), {"schema": schema_name})
            tables = [row[0] for row in result.fetchall()]

            if not tables:
                print("No tables found. Run migrations first:")
                print("  uv run alembic upgrade head")
                sys.exit(1)

            print("Tables found:")
            for t in tables:
                print(f"  - {t}")

            # Check data counts for main tables
            print("\nData counts:")
            data_tables = ['prompts_versioned', 'app_settings', 'projects', 'environments']
            for table in data_tables:
                if table in tables:
                    result = conn.execute(text(
                        f'SELECT COUNT(*) FROM "{schema_name}"."{table}"'
                    ))
                    count = result.scalar()
                    print(f"  - {table}: {count} rows")

            print("\nVerification complete!")

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    verify_schema()
