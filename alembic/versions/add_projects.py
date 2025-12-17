"""Add projects, project_settings, and environments tables

Revision ID: add_projects
Revises: add_app_settings
Create Date: 2025-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_projects'
down_revision = 'add_app_settings'
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
    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_code', sa.String(length=50), nullable=False),
        sa.Column('project_name', sa.String(length=255), nullable=False),
        sa.Column('log_source_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_code', name='uq_project_code'),
        schema=SCHEMA
    )

    # Create indexes for projects
    op.create_index('idx_projects_code', 'projects', ['project_code'], schema=SCHEMA)
    op.create_index('idx_projects_active', 'projects', ['is_active'], schema=SCHEMA)

    # Create project_settings table
    op.create_table(
        'project_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('setting_key', sa.String(length=255), nullable=False),
        sa.Column('setting_value', sa.Text(), nullable=False),
        sa.Column('value_type', sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], [f'{SCHEMA}.projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'setting_key', name='uq_project_setting'),
        schema=SCHEMA
    )

    # Create indexes for project_settings
    op.create_index('idx_project_settings_project', 'project_settings', ['project_id'], schema=SCHEMA)

    # Create environments table
    op.create_table(
        'environments',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('env_code', sa.String(length=50), nullable=False),
        sa.Column('env_name', sa.String(length=100), nullable=True),
        sa.Column('loki_namespace', sa.String(length=100), nullable=True),
        sa.Column('log_base_path', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['project_id'], [f'{SCHEMA}.projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'env_code', name='uq_project_env'),
        schema=SCHEMA
    )

    # Create indexes for environments
    op.create_index('idx_environments_project', 'environments', ['project_id'], schema=SCHEMA)
    op.create_index('idx_environments_active', 'environments', ['is_active'], schema=SCHEMA)

    # Create trigger for projects updated_at
    op.execute(f"""
        CREATE TRIGGER trg_projects_updated_at
        BEFORE UPDATE ON {SCHEMA}.projects
        FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.update_updated_at_column();
    """)


def downgrade() -> None:
    # Drop trigger
    op.execute(f"DROP TRIGGER IF EXISTS trg_projects_updated_at ON {SCHEMA}.projects;")

    # Drop environments table
    op.drop_index('idx_environments_active', table_name='environments', schema=SCHEMA)
    op.drop_index('idx_environments_project', table_name='environments', schema=SCHEMA)
    op.drop_table('environments', schema=SCHEMA)

    # Drop project_settings table
    op.drop_index('idx_project_settings_project', table_name='project_settings', schema=SCHEMA)
    op.drop_table('project_settings', schema=SCHEMA)

    # Drop projects table
    op.drop_index('idx_projects_active', table_name='projects', schema=SCHEMA)
    op.drop_index('idx_projects_code', table_name='projects', schema=SCHEMA)
    op.drop_table('projects', schema=SCHEMA)
