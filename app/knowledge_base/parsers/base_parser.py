# app/knowledge_base/parsers/base_parser.py
"""
Base parser class for code parsing.

Defines the interface that all language-specific parsers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional
import re


@dataclass
class ParsedElement:
    """Represents a parsed code element (endpoint, class, method, etc.)."""

    element_type: str  # 'endpoint', 'exception', 'dto', 'service_call', 'log_pattern', etc.
    element_name: str  # Name of the element
    qualified_name: Optional[str] = None  # Full qualified name
    file_path: Optional[str] = None  # Relative path to source file
    line_number: Optional[int] = None  # Line number in source
    signature: Optional[str] = None  # Method/class signature
    description: Optional[str] = None  # Extracted or generated description
    metadata: Dict[str, Any] = field(default_factory=dict)  # Type-specific metadata

    def to_embedding_text(self) -> str:
        """Generate text representation for embedding."""
        parts = [
            f"Type: {self.element_type}",
            f"Name: {self.element_name}",
        ]
        if self.signature:
            parts.append(f"Signature: {self.signature}")
        if self.description:
            parts.append(f"Description: {self.description}")
        if self.metadata:
            # Include key metadata fields
            for key in ['path', 'http_method', 'error_code', 'target_service', 'log_level']:
                if key in self.metadata:
                    parts.append(f"{key}: {self.metadata[key]}")
        return " | ".join(parts)


@dataclass
class ParsedService:
    """Represents a parsed service/project."""

    service_code: str  # Directory name / service identifier
    service_name: str  # Human-readable name
    service_type: str  # 'spring-boot', 'angular', 'java', 'typescript'
    base_package: Optional[str] = None  # Base package (for Java)
    description: Optional[str] = None  # Generated service description
    elements: List[ParsedElement] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)  # Inter-service dependencies
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_elements_by_type(self, element_type: str) -> List[ParsedElement]:
        """Get all elements of a specific type."""
        return [e for e in self.elements if e.element_type == element_type]

    def get_element_counts(self) -> Dict[str, int]:
        """Get count of elements by type."""
        counts: Dict[str, int] = {}
        for element in self.elements:
            counts[element.element_type] = counts.get(element.element_type, 0) + 1
        return counts


class BaseParser(ABC):
    """
    Abstract base class for code parsers.

    Each parser implementation handles a specific language/framework.
    """

    def __init__(self, service_path: Path):
        """
        Initialize parser with service path.

        Args:
            service_path: Path to the service/project directory
        """
        self.service_path = service_path
        self.service_code = service_path.name

    @abstractmethod
    def detect_service_type(self) -> str:
        """
        Detect the type of service (spring-boot, angular, etc.).

        Returns:
            Service type string
        """
        pass

    @abstractmethod
    def parse(self) -> ParsedService:
        """
        Parse the service and return structured data.

        Returns:
            ParsedService with all extracted elements
        """
        pass

    @abstractmethod
    def extract_elements(self) -> List[ParsedElement]:
        """
        Extract all code elements from the service.

        Returns:
            List of ParsedElement objects
        """
        pass

    def _humanize_service_name(self, service_code: str) -> str:
        """
        Convert service code to human-readable name.

        Examples:
            'bs23-ib-rt-payment-service' -> 'Payment Service'
            'ab-customer-web-portal' -> 'Customer Web Portal'
        """
        # Remove common prefixes
        name = service_code
        for prefix in ['bs23-ib-rt-', 'bs23-ib-', 'bs-ib-', 'bs-', 'ab-', 'ncc-ib-']:
            if name.startswith(prefix):
                name = name[len(prefix):]
                break

        # Remove common suffixes
        for suffix in ['-service', '-web', '-portal']:
            if name.endswith(suffix):
                name = name[:-len(suffix)]
                break

        # Convert to title case
        words = name.replace('-', ' ').replace('_', ' ').split()
        return ' '.join(word.capitalize() for word in words)

    def _find_files(self, pattern: str, exclude_dirs: Optional[List[str]] = None) -> List[Path]:
        """
        Find all files matching a pattern in the service directory.

        Args:
            pattern: Glob pattern (e.g., "*.java", "**/*.ts")
            exclude_dirs: List of directory names to exclude

        Returns:
            List of matching file paths
        """
        exclude_dirs = exclude_dirs or ['node_modules', 'target', 'build', '.git', 'dist', '__pycache__']
        files = []

        for file_path in self.service_path.rglob(pattern):
            # Check if any parent directory should be excluded
            should_exclude = False
            for part in file_path.parts:
                if part in exclude_dirs:
                    should_exclude = True
                    break

            if not should_exclude:
                files.append(file_path)

        return files

    def _read_file_safe(self, file_path: Path, encoding: str = 'utf-8') -> Optional[str]:
        """
        Safely read a file, returning None on error.

        Args:
            file_path: Path to file
            encoding: File encoding

        Returns:
            File contents or None if error
        """
        try:
            return file_path.read_text(encoding=encoding)
        except Exception:
            try:
                # Fallback to latin-1 which can read any byte sequence
                return file_path.read_text(encoding='latin-1')
            except Exception:
                return None
