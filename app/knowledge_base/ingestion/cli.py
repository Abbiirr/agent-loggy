# app/knowledge_base/ingestion/cli.py
"""
CLI commands for knowledge base management.

Usage:
    # Full ingestion
    uv run python -m app.knowledge_base.ingestion.cli ingest

    # Single service
    uv run python -m app.knowledge_base.ingestion.cli ingest --service bs23-ib-rt-payment-service

    # Search
    uv run python -m app.knowledge_base.ingestion.cli search "payment processing"

    # Stats
    uv run python -m app.knowledge_base.ingestion.cli stats
"""

import argparse
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def cmd_ingest(args):
    """Run ingestion."""
    from app.knowledge_base.ingestion.pipeline import IngestionPipeline

    pipeline = IngestionPipeline(codebase_path=args.codebase)

    if args.service:
        print(f"Ingesting single service: {args.service}")
        stats = pipeline.ingest_single_service(args.service)
    else:
        print("Starting full ingestion...")
        stats = pipeline.run_full_ingestion()

    print("\nIngestion complete!")
    print(f"  Services processed: {stats.get('services_processed', 1)}")
    print(f"  Elements created: {stats.get('elements_created', stats.get('elements', 0))}")
    print(f"  Embeddings generated: {stats.get('embeddings_generated', stats.get('embeddings', 0))}")

    if stats.get('errors'):
        print(f"\nErrors ({len(stats['errors'])}):")
        for error in stats['errors'][:5]:  # Show first 5
            print(f"  - {error.get('service', 'unknown')}: {error.get('error', 'unknown error')}")


def cmd_search(args):
    """Search the knowledge base."""
    from app.knowledge_base.retrieval.rag_service import get_rag_service

    rag_service = get_rag_service()

    element_types = [args.type] if args.type else None
    results = rag_service.retrieve(
        query=args.query,
        element_types=element_types,
        top_k=args.limit
    )

    if not results:
        print("No results found.")
        return

    print(f"Found {len(results)} results:\n")
    for i, result in enumerate(results, 1):
        print(f"{i}. [{result.service_name}] {result.element_type}: {result.element_name}")
        print(f"   Similarity: {result.similarity:.3f}")
        if result.signature:
            print(f"   Signature: {result.signature}")
        if result.description:
            desc = result.description[:100] + ('...' if len(result.description) > 100 else '')
            print(f"   Description: {desc}")
        print()


def cmd_stats(args):
    """Show knowledge base statistics."""
    from app.knowledge_base.retrieval.rag_service import get_rag_service

    rag_service = get_rag_service()
    stats = rag_service.get_stats()

    print("Knowledge Base Statistics:")
    print(f"  Services: {stats['services_count']}")
    print(f"  Elements: {stats['elements_count']}")

    if stats['by_element_type']:
        print("\n  By Element Type:")
        for element_type, count in stats['by_element_type'].items():
            print(f"    {element_type}: {count}")

    if stats['last_ingestion']:
        run = stats['last_ingestion']
        print(f"\n  Last Ingestion:")
        print(f"    Type: {run['type']}")
        print(f"    Status: {run['status']}")
        print(f"    Started: {run['started_at']}")
        if run['completed_at']:
            print(f"    Completed: {run['completed_at']}")


def cmd_services(args):
    """List all services in the knowledge base."""
    from sqlalchemy import text
    from app.config import settings
    from app.db.session import get_db_session

    schema = settings.DATABASE_SCHEMA

    with get_db_session() as db:
        result = db.execute(text(f"""
            SELECT service_code, service_name, service_type,
                   api_endpoints_count, classes_count, indexed_at
            FROM {schema}.kb_services
            WHERE is_active = TRUE
            ORDER BY service_code
        """))
        rows = result.fetchall()

    if not rows:
        print("No services indexed.")
        return

    print(f"Indexed Services ({len(rows)}):\n")
    for row in rows:
        print(f"  {row.service_code}")
        print(f"    Name: {row.service_name}")
        print(f"    Type: {row.service_type}")
        print(f"    Endpoints: {row.api_endpoints_count}, Classes: {row.classes_count}")
        if row.indexed_at:
            print(f"    Indexed: {row.indexed_at}")
        print()


def main():
    parser = argparse.ArgumentParser(description='Knowledge Base CLI')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Ingest command
    ingest_parser = subparsers.add_parser('ingest', help='Ingest codebase into knowledge base')
    ingest_parser.add_argument('--codebase', '-c', help='Path to codebase directory')
    ingest_parser.add_argument('--service', '-s', help='Specific service to ingest')
    ingest_parser.set_defaults(func=cmd_ingest)

    # Search command
    search_parser = subparsers.add_parser('search', help='Search the knowledge base')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--limit', '-l', type=int, default=10, help='Number of results')
    search_parser.add_argument('--type', '-t', help='Filter by element type')
    search_parser.set_defaults(func=cmd_search)

    # Stats command
    stats_parser = subparsers.add_parser('stats', help='Show knowledge base statistics')
    stats_parser.set_defaults(func=cmd_stats)

    # Services command
    services_parser = subparsers.add_parser('services', help='List indexed services')
    services_parser.set_defaults(func=cmd_services)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == '__main__':
    main()
