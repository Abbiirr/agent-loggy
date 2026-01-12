"""Add conversations, messages, and pipeline_executions tables

Revision ID: add_conversations
Revises: add_knowledge_base
Create Date: 2025-01-12

This migration creates:
1. conversations table - Persistent conversation sessions
2. messages table - Individual messages in conversations
3. pipeline_executions table - Tracks analysis runs within conversations

These tables enable multi-session persistent chat with message history,
context retention, and pipeline execution tracking.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = 'add_conversations'
down_revision = 'add_knowledge_base'
branch_labels = None
depends_on = None


def get_schema():
    try:
        from app.config import settings
        return settings.DATABASE_SCHEMA
    except:
        return "public"


SCHEMA = get_schema()


def upgrade() -> None:
    """Create conversations, messages, and pipeline_executions tables."""

    # ─── conversations table ───────────────────────────────────────
    op.create_table(
        'conversations',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('conversation_id', sa.String(100), nullable=False),
        sa.Column('project_code', sa.String(50), nullable=True),
        sa.Column('env', sa.String(50), nullable=True),
        sa.Column('domain', sa.String(100), nullable=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('summary_token_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('conversation_id', name='uq_conversations_conversation_id'),
        schema=SCHEMA
    )

    # Indexes for conversations
    op.create_index('idx_conversations_conversation_id', 'conversations',
                    ['conversation_id'], schema=SCHEMA)
    op.create_index('idx_conversations_project', 'conversations',
                    ['project_code'], schema=SCHEMA)
    op.create_index('idx_conversations_status', 'conversations',
                    ['status'], schema=SCHEMA)
    op.create_index('idx_conversations_active', 'conversations',
                    ['is_active'], schema=SCHEMA)
    op.create_index('idx_conversations_created', 'conversations',
                    ['created_at'], schema=SCHEMA)
    op.create_index('idx_conversations_updated', 'conversations',
                    ['updated_at'], schema=SCHEMA)

    # ─── messages table ────────────────────────────────────────────
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('message_type', sa.String(50), nullable=True),
        sa.Column('message_metadata', JSONB, nullable=True),
        sa.Column('token_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['conversation_id'],
            [f'{SCHEMA}.conversations.id'],
            name='fk_messages_conversation',
            ondelete='CASCADE'
        ),
        schema=SCHEMA
    )

    # Indexes for messages
    op.create_index('idx_messages_conversation', 'messages',
                    ['conversation_id'], schema=SCHEMA)
    op.create_index('idx_messages_role', 'messages',
                    ['role'], schema=SCHEMA)
    op.create_index('idx_messages_type', 'messages',
                    ['message_type'], schema=SCHEMA)
    op.create_index('idx_messages_created', 'messages',
                    ['created_at'], schema=SCHEMA)

    # ─── pipeline_executions table ─────────────────────────────────
    op.create_table(
        'pipeline_executions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('conversation_id', sa.Integer(), nullable=False),
        sa.Column('execution_id', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('extracted_params', JSONB, nullable=True),
        sa.Column('plan', JSONB, nullable=True),
        sa.Column('trace_ids', JSONB, nullable=True),
        sa.Column('report_files', JSONB, nullable=True),
        sa.Column('cache_diagnostics', JSONB, nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('execution_id', name='uq_executions_execution_id'),
        sa.ForeignKeyConstraint(
            ['conversation_id'],
            [f'{SCHEMA}.conversations.id'],
            name='fk_executions_conversation',
            ondelete='CASCADE'
        ),
        schema=SCHEMA
    )

    # Indexes for pipeline_executions
    op.create_index('idx_executions_execution_id', 'pipeline_executions',
                    ['execution_id'], schema=SCHEMA)
    op.create_index('idx_executions_conversation', 'pipeline_executions',
                    ['conversation_id'], schema=SCHEMA)
    op.create_index('idx_executions_status', 'pipeline_executions',
                    ['status'], schema=SCHEMA)
    op.create_index('idx_executions_started', 'pipeline_executions',
                    ['started_at'], schema=SCHEMA)

    # ─── Triggers ──────────────────────────────────────────────────
    # Create updated_at trigger for conversations table
    # First check if the trigger function exists (created in initial_schema)
    op.execute(f"""
        DO $$
        BEGIN
            -- Create trigger function if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM pg_proc p
                JOIN pg_namespace n ON p.pronamespace = n.oid
                WHERE n.nspname = '{SCHEMA}' AND p.proname = 'update_updated_at_column'
            ) THEN
                CREATE OR REPLACE FUNCTION {SCHEMA}.update_updated_at_column()
                RETURNS TRIGGER AS $func$
                BEGIN
                    NEW.updated_at = CURRENT_TIMESTAMP;
                    RETURN NEW;
                END;
                $func$ LANGUAGE plpgsql;
            END IF;
        END $$;
    """)

    op.execute(f"""
        CREATE TRIGGER trg_conversations_updated_at
        BEFORE UPDATE ON {SCHEMA}.conversations
        FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.update_updated_at_column();
    """)


def downgrade() -> None:
    """Remove conversations, messages, and pipeline_executions tables."""

    # Drop trigger first
    op.execute(f"""
        DROP TRIGGER IF EXISTS trg_conversations_updated_at ON {SCHEMA}.conversations;
    """)

    # Drop indexes for pipeline_executions
    op.drop_index('idx_executions_started', table_name='pipeline_executions', schema=SCHEMA)
    op.drop_index('idx_executions_status', table_name='pipeline_executions', schema=SCHEMA)
    op.drop_index('idx_executions_conversation', table_name='pipeline_executions', schema=SCHEMA)
    op.drop_index('idx_executions_execution_id', table_name='pipeline_executions', schema=SCHEMA)

    # Drop pipeline_executions table
    op.drop_table('pipeline_executions', schema=SCHEMA)

    # Drop indexes for messages
    op.drop_index('idx_messages_created', table_name='messages', schema=SCHEMA)
    op.drop_index('idx_messages_type', table_name='messages', schema=SCHEMA)
    op.drop_index('idx_messages_role', table_name='messages', schema=SCHEMA)
    op.drop_index('idx_messages_conversation', table_name='messages', schema=SCHEMA)

    # Drop messages table
    op.drop_table('messages', schema=SCHEMA)

    # Drop indexes for conversations
    op.drop_index('idx_conversations_updated', table_name='conversations', schema=SCHEMA)
    op.drop_index('idx_conversations_created', table_name='conversations', schema=SCHEMA)
    op.drop_index('idx_conversations_active', table_name='conversations', schema=SCHEMA)
    op.drop_index('idx_conversations_status', table_name='conversations', schema=SCHEMA)
    op.drop_index('idx_conversations_project', table_name='conversations', schema=SCHEMA)
    op.drop_index('idx_conversations_conversation_id', table_name='conversations', schema=SCHEMA)

    # Drop conversations table
    op.drop_table('conversations', schema=SCHEMA)
