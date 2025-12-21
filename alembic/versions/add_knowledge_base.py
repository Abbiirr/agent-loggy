"""Add knowledge base tables for RAG

Revision ID: add_knowledge_base
Revises: add_context_rules
Create Date: 2025-12-21

This migration creates:
1. pgvector extension for vector similarity search
2. kb_services table for service-level knowledge
3. kb_elements table for element-level knowledge (endpoints, exceptions, etc.)
4. kb_ingestion_runs table for tracking ingestion jobs

PREREQUISITE: pgvector must be installed on the PostgreSQL server.
- For Docker: Use pgvector/pgvector:pg17 image
- For Ubuntu: sudo apt install postgresql-17-pgvector
- For macOS: brew install pgvector
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision = 'add_knowledge_base'
down_revision = 'add_context_rules'
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
    """Create pgvector extension and knowledge base tables."""

    # ─── Enable pgvector extension ───────────────────────────────
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    # ─── kb_services table ───────────────────────────────────────
    op.create_table(
        'kb_services',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('service_code', sa.String(length=100), nullable=False),
        sa.Column('service_name', sa.String(length=255), nullable=False),
        sa.Column('service_type', sa.String(length=50), nullable=False),
        sa.Column('base_package', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        # Vector column will be added via raw SQL below
        sa.Column('api_endpoints_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('classes_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('error_codes_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('metadata', JSONB, nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('indexed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('service_code', name='uq_kb_services_code'),
        schema=SCHEMA
    )

    # Add vector column using raw SQL (pgvector specific syntax)
    op.execute(f"""
        ALTER TABLE {SCHEMA}.kb_services
        ADD COLUMN summary_embedding vector(768);
    """)

    # Indexes for kb_services
    op.create_index('idx_kb_services_code', 'kb_services', ['service_code'], schema=SCHEMA)
    op.create_index('idx_kb_services_type', 'kb_services', ['service_type'], schema=SCHEMA)
    op.create_index('idx_kb_services_active', 'kb_services', ['is_active'], schema=SCHEMA)

    # Vector index for similarity search (IVFFlat)
    op.execute(f"""
        CREATE INDEX idx_kb_services_embedding
        ON {SCHEMA}.kb_services
        USING ivfflat (summary_embedding vector_cosine_ops)
        WITH (lists = 100);
    """)

    # Trigger for updated_at
    op.execute(f"""
        CREATE TRIGGER trg_kb_services_updated_at
        BEFORE UPDATE ON {SCHEMA}.kb_services
        FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.update_updated_at_column();
    """)

    # ─── kb_elements table ───────────────────────────────────────
    op.create_table(
        'kb_elements',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('service_id', sa.Integer(), nullable=False),
        sa.Column('element_type', sa.String(length=50), nullable=False),
        sa.Column('element_name', sa.String(length=255), nullable=False),
        sa.Column('qualified_name', sa.String(length=500), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=True),
        sa.Column('line_number', sa.Integer(), nullable=True),
        sa.Column('signature', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=True),
        sa.Column('metadata', JSONB, nullable=False, server_default='{}'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['service_id'],
            [f'{SCHEMA}.kb_services.id'],
            name='fk_kb_elements_service',
            ondelete='CASCADE'
        ),
        schema=SCHEMA
    )

    # Add vector column for element embedding
    op.execute(f"""
        ALTER TABLE {SCHEMA}.kb_elements
        ADD COLUMN content_embedding vector(768);
    """)

    # Indexes for kb_elements
    op.create_index('idx_kb_elements_service', 'kb_elements', ['service_id'], schema=SCHEMA)
    op.create_index('idx_kb_elements_type', 'kb_elements', ['element_type'], schema=SCHEMA)
    op.create_index('idx_kb_elements_name', 'kb_elements', ['element_name'], schema=SCHEMA)
    op.create_index('idx_kb_elements_qualified', 'kb_elements', ['qualified_name'], schema=SCHEMA)
    op.create_index('idx_kb_elements_active', 'kb_elements', ['is_active'], schema=SCHEMA)
    op.create_index('idx_kb_elements_service_type', 'kb_elements', ['service_id', 'element_type'], schema=SCHEMA)
    op.execute(f"""
        CREATE INDEX idx_kb_elements_metadata
        ON {SCHEMA}.kb_elements
        USING gin(metadata);
    """)

    # Vector index for similarity search
    op.execute(f"""
        CREATE INDEX idx_kb_elements_embedding
        ON {SCHEMA}.kb_elements
        USING ivfflat (content_embedding vector_cosine_ops)
        WITH (lists = 100);
    """)

    # Trigger for updated_at
    op.execute(f"""
        CREATE TRIGGER trg_kb_elements_updated_at
        BEFORE UPDATE ON {SCHEMA}.kb_elements
        FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.update_updated_at_column();
    """)

    # ─── kb_ingestion_runs table ─────────────────────────────────
    op.create_table(
        'kb_ingestion_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('services_processed', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('elements_created', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('elements_updated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('elements_deleted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('embeddings_generated', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('errors', JSONB, nullable=False, server_default='[]'),
        sa.Column('metadata', JSONB, nullable=False, server_default='{}'),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA
    )

    # Indexes for kb_ingestion_runs
    op.create_index('idx_kb_ingestion_runs_status', 'kb_ingestion_runs', ['status'], schema=SCHEMA)
    op.create_index('idx_kb_ingestion_runs_started', 'kb_ingestion_runs', ['started_at'], schema=SCHEMA)


def downgrade() -> None:
    """Drop knowledge base tables."""

    # Drop triggers
    op.execute(f"DROP TRIGGER IF EXISTS trg_kb_elements_updated_at ON {SCHEMA}.kb_elements;")
    op.execute(f"DROP TRIGGER IF EXISTS trg_kb_services_updated_at ON {SCHEMA}.kb_services;")

    # Drop indexes (vector indexes first)
    op.execute(f"DROP INDEX IF EXISTS {SCHEMA}.idx_kb_elements_embedding;")
    op.execute(f"DROP INDEX IF EXISTS {SCHEMA}.idx_kb_elements_metadata;")
    op.execute(f"DROP INDEX IF EXISTS {SCHEMA}.idx_kb_services_embedding;")

    # Drop regular indexes
    op.drop_index('idx_kb_ingestion_runs_started', table_name='kb_ingestion_runs', schema=SCHEMA)
    op.drop_index('idx_kb_ingestion_runs_status', table_name='kb_ingestion_runs', schema=SCHEMA)
    op.drop_index('idx_kb_elements_service_type', table_name='kb_elements', schema=SCHEMA)
    op.drop_index('idx_kb_elements_active', table_name='kb_elements', schema=SCHEMA)
    op.drop_index('idx_kb_elements_qualified', table_name='kb_elements', schema=SCHEMA)
    op.drop_index('idx_kb_elements_name', table_name='kb_elements', schema=SCHEMA)
    op.drop_index('idx_kb_elements_type', table_name='kb_elements', schema=SCHEMA)
    op.drop_index('idx_kb_elements_service', table_name='kb_elements', schema=SCHEMA)
    op.drop_index('idx_kb_services_active', table_name='kb_services', schema=SCHEMA)
    op.drop_index('idx_kb_services_type', table_name='kb_services', schema=SCHEMA)
    op.drop_index('idx_kb_services_code', table_name='kb_services', schema=SCHEMA)

    # Drop tables
    op.drop_table('kb_ingestion_runs', schema=SCHEMA)
    op.drop_table('kb_elements', schema=SCHEMA)
    op.drop_table('kb_services', schema=SCHEMA)

    # Note: We don't drop the pgvector extension as other tables might use it
