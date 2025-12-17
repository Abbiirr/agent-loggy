"""Add prompts_versioned and prompt_history tables

Revision ID: add_prompts_versioned
Revises: 1b671ff38c8c
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_prompts_versioned'
down_revision = '1b671ff38c8c'
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
    # Create prompts_versioned table
    op.create_table(
        'prompts_versioned',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('prompt_name', sa.String(length=255), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('prompt_content', sa.Text(), nullable=False),
        sa.Column('variables', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('agent_name', sa.String(length=100), nullable=True),
        sa.Column('prompt_type', sa.String(length=50), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_by', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('deactivated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('prompt_name', 'version', name='uq_prompt_name_version'),
        schema=SCHEMA
    )

    # Create indexes for prompts_versioned
    op.create_index('idx_prompts_versioned_name', 'prompts_versioned', ['prompt_name'], schema=SCHEMA)
    op.create_index('idx_prompts_versioned_active', 'prompts_versioned', ['prompt_name', 'is_active'], schema=SCHEMA)

    # Create prompt_history table
    op.create_table(
        'prompt_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('prompt_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=20), nullable=False),
        sa.Column('old_content', sa.Text(), nullable=True),
        sa.Column('new_content', sa.Text(), nullable=True),
        sa.Column('changed_by', sa.String(length=100), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['prompt_id'], [f'{SCHEMA}.prompts_versioned.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA
    )

    # Create indexes for prompt_history
    op.create_index('idx_prompt_history_prompt_id', 'prompt_history', ['prompt_id'], schema=SCHEMA)
    op.create_index('idx_prompt_history_changed_at', 'prompt_history', ['changed_at'], schema=SCHEMA)

    # Create triggers for updated_at (using the existing function from initial migration)
    op.execute(f"""
        CREATE TRIGGER trg_prompts_versioned_updated_at
        BEFORE UPDATE ON {SCHEMA}.prompts_versioned
        FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.update_updated_at_column();
    """)


def downgrade() -> None:
    # Drop trigger
    op.execute(f"DROP TRIGGER IF EXISTS trg_prompts_versioned_updated_at ON {SCHEMA}.prompts_versioned;")

    # Drop tables
    op.drop_index('idx_prompt_history_changed_at', table_name='prompt_history', schema=SCHEMA)
    op.drop_index('idx_prompt_history_prompt_id', table_name='prompt_history', schema=SCHEMA)
    op.drop_table('prompt_history', schema=SCHEMA)

    op.drop_index('idx_prompts_versioned_active', table_name='prompts_versioned', schema=SCHEMA)
    op.drop_index('idx_prompts_versioned_name', table_name='prompts_versioned', schema=SCHEMA)
    op.drop_table('prompts_versioned', schema=SCHEMA)
