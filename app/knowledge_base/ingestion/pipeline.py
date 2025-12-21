# app/knowledge_base/ingestion/pipeline.py
"""
Ingestion pipeline for populating the knowledge base.

This module orchestrates:
- Service discovery from the codebase
- Code parsing using language-specific parsers
- Embedding generation for all elements
- Database persistence
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.db.session import get_db_session
from app.knowledge_base.models.kb_models import KBService, KBElement, KBIngestionRun
from app.knowledge_base.parsers.java_parser import JavaParser
from app.knowledge_base.parsers.typescript_parser import TypeScriptParser
from app.knowledge_base.parsers.base_parser import ParsedService, ParsedElement
from app.knowledge_base.embedding.embedding_service import get_embedding_service

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    Orchestrates the knowledge base ingestion process.

    Supports:
    - Full ingestion of all services
    - Incremental updates
    - Single service ingestion
    """

    def __init__(self, codebase_path: Optional[str] = None):
        """
        Initialize the ingestion pipeline.

        Args:
            codebase_path: Path to the codebase directory. Defaults to config value.
        """
        self.codebase_path = Path(codebase_path or settings.KB_CODEBASE_PATH)
        if not self.codebase_path.is_absolute():
            # Make it relative to the project root
            self.codebase_path = Path.cwd() / self.codebase_path

        self.embedding_service = get_embedding_service()

    def run_full_ingestion(self) -> Dict[str, Any]:
        """
        Run full ingestion of all services in the codebase.

        Returns:
            Statistics dictionary with counts and errors
        """
        logger.info(f"Starting full ingestion from {self.codebase_path}")

        # Create ingestion run record
        run_id = self._create_run_record('full')

        stats = {
            'services_processed': 0,
            'elements_created': 0,
            'embeddings_generated': 0,
            'errors': [],
        }

        try:
            # Discover services
            service_dirs = self._discover_services()
            logger.info(f"Discovered {len(service_dirs)} services")

            for service_dir in service_dirs:
                try:
                    service_stats = self._ingest_service(service_dir)
                    stats['services_processed'] += 1
                    stats['elements_created'] += service_stats['elements']
                    stats['embeddings_generated'] += service_stats['embeddings']
                    logger.info(f"Ingested {service_dir.name}: {service_stats['elements']} elements")
                except Exception as e:
                    logger.error(f"Error ingesting {service_dir.name}: {e}")
                    stats['errors'].append({
                        'service': service_dir.name,
                        'error': str(e)
                    })

            # Update run record
            self._complete_run_record(run_id, 'completed', stats)

        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            self._complete_run_record(run_id, 'failed', {
                **stats,
                'errors': [{'error': str(e)}]
            })
            raise

        logger.info(f"Ingestion complete: {stats}")
        return stats

    def ingest_single_service(self, service_code: str) -> Dict[str, Any]:
        """
        Ingest a single service by its code.

        Args:
            service_code: The service directory name

        Returns:
            Statistics dictionary
        """
        service_path = self.codebase_path / service_code
        if not service_path.exists():
            raise ValueError(f"Service not found: {service_code}")

        run_id = self._create_run_record('service')

        try:
            stats = self._ingest_service(service_path)
            self._complete_run_record(run_id, 'completed', {
                'services_processed': 1,
                'elements_created': stats['elements'],
                'embeddings_generated': stats['embeddings'],
                'errors': [],
            })
            return stats
        except Exception as e:
            self._complete_run_record(run_id, 'failed', {
                'services_processed': 0,
                'errors': [{'service': service_code, 'error': str(e)}],
            })
            raise

    def _discover_services(self) -> List[Path]:
        """Discover service directories in the codebase."""
        services = []

        if not self.codebase_path.exists():
            logger.warning(f"Codebase path does not exist: {self.codebase_path}")
            return services

        for item in self.codebase_path.iterdir():
            if not item.is_dir() or item.name.startswith('.'):
                continue

            # Check if it's a valid service (has pom.xml, package.json, angular.json, etc.)
            is_java = (item / 'pom.xml').exists() or (item / 'build.gradle').exists()
            is_node = (item / 'package.json').exists()
            is_angular = (item / 'angular.json').exists()

            if is_java or is_node or is_angular:
                services.append(item)

        return sorted(services, key=lambda x: x.name)

    def _ingest_service(self, service_path: Path) -> Dict[str, int]:
        """
        Ingest a single service.

        Args:
            service_path: Path to the service directory

        Returns:
            Statistics dict with 'elements' and 'embeddings' counts
        """
        logger.info(f"Ingesting service: {service_path.name}")

        # Determine parser type
        parser = self._get_parser(service_path)
        if parser is None:
            logger.warning(f"No parser available for {service_path.name}")
            return {'elements': 0, 'embeddings': 0}

        # Parse service
        parsed = parser.parse()
        logger.info(f"Parsed {len(parsed.elements)} elements from {service_path.name}")

        # Store in database
        with get_db_session() as db:
            # Upsert service
            service = self._upsert_service(db, parsed)

            # Deactivate old elements
            db.query(KBElement).filter(
                KBElement.service_id == service.id
            ).update({'is_active': False})

            # Generate and store elements with embeddings
            elements_created = 0
            embeddings_generated = 0

            for element in parsed.elements:
                try:
                    # Generate embedding
                    embedding_text = element.to_embedding_text()
                    embedding_result = self.embedding_service.embed_for_document(embedding_text)
                    embeddings_generated += 1

                    # Create element record
                    kb_element = KBElement(
                        service_id=service.id,
                        element_type=element.element_type,
                        element_name=element.element_name,
                        qualified_name=element.qualified_name,
                        file_path=element.file_path,
                        line_number=element.line_number,
                        signature=element.signature,
                        description=element.description,
                        content_embedding=embedding_result,
                        extra=element.metadata,  # ParsedElement.metadata -> KBElement.extra
                        is_active=True,
                    )
                    db.add(kb_element)
                    elements_created += 1

                except Exception as e:
                    logger.debug(f"Error creating element {element.element_name}: {e}")

            # Generate service-level embedding
            service_summary = self._generate_service_summary(parsed)
            try:
                service_embedding = self.embedding_service.embed_for_document(service_summary)
                service.summary_embedding = service_embedding
                embeddings_generated += 1
            except Exception as e:
                logger.warning(f"Failed to generate service embedding: {e}")

            # Update service counts
            service.api_endpoints_count = len([e for e in parsed.elements if e.element_type == 'endpoint'])
            service.classes_count = len([e for e in parsed.elements if e.element_type in ('class', 'dto', 'component')])
            service.error_codes_count = len([e for e in parsed.elements if e.element_type == 'error_code'])
            service.indexed_at = datetime.utcnow()

            db.commit()

        return {'elements': elements_created, 'embeddings': embeddings_generated}

    def _get_parser(self, service_path: Path):
        """Get the appropriate parser for a service."""
        # Check for Java/Maven
        if (service_path / 'pom.xml').exists() or (service_path / 'build.gradle').exists():
            return JavaParser(service_path)

        # Check for Angular
        if (service_path / 'angular.json').exists():
            return TypeScriptParser(service_path)

        # Check for Node/TypeScript
        if (service_path / 'package.json').exists():
            return TypeScriptParser(service_path)

        return None

    def _upsert_service(self, db: Session, parsed: ParsedService) -> KBService:
        """Create or update a service record."""
        service = db.query(KBService).filter(
            KBService.service_code == parsed.service_code
        ).first()

        if service:
            # Update existing
            service.service_name = parsed.service_name
            service.service_type = parsed.service_type
            service.base_package = parsed.base_package
            service.description = parsed.description
            service.extra = parsed.metadata  # ParsedService.metadata -> KBService.extra
            service.updated_at = datetime.utcnow()
        else:
            # Create new
            service = KBService(
                service_code=parsed.service_code,
                service_name=parsed.service_name,
                service_type=parsed.service_type,
                base_package=parsed.base_package,
                description=parsed.description,
                extra=parsed.metadata,  # ParsedService.metadata -> KBService.extra
            )
            db.add(service)
            db.flush()  # Get the ID

        return service

    def _generate_service_summary(self, parsed: ParsedService) -> str:
        """Generate a summary text for service-level embedding."""
        parts = [
            f"Service: {parsed.service_name}",
            f"Type: {parsed.service_type}",
        ]
        if parsed.description:
            parts.append(f"Description: {parsed.description}")
        if parsed.base_package:
            parts.append(f"Package: {parsed.base_package}")

        # Add element type counts
        element_counts = parsed.get_element_counts()
        if element_counts:
            counts_str = ", ".join(f"{count} {etype}s" for etype, count in element_counts.items())
            parts.append(f"Contains: {counts_str}")

        return " | ".join(parts)

    def _create_run_record(self, run_type: str) -> int:
        """Create an ingestion run record."""
        with get_db_session() as db:
            run = KBIngestionRun(
                run_type=run_type,
                status='running',
            )
            db.add(run)
            db.commit()
            return run.id

    def _complete_run_record(self, run_id: int, status: str, stats: Dict[str, Any]) -> None:
        """Update an ingestion run record with completion status."""
        with get_db_session() as db:
            run = db.query(KBIngestionRun).filter(KBIngestionRun.id == run_id).first()
            if run:
                run.status = status
                run.completed_at = datetime.utcnow()
                run.services_processed = stats.get('services_processed', 0)
                run.elements_created = stats.get('elements_created', 0)
                run.embeddings_generated = stats.get('embeddings_generated', 0)
                run.errors = stats.get('errors', [])
                db.commit()


def run_ingestion(codebase_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to run full ingestion.

    Args:
        codebase_path: Optional path to codebase directory

    Returns:
        Ingestion statistics
    """
    pipeline = IngestionPipeline(codebase_path)
    return pipeline.run_full_ingestion()
