"""Add prompt evaluation tables

Revision ID: add_eval_tables
Revises: update_param_prompt
Create Date: 2025-12-17

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_eval_tables'
down_revision = 'update_param_prompt'
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
    # Create prompt_eval_runs table (one row per evaluation run)
    op.create_table(
        'prompt_eval_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('prompt_name', sa.String(length=255), nullable=False),
        sa.Column('prompt_version', sa.Integer(), nullable=False),
        sa.Column('dataset_name', sa.String(length=100), nullable=False),
        sa.Column('run_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('total_cases', sa.Integer(), nullable=True),
        sa.Column('passed', sa.Integer(), nullable=True),
        sa.Column('failed', sa.Integer(), nullable=True),
        sa.Column('accuracy', sa.Float(), nullable=True),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA
    )

    # Create indexes for prompt_eval_runs
    op.create_index('idx_eval_runs_prompt_name', 'prompt_eval_runs', ['prompt_name'], schema=SCHEMA)
    op.create_index('idx_eval_runs_run_at', 'prompt_eval_runs', ['run_at'], schema=SCHEMA)
    op.create_index('idx_eval_runs_prompt_version', 'prompt_eval_runs', ['prompt_name', 'prompt_version'], schema=SCHEMA)

    # Create prompt_eval_cases table (individual test case results)
    op.create_table(
        'prompt_eval_cases',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('case_id', sa.String(length=100), nullable=True),
        sa.Column('input_text', sa.Text(), nullable=True),
        sa.Column('expected', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('actual', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('passed', sa.Boolean(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.ForeignKeyConstraint(['run_id'], [f'{SCHEMA}.prompt_eval_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA
    )

    # Create indexes for prompt_eval_cases
    op.create_index('idx_eval_cases_run_id', 'prompt_eval_cases', ['run_id'], schema=SCHEMA)
    op.create_index('idx_eval_cases_passed', 'prompt_eval_cases', ['passed'], schema=SCHEMA)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_eval_cases_passed', table_name='prompt_eval_cases', schema=SCHEMA)
    op.drop_index('idx_eval_cases_run_id', table_name='prompt_eval_cases', schema=SCHEMA)
    op.drop_table('prompt_eval_cases', schema=SCHEMA)

    op.drop_index('idx_eval_runs_prompt_version', table_name='prompt_eval_runs', schema=SCHEMA)
    op.drop_index('idx_eval_runs_run_at', table_name='prompt_eval_runs', schema=SCHEMA)
    op.drop_index('idx_eval_runs_prompt_name', table_name='prompt_eval_runs', schema=SCHEMA)
    op.drop_table('prompt_eval_runs', schema=SCHEMA)
