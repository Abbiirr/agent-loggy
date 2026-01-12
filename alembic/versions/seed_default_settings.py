"""Seed default app_settings for Phase 3 configuration

Revision ID: seed_default_settings
Revises: seed_negate_rules
Create Date: 2025-01-12

This migration seeds default values for:
- Loki configuration (base_url)
- Threshold settings (highly_relevant, relevant, potentially_relevant)
- Path settings (analysis_output, verification_output)
"""
from alembic import op
import sqlalchemy as sa
import json

# revision identifiers, used by Alembic.
revision = 'seed_default_settings'
down_revision = 'seed_negate_rules'
branch_labels = None
depends_on = None


def get_schema():
    try:
        from app.config import settings
        return settings.DATABASE_SCHEMA
    except:
        return "public"


SCHEMA = get_schema()

# Default settings to seed
DEFAULT_SETTINGS = [
    # Loki settings
    {
        "category": "loki",
        "setting_key": "base_url",
        "setting_value": "https://loki-gateway.local.fintech23.xyz/loki/api/v1/query_range",
        "value_type": "string",
        "description": "Loki API endpoint for log queries"
    },
    # Threshold settings
    {
        "category": "thresholds",
        "setting_key": "highly_relevant",
        "setting_value": "80",
        "value_type": "int",
        "description": "Score threshold for highly relevant classification (0-100)"
    },
    {
        "category": "thresholds",
        "setting_key": "relevant",
        "setting_value": "60",
        "value_type": "int",
        "description": "Score threshold for relevant classification (0-100)"
    },
    {
        "category": "thresholds",
        "setting_key": "potentially_relevant",
        "setting_value": "40",
        "value_type": "int",
        "description": "Score threshold for potentially relevant classification (0-100)"
    },
    {
        "category": "thresholds",
        "setting_key": "batch_size",
        "setting_value": "10",
        "value_type": "int",
        "description": "Batch size for relevance analysis"
    },
    # Path settings
    {
        "category": "paths",
        "setting_key": "analysis_output",
        "setting_value": "app/comprehensive_analysis",
        "value_type": "string",
        "description": "Output directory for analysis reports"
    },
    {
        "category": "paths",
        "setting_key": "verification_output",
        "setting_value": "app/verification_reports",
        "value_type": "string",
        "description": "Output directory for verification reports"
    },
]


def upgrade() -> None:
    """Seed default settings in app_settings table."""
    for setting in DEFAULT_SETTINGS:
        # Use dollar-quoting for values that might contain special chars
        op.execute(f"""
            INSERT INTO {SCHEMA}.app_settings
            (category, setting_key, setting_value, value_type, description, is_active, created_at, updated_at)
            VALUES (
                '{setting["category"]}',
                '{setting["setting_key"]}',
                $val${setting["setting_value"]}$val$,
                '{setting["value_type"]}',
                $desc${setting["description"]}$desc$,
                true,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (category, setting_key) DO UPDATE
            SET setting_value = EXCLUDED.setting_value,
                description = EXCLUDED.description,
                updated_at = CURRENT_TIMESTAMP;
        """)


def downgrade() -> None:
    """Remove seeded settings from app_settings."""
    categories = set(s["category"] for s in DEFAULT_SETTINGS)
    for category in categories:
        op.execute(f"""
            DELETE FROM {SCHEMA}.app_settings
            WHERE category = '{category}';
        """)
