# app/knowledge_base/parsers/typescript_parser.py
"""
TypeScript/Angular parser for knowledge extraction.

Extracts:
- Angular components
- Services with HTTP calls
- API endpoints called from frontend
"""

import re
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from app.knowledge_base.parsers.base_parser import BaseParser, ParsedService, ParsedElement

logger = logging.getLogger(__name__)


class TypeScriptParser(BaseParser):
    """Parser for TypeScript/Angular projects."""

    # Regex patterns for TypeScript parsing
    PATTERNS = {
        'component': re.compile(r"@Component\s*\(\s*\{[^}]*selector:\s*['\"]([^'\"]+)['\"]", re.DOTALL),
        'injectable': re.compile(r"@Injectable\s*\([^)]*\)\s*export\s+class\s+(\w+)"),
        'http_call': re.compile(
            r"this\.http\.(get|post|put|delete|patch)\s*(?:<[^>]+>)?\s*\(\s*[`'\"]([^`'\"]+)[`'\"]"
        ),
        'class_decl': re.compile(r"export\s+(?:abstract\s+)?class\s+(\w+)"),
        'interface_decl': re.compile(r"export\s+interface\s+(\w+)"),
        'import_statement': re.compile(r"import\s+\{([^}]+)\}\s+from\s+['\"]([^'\"]+)['\"]"),
        'api_endpoint': re.compile(r"['\"`]\/api\/[^'\"`]+['\"`]"),
        'environment_var': re.compile(r"environment\.(\w+)"),
    }

    def detect_service_type(self) -> str:
        """Detect if this is an Angular project."""
        angular_json = self.service_path / "angular.json"
        package_json = self.service_path / "package.json"

        if angular_json.exists():
            return 'angular'

        if package_json.exists():
            content = self._read_file_safe(package_json)
            if content:
                try:
                    pkg = json.loads(content)
                    deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                    if '@angular/core' in deps:
                        return 'angular'
                    if 'react' in deps:
                        return 'react'
                    if 'vue' in deps:
                        return 'vue'
                except json.JSONDecodeError:
                    pass

        return 'typescript'

    def parse(self) -> ParsedService:
        """Parse the TypeScript/Angular project."""
        logger.info(f"Parsing TypeScript project: {self.service_code}")

        service_type = self.detect_service_type()
        elements = self.extract_elements()

        # Generate description
        element_counts = {}
        for elem in elements:
            element_counts[elem.element_type] = element_counts.get(elem.element_type, 0) + 1

        description = f"{service_type.title()} application"
        if element_counts:
            parts = [f"{count} {etype}s" for etype, count in element_counts.items()]
            description += f" with {', '.join(parts)}"

        return ParsedService(
            service_code=self.service_code,
            service_name=self._humanize_service_name(self.service_code),
            service_type=service_type,
            description=description,
            elements=elements,
            metadata={
                'angular_version': self._detect_angular_version(),
            }
        )

    def extract_elements(self) -> List[ParsedElement]:
        """Extract all elements from TypeScript files."""
        elements = []
        ts_files = self._find_files("*.ts")

        logger.info(f"Found {len(ts_files)} TypeScript files in {self.service_code}")

        for ts_file in ts_files:
            try:
                content = self._read_file_safe(ts_file)
                if content:
                    file_elements = self._parse_ts_file(ts_file, content)
                    elements.extend(file_elements)
            except Exception as e:
                logger.debug(f"Error parsing {ts_file}: {e}")

        logger.info(f"Extracted {len(elements)} elements from {self.service_code}")
        return elements

    def _parse_ts_file(self, file_path: Path, content: str) -> List[ParsedElement]:
        """Parse a single TypeScript file and extract elements."""
        elements = []
        relative_path = str(file_path.relative_to(self.service_path))

        # Extract components
        for match in self.PATTERNS['component'].finditer(content):
            selector = match.group(1)
            line_num = content[:match.start()].count('\n') + 1

            # Try to find the class name
            class_match = self.PATTERNS['class_decl'].search(content[match.end():match.end() + 500])
            class_name = class_match.group(1) if class_match else selector

            elements.append(ParsedElement(
                element_type='component',
                element_name=class_name,
                qualified_name=f"{relative_path}:{class_name}",
                file_path=relative_path,
                line_number=line_num,
                signature=f"<{selector}>",
                description=f"Angular component with selector '{selector}'",
                metadata={
                    'selector': selector,
                    'framework': 'angular',
                }
            ))

        # Extract injectable services
        for match in self.PATTERNS['injectable'].finditer(content):
            service_name = match.group(1)
            line_num = content[:match.start()].count('\n') + 1

            elements.append(ParsedElement(
                element_type='service',
                element_name=service_name,
                qualified_name=f"{relative_path}:{service_name}",
                file_path=relative_path,
                line_number=line_num,
                description=f"Injectable service {service_name}",
                metadata={
                    'framework': 'angular',
                }
            ))

        # Extract HTTP calls (API endpoints called from frontend)
        for match in self.PATTERNS['http_call'].finditer(content):
            http_method = match.group(1).upper()
            url = match.group(2)
            line_num = content[:match.start()].count('\n') + 1

            # Skip template literals with complex expressions
            if '${' in url:
                continue

            elements.append(ParsedElement(
                element_type='http_call',
                element_name=f"{http_method} {url}",
                qualified_name=f"{relative_path}",
                file_path=relative_path,
                line_number=line_num,
                signature=f"{http_method} {url}",
                description=f"HTTP call to backend: {http_method} {url}",
                metadata={
                    'http_method': http_method,
                    'url': url,
                }
            ))

        # Extract interfaces (potential DTOs)
        for match in self.PATTERNS['interface_decl'].finditer(content):
            interface_name = match.group(1)
            line_num = content[:match.start()].count('\n') + 1

            # Only include if it looks like a DTO
            if any(suffix in interface_name for suffix in ['Request', 'Response', 'Model', 'Dto', 'DTO']):
                elements.append(ParsedElement(
                    element_type='interface',
                    element_name=interface_name,
                    qualified_name=f"{relative_path}:{interface_name}",
                    file_path=relative_path,
                    line_number=line_num,
                    description=f"TypeScript interface {interface_name}",
                    metadata={
                        'type': 'dto' if 'Request' in interface_name or 'Response' in interface_name else 'model',
                    }
                ))

        return elements

    def _detect_angular_version(self) -> Optional[str]:
        """Detect Angular version from package.json."""
        package_json = self.service_path / "package.json"
        if not package_json.exists():
            return None

        try:
            content = self._read_file_safe(package_json)
            if content:
                pkg = json.loads(content)
                deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                return deps.get('@angular/core', '').lstrip('^~')
        except (json.JSONDecodeError, Exception):
            pass

        return None
