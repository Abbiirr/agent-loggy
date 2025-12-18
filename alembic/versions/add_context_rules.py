"""Add context_rules table and seed default rules

Revision ID: add_context_rules
Revises: seed_initial_prompts
Create Date: 2025-12-18

This migration creates the context_rules table for RAG-based relevance analysis
and seeds the default context rules.

Context rules define what patterns are important vs. ignorable for specific contexts
(e.g., MFS, bKash, transactions).
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_context_rules'
down_revision = 'seed_initial_prompts'
branch_labels = None
depends_on = None


def get_schema():
    try:
        from app.config import settings
        return settings.DATABASE_SCHEMA
    except:
        return "public"


SCHEMA = get_schema()

# Default context rules
DEFAULT_RULES = [
    {
        'context': 'mfs',
        'important': 'processPayment,transferMoney,balanceInquiry',
        'ignore': 'MFS_TRANSFER_STATUS_UPDATE_SCHEDULER_INVOCATION_TOPIC,HEARTBEAT,HEALTH_CHECK',
        'description': 'MFS payment processing - ignore scheduled status updates and health checks'
    },
    {
        'context': 'transactions',
        'important': 'transaction_created,payment_processed,amount,merchant',
        'ignore': 'session_cleanup,cache_refresh,log_rotation',
        'description': 'Transaction processing - focus on actual transactions, ignore maintenance'
    },
    {
        'context': 'bkash',
        'important': 'bkash_payment,mobile_wallet,OTP_verification',
        'ignore': 'bkash_heartbeat,connection_pool_stats',
        'description': 'bKash payments - ignore connection maintenance'
    },
]


def upgrade() -> None:
    """Create context_rules table and seed default rules."""

    # Create context_rules table
    op.create_table(
        'context_rules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('context', sa.String(length=100), nullable=False),
        sa.Column('important', sa.Text(), nullable=True),
        sa.Column('ignore', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA
    )

    # Create indexes
    op.create_index('idx_context_rules_context', 'context_rules', ['context'], schema=SCHEMA)
    op.create_index('idx_context_rules_active', 'context_rules', ['is_active'], schema=SCHEMA)

    # Seed default rules
    for rule in DEFAULT_RULES:
        op.execute(f"""
            INSERT INTO {SCHEMA}.context_rules
            (context, important, ignore, description, is_active, created_at, updated_at)
            VALUES (
                '{rule['context']}',
                '{rule['important']}',
                '{rule['ignore']}',
                $desc${rule['description']}$desc$,
                true,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            );
        """)


def downgrade() -> None:
    """Drop context_rules table."""
    op.drop_index('idx_context_rules_active', table_name='context_rules', schema=SCHEMA)
    op.drop_index('idx_context_rules_context', table_name='context_rules', schema=SCHEMA)
    op.drop_table('context_rules', schema=SCHEMA)
