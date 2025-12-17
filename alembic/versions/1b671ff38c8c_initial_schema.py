from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = "1b671ff38c8c"
down_revision = None
branch_labels = None
depends_on = None


def get_schema():
    """Get schema from alembic config or default."""
    from alembic import context
    config = context.config
    # Try to get from app config
    try:
        from app.config import settings
        return settings.DATABASE_SCHEMA
    except:
        return "public"


def upgrade():
    """Create base infrastructure - trigger function for updated_at."""
    schema = get_schema()

    # Create the update_updated_at_column function
    op.execute(f"""
        CREATE OR REPLACE FUNCTION "{schema}".update_updated_at_column()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = CURRENT_TIMESTAMP;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)


def downgrade():
    """Drop the trigger function."""
    schema = get_schema()
    op.execute(f'DROP FUNCTION IF EXISTS "{schema}".update_updated_at_column() CASCADE;')
