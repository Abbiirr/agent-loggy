#!/usr/bin/env python
"""
Create the database schema specified in DATABASE_SCHEMA environment variable.

Run this script before running migrations:
    uv run python scripts/create_schema.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from app.config import settings


def create_schema():
    """Create the database schema if it doesn't exist."""
    schema_name = settings.DATABASE_SCHEMA
    database_url = settings.DATABASE_URL

    print(f"Connecting to database...")
    print(f"Target schema: {schema_name}")

    engine = create_engine(database_url)

    try:
        with engine.connect() as conn:
            # Check if schema exists
            result = conn.execute(text(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"
            ), {"schema": schema_name})
            exists = result.fetchone() is not None

            if exists:
                print(f"Schema '{schema_name}' already exists.")
            else:
                # Create schema
                conn.execute(text(f'CREATE SCHEMA "{schema_name}"'))
                conn.commit()
                print(f"Schema '{schema_name}' created successfully!")

            # Verify
            result = conn.execute(text(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"
            ), {"schema": schema_name})
            if result.fetchone():
                print(f"Verified: Schema '{schema_name}' exists.")
            else:
                print(f"ERROR: Schema '{schema_name}' was not created!")
                sys.exit(1)

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    create_schema()
