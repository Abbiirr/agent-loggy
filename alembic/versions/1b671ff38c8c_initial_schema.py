from alembic import op
import os

# revision identifiers
revision = "1b671ff38c8c"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    here     = os.path.dirname(__file__)
    sql_path = os.path.join(here, "setup_database.sql")
    with open(sql_path, "r", encoding="utf-8") as f:
        ddl = f.read()
    op.execute(ddl)

def downgrade():
    # drop the schema (or individual tables) if you like
    op.execute("DROP SCHEMA IF EXISTS agent_loggy CASCADE;")
