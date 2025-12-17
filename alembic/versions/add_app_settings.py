"""Add app_settings and settings_history tables

Revision ID: add_app_settings
Revises: add_prompts_versioned
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_app_settings'
down_revision = 'add_prompts_versioned'
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
    # Create app_settings table
    op.create_table(
        'app_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('setting_key', sa.String(length=255), nullable=False),
        sa.Column('setting_value', sa.Text(), nullable=False),
        sa.Column('value_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('category', 'setting_key', name='uq_category_key'),
        schema=SCHEMA
    )

    # Create indexes for app_settings
    op.create_index('idx_app_settings_category', 'app_settings', ['category'], schema=SCHEMA)
    op.create_index('idx_app_settings_key', 'app_settings', ['setting_key'], schema=SCHEMA)
    op.create_index('idx_app_settings_active', 'app_settings', ['is_active'], schema=SCHEMA)

    # Create settings_history table
    op.create_table(
        'settings_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('setting_id', sa.Integer(), nullable=False),
        sa.Column('old_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('changed_by', sa.String(length=100), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['setting_id'], [f'{SCHEMA}.app_settings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA
    )

    # Create indexes for settings_history
    op.create_index('idx_settings_history_setting_id', 'settings_history', ['setting_id'], schema=SCHEMA)
    op.create_index('idx_settings_history_changed_at', 'settings_history', ['changed_at'], schema=SCHEMA)

    # Create trigger for updated_at (using the existing function from initial migration)
    op.execute(f"""
        CREATE TRIGGER trg_app_settings_updated_at
        BEFORE UPDATE ON {SCHEMA}.app_settings
        FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.update_updated_at_column();
    """)


def downgrade() -> None:
    # Drop trigger
    op.execute(f"DROP TRIGGER IF EXISTS trg_app_settings_updated_at ON {SCHEMA}.app_settings;")

    # Drop tables
    op.drop_index('idx_settings_history_changed_at', table_name='settings_history', schema=SCHEMA)
    op.drop_index('idx_settings_history_setting_id', table_name='settings_history', schema=SCHEMA)
    op.drop_table('settings_history', schema=SCHEMA)

    op.drop_index('idx_app_settings_active', table_name='app_settings', schema=SCHEMA)
    op.drop_index('idx_app_settings_key', table_name='app_settings', schema=SCHEMA)
    op.drop_index('idx_app_settings_category', table_name='app_settings', schema=SCHEMA)
    op.drop_table('app_settings', schema=SCHEMA)
