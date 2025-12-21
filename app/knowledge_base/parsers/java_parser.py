# app/knowledge_base/parsers/java_parser.py
"""
Java/Spring Boot parser for knowledge extraction.

Extracts:
- REST endpoints (@GetMapping, @PostMapping, etc.)
- Exception classes and error codes
- DTOs (Request/Response objects)
- Feign clients (inter-service calls)
- Log patterns (logger statements)
"""

import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from xml.etree import ElementTree as ET

from app.knowledge_base.parsers.base_parser import BaseParser, ParsedService, ParsedElement

logger = logging.getLogger(__name__)


class JavaParser(BaseParser):
    """Parser for Java/Spring Boot services."""

    # Regex patterns for Java parsing
    PATTERNS = {
        'package': re.compile(r'package\s+([\w.]+);'),
        'class_decl': re.compile(r'(?:public\s+)?(?:abstract\s+)?(?:class|interface|enum)\s+(\w+)'),
        'rest_controller': re.compile(r'@RestController'),
        'controller': re.compile(r'@Controller'),
        'request_mapping_class': re.compile(r'@RequestMapping\s*\(\s*(?:value\s*=\s*)?["\']([^"\']+)["\']'),
        'http_mapping': re.compile(
            r'@(Get|Post|Put|Delete|Patch)Mapping\s*\(\s*(?:value\s*=\s*)?["\']?([^"\')\s]*)["\']?\s*\)'
        ),
        'feign_client': re.compile(r'@FeignClient\s*\([^)]*name\s*=\s*["\']([^"\']+)["\']'),
        'request_body': re.compile(r'@RequestBody\s+(?:@Valid\s+)?(\w+)'),
        'api_response': re.compile(r'ApiResponse<(\w+)>'),
        'exception_class': re.compile(r'class\s+(\w+(?:Exception|Error))\s+extends'),
        'error_code': re.compile(r'(?:ApiResponseCode|ErrorCode|ResponseMessage)\.(\w+)'),
        'log_statement': re.compile(
            r'(?:log|logger|LOGGER)\.(debug|info|warn|error|trace)\s*\(\s*["\']([^"\']{10,})["\']'
        ),
        'method_signature': re.compile(
            r'(?:public|private|protected)\s+(?:static\s+)?(?:[\w<>?,\s]+)\s+(\w+)\s*\([^)]*\)'
        ),
    }

    def detect_service_type(self) -> str:
        """Detect if this is a Spring Boot service."""
        pom_path = self.service_path / "pom.xml"
        build_gradle = self.service_path / "build.gradle"

        if pom_path.exists():
            content = self._read_file_safe(pom_path)
            if content and 'spring-boot' in content.lower():
                return 'spring-boot'
            return 'java'

        if build_gradle.exists():
            content = self._read_file_safe(build_gradle)
            if content and 'spring' in content.lower():
                return 'spring-boot'
            return 'java'

        return 'java'

    def parse(self) -> ParsedService:
        """Parse the Java service."""
        logger.info(f"Parsing Java service: {self.service_code}")

        service_type = self.detect_service_type()
        elements = self.extract_elements()
        relationships = self._extract_relationships(elements)
        base_package = self._detect_base_package()

        # Generate description
        element_counts = {}
        for elem in elements:
            element_counts[elem.element_type] = element_counts.get(elem.element_type, 0) + 1

        description = f"{service_type.title()} service"
        if element_counts:
            parts = [f"{count} {etype}s" for etype, count in element_counts.items()]
            description += f" with {', '.join(parts)}"

        return ParsedService(
            service_code=self.service_code,
            service_name=self._humanize_service_name(self.service_code),
            service_type=service_type,
            base_package=base_package,
            description=description,
            elements=elements,
            relationships=relationships,
            metadata={
                'java_version': self._detect_java_version(),
                'spring_boot_version': self._detect_spring_boot_version(),
            }
        )

    def extract_elements(self) -> List[ParsedElement]:
        """Extract all elements from Java source files."""
        elements = []
        java_files = self._find_files("*.java")

        logger.info(f"Found {len(java_files)} Java files in {self.service_code}")

        for java_file in java_files:
            try:
                content = self._read_file_safe(java_file)
                if content:
                    file_elements = self._parse_java_file(java_file, content)
                    elements.extend(file_elements)
            except Exception as e:
                logger.debug(f"Error parsing {java_file}: {e}")

        logger.info(f"Extracted {len(elements)} elements from {self.service_code}")
        return elements

    def _parse_java_file(self, file_path: Path, content: str) -> List[ParsedElement]:
        """Parse a single Java file and extract elements."""
        elements = []
        relative_path = str(file_path.relative_to(self.service_path))

        # Extract package
        package_match = self.PATTERNS['package'].search(content)
        package = package_match.group(1) if package_match else ''

        # Extract class name
        class_match = self.PATTERNS['class_decl'].search(content)
        class_name = class_match.group(1) if class_match else 'Unknown'

        # Check if this is a controller
        is_controller = bool(
            self.PATTERNS['rest_controller'].search(content) or
            self.PATTERNS['controller'].search(content)
        )

        if is_controller:
            elements.extend(self._extract_endpoints(content, package, class_name, relative_path))

        # Check if this is a Feign client
        feign_match = self.PATTERNS['feign_client'].search(content)
        if feign_match:
            elements.extend(self._extract_feign_client(content, package, class_name, relative_path, feign_match))

        # Check if this is an exception class
        exception_match = self.PATTERNS['exception_class'].search(content)
        if exception_match:
            elements.append(self._extract_exception(content, package, exception_match.group(1), relative_path))

        # Extract DTOs (classes ending in Request, Response, Dto)
        if any(suffix in class_name for suffix in ['Request', 'Response', 'Dto', 'DTO']):
            elements.append(self._extract_dto(content, package, class_name, relative_path))

        # Extract log patterns
        elements.extend(self._extract_log_patterns(content, package, class_name, relative_path))

        # Extract error codes
        elements.extend(self._extract_error_codes(content, package, class_name, relative_path))

        return elements

    def _extract_endpoints(
        self, content: str, package: str, class_name: str, file_path: str
    ) -> List[ParsedElement]:
        """Extract REST endpoints from a controller."""
        elements = []
        lines = content.split('\n')

        # Get class-level mapping
        class_mapping = ""
        class_mapping_match = self.PATTERNS['request_mapping_class'].search(content)
        if class_mapping_match:
            class_mapping = class_mapping_match.group(1)

        # Find all HTTP method mappings
        for match in self.PATTERNS['http_mapping'].finditer(content):
            http_method = match.group(1).upper()
            path = match.group(2) or ''
            full_path = f"{class_mapping}{path}".replace('//', '/')

            # Find line number
            line_num = content[:match.start()].count('\n') + 1

            # Try to find method name (look for next method signature after the annotation)
            after_annotation = content[match.end():match.end() + 500]
            method_match = self.PATTERNS['method_signature'].search(after_annotation)
            method_name = method_match.group(1) if method_match else 'unknown'

            # Try to find request body type
            request_type = None
            if method_match:
                method_content = after_annotation[:method_match.end() + 100]
                request_body_match = self.PATTERNS['request_body'].search(method_content)
                if request_body_match:
                    request_type = request_body_match.group(1)

            # Try to find response type
            response_type = None
            response_match = self.PATTERNS['api_response'].search(after_annotation[:200])
            if response_match:
                response_type = response_match.group(1)

            elements.append(ParsedElement(
                element_type='endpoint',
                element_name=method_name,
                qualified_name=f"{package}.{class_name}.{method_name}",
                file_path=file_path,
                line_number=line_num,
                signature=f"{http_method} {full_path}",
                description=f"REST endpoint {http_method} {full_path} in {class_name}",
                metadata={
                    'http_method': http_method,
                    'path': full_path,
                    'controller': class_name,
                    'request_dto': request_type,
                    'response_dto': response_type,
                }
            ))

        return elements

    def _extract_feign_client(
        self, content: str, package: str, class_name: str, file_path: str, feign_match
    ) -> List[ParsedElement]:
        """Extract Feign client information."""
        elements = []
        target_service = feign_match.group(1)

        # Find all methods in the Feign client
        for method_match in self.PATTERNS['method_signature'].finditer(content):
            method_name = method_match.group(1)
            line_num = content[:method_match.start()].count('\n') + 1

            # Check if there's an HTTP mapping before this method
            before_method = content[max(0, method_match.start() - 200):method_match.start()]
            http_match = self.PATTERNS['http_mapping'].search(before_method)

            http_method = http_match.group(1).upper() if http_match else 'UNKNOWN'
            path = http_match.group(2) if http_match else ''

            elements.append(ParsedElement(
                element_type='service_call',
                element_name=method_name,
                qualified_name=f"{package}.{class_name}.{method_name}",
                file_path=file_path,
                line_number=line_num,
                signature=f"Feign: {http_method} -> {target_service}",
                description=f"Feign client call to {target_service} service",
                metadata={
                    'target_service': target_service,
                    'feign_client': class_name,
                    'method': method_name,
                    'http_method': http_method,
                    'path': path,
                }
            ))

        return elements

    def _extract_exception(
        self, content: str, package: str, class_name: str, file_path: str
    ) -> ParsedElement:
        """Extract exception class information."""
        # Try to find error code or message
        error_code = None
        error_codes = self.PATTERNS['error_code'].findall(content)
        if error_codes:
            error_code = error_codes[0]

        return ParsedElement(
            element_type='exception',
            element_name=class_name,
            qualified_name=f"{package}.{class_name}",
            file_path=file_path,
            line_number=1,
            description=f"Exception class {class_name}",
            metadata={
                'error_code': error_code,
                'package': package,
            }
        )

    def _extract_dto(
        self, content: str, package: str, class_name: str, file_path: str
    ) -> ParsedElement:
        """Extract DTO class information."""
        # Determine DTO type
        dto_type = 'dto'
        if 'Request' in class_name:
            dto_type = 'request_dto'
        elif 'Response' in class_name:
            dto_type = 'response_dto'

        # Try to extract field names
        field_pattern = re.compile(r'private\s+[\w<>?,\s]+\s+(\w+)\s*[;=]')
        fields = field_pattern.findall(content)

        return ParsedElement(
            element_type='dto',
            element_name=class_name,
            qualified_name=f"{package}.{class_name}",
            file_path=file_path,
            line_number=1,
            description=f"Data Transfer Object {class_name}",
            metadata={
                'dto_type': dto_type,
                'fields': fields[:20],  # Limit to first 20 fields
            }
        )

    def _extract_log_patterns(
        self, content: str, package: str, class_name: str, file_path: str
    ) -> List[ParsedElement]:
        """Extract logging statement patterns."""
        elements = []

        for match in self.PATTERNS['log_statement'].finditer(content):
            log_level = match.group(1).upper()
            log_message = match.group(2)
            line_num = content[:match.start()].count('\n') + 1

            # Extract placeholders from log message
            placeholders = re.findall(r'\{(\w*)\}', log_message)

            elements.append(ParsedElement(
                element_type='log_pattern',
                element_name=log_message[:50] + ('...' if len(log_message) > 50 else ''),
                qualified_name=f"{package}.{class_name}",
                file_path=file_path,
                line_number=line_num,
                description=f"Log statement: {log_message[:100]}",
                metadata={
                    'log_level': log_level,
                    'pattern': log_message,
                    'placeholders': placeholders,
                    'class': class_name,
                }
            ))

        return elements

    def _extract_error_codes(
        self, content: str, package: str, class_name: str, file_path: str
    ) -> List[ParsedElement]:
        """Extract error code references."""
        elements = []
        seen_codes = set()

        for match in self.PATTERNS['error_code'].finditer(content):
            error_code = match.group(1)
            if error_code in seen_codes:
                continue
            seen_codes.add(error_code)

            line_num = content[:match.start()].count('\n') + 1

            elements.append(ParsedElement(
                element_type='error_code',
                element_name=error_code,
                qualified_name=f"{package}.{class_name}",
                file_path=file_path,
                line_number=line_num,
                description=f"Error code {error_code} used in {class_name}",
                metadata={
                    'code': error_code,
                    'class': class_name,
                }
            ))

        return elements

    def _extract_relationships(self, elements: List[ParsedElement]) -> List[Dict[str, Any]]:
        """Extract inter-service relationships from parsed elements."""
        relationships = []
        seen = set()

        for element in elements:
            if element.element_type == 'service_call':
                target = element.metadata.get('target_service')
                if target and target not in seen:
                    seen.add(target)
                    relationships.append({
                        'target_service': target,
                        'relationship_type': 'feign_call',
                        'source_class': element.metadata.get('feign_client'),
                    })

        return relationships

    def _detect_base_package(self) -> Optional[str]:
        """Detect the base package from Java source files."""
        java_files = self._find_files("*.java")
        packages = []

        for java_file in java_files[:10]:  # Check first 10 files
            content = self._read_file_safe(java_file)
            if content:
                match = self.PATTERNS['package'].search(content)
                if match:
                    packages.append(match.group(1))

        if not packages:
            return None

        # Find common prefix
        if len(packages) == 1:
            return packages[0]

        # Find the shortest common package prefix
        packages.sort(key=len)
        base = packages[0]
        for pkg in packages[1:]:
            while not pkg.startswith(base) and '.' in base:
                base = base.rsplit('.', 1)[0]

        return base if base else None

    def _detect_java_version(self) -> Optional[str]:
        """Detect Java version from pom.xml."""
        pom_path = self.service_path / "pom.xml"
        if not pom_path.exists():
            return None

        try:
            tree = ET.parse(pom_path)
            root = tree.getroot()
            ns = {'m': 'http://maven.apache.org/POM/4.0.0'}

            # Try properties first
            props = root.find('.//m:properties', ns)
            if props is not None:
                java_version = props.find('m:java.version', ns)
                if java_version is not None:
                    return java_version.text

            return None
        except Exception:
            return None

    def _detect_spring_boot_version(self) -> Optional[str]:
        """Detect Spring Boot version from pom.xml."""
        pom_path = self.service_path / "pom.xml"
        if not pom_path.exists():
            return None

        try:
            tree = ET.parse(pom_path)
            root = tree.getroot()
            ns = {'m': 'http://maven.apache.org/POM/4.0.0'}

            # Check parent version
            parent = root.find('m:parent', ns)
            if parent is not None:
                artifact = parent.find('m:artifactId', ns)
                if artifact is not None and 'spring-boot' in artifact.text:
                    version = parent.find('m:version', ns)
                    if version is not None:
                        return version.text

            return None
        except Exception:
            return None
