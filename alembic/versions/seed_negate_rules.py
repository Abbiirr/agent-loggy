"""Seed negate rules in app_settings table

Revision ID: seed_negate_rules
Revises: add_conversations
Create Date: 2025-01-12

This migration seeds the negate_rules category in app_settings with
default log filtering terms. These are used to exclude noise from Loki queries.
"""
from alembic import op
import sqlalchemy as sa
import json

# revision identifiers, used by Alembic.
revision = 'seed_negate_rules'
down_revision = 'add_conversations'
branch_labels = None
depends_on = None


def get_schema():
    try:
        from app.config import settings
        return settings.DATABASE_SCHEMA
    except:
        return "public"


SCHEMA = get_schema()

# Default negate terms - these are used to filter out noise from log queries
DEFAULT_NEGATE_TERMS = [
    "processMfsStatusUpdateInvocationEvent",
    "MFS_TRANSFER_STATUS_UPDATE_SCHEDULER_INVOCATION_TOPIC",
    "HEARTBEAT",
    "HEALTH_CHECK",
    "health_check",
    "healthcheck",
    "connection_pool_stats",
    "session_cleanup",
    "cache_refresh",
]


def upgrade() -> None:
    """Seed negate_rules in app_settings table."""
    # Insert negate_rules as JSON list
    terms_json = json.dumps(DEFAULT_NEGATE_TERMS)

    op.execute(f"""
        INSERT INTO {SCHEMA}.app_settings
        (category, setting_key, setting_value, value_type, description, is_active, created_at, updated_at)
        VALUES (
            'negate_rules',
            'terms',
            '{terms_json}',
            'json',
            'List of terms to exclude from Loki log queries (noise filtering)',
            true,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        ON CONFLICT (category, setting_key) DO UPDATE
        SET setting_value = EXCLUDED.setting_value,
            updated_at = CURRENT_TIMESTAMP;
    """)


def downgrade() -> None:
    """Remove negate_rules from app_settings."""
    op.execute(f"""
        DELETE FROM {SCHEMA}.app_settings
        WHERE category = 'negate_rules' AND setting_key = 'terms';
    """)
