#!/usr/bin/env python
"""
Drop the database schema (DESTRUCTIVE - deletes all tables and data).

Run this script to completely remove the schema:
    uv run python scripts/drop_schema.py

WARNING: This will delete ALL tables and data in the schema!
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy import create_engine, text
from app.config import settings


def drop_schema():
    """Drop the database schema."""
    schema_name = settings.DATABASE_SCHEMA
    database_url = settings.DATABASE_URL

    print(f"Target schema: {schema_name}")
    print("WARNING: This will DELETE ALL tables and data in this schema!")
    print()

    # Confirm
    confirm = input(f"Type '{schema_name}' to confirm deletion: ")
    if confirm != schema_name:
        print("Aborted. Schema was NOT dropped.")
        sys.exit(0)

    engine = create_engine(database_url)

    try:
        with engine.connect() as conn:
            # Check if schema exists
            result = conn.execute(text(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name = :schema"
            ), {"schema": schema_name})
            if not result.fetchone():
                print(f"Schema '{schema_name}' does not exist. Nothing to drop.")
                sys.exit(0)

            # Drop schema with CASCADE
            conn.execute(text(f'DROP SCHEMA "{schema_name}" CASCADE'))
            conn.commit()
            print(f"Schema '{schema_name}' dropped successfully!")

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    drop_schema()
