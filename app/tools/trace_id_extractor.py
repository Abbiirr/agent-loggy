# tools/trace_id_extractor.py

import re
from typing import List, Dict, Optional


class TraceIDExtractor:
    """
    Extracts the <request-id> value from an XML-wrapped log entry.

    Usage:
        trace_id = TraceIDExtractor.extract(log_text, position)
    where `log_text` is the full file or snippet, and `position`
    is the character index where a match was found.
    If `position` is None, returns the first trace ID found.
    """

    @classmethod
    def extract(cls, log_text: str, position: int = None) -> str | None:
        """
        Extract trace ID from log content at a specific position.

        Args:
            log_text: Full log content
            position: Character position where match was found (optional)

        Returns:
            Trace ID string or None if not found
        """
        # Type check for input
        if not isinstance(log_text, str):
            raise TypeError("log_text must be a string")

        # Handle empty input
        if not log_text:
            return None

        # Handle negative position by treating as None
        if position is not None and position < 0:
            position = None

        # Find all log-row blocks
        log_rows = cls._find_log_row_blocks(log_text)

        if not log_rows:
            return None

        # If no position specified, extract from first log-row
        if position is None:
            row_content = log_rows[0][2]  # content
            return cls._extract_request_id(row_content)

        # Find the log-row that contains the given position
        for start, end, content in log_rows:
            if start <= position <= end:
                return cls._extract_request_id(content)

        return None

    @classmethod
    def extract_from_matches(cls, matches_with_positions: List[Dict]) -> List[Dict]:
        """
        Extract trace IDs from a list of matches that include position and full content.

        Args:
            matches_with_positions: List of dicts with 'match', 'position', 'full_content'

        Returns:
            List of dicts with original match data plus 'trace_id'
        """
        results = []

        for match_data in matches_with_positions:
            full_content = match_data.get('full_content', '')
            position = match_data.get('position')

            # Extract trace ID
            trace_id = cls.extract(full_content, position)

            # Create result with all original data plus trace_id
            result = match_data.copy()
            result['trace_id'] = trace_id

            # Remove full_content to keep result clean (it's large)
            if 'full_content' in result:
                del result['full_content']

            results.append(result)

        return results

    @classmethod
    def extract_all_from_content(cls, log_content: str) -> List[Dict]:
        """
        Extract all trace IDs from log content.

        Args:
            log_content: Full log file content

        Returns:
            List of dicts with 'trace_id', 'position', 'log_row_content'
        """
        all_trace_ids = []

        # Find all log-row blocks
        log_rows = cls._find_log_row_blocks(log_content)

        for start, end, content in log_rows:
            trace_id = cls._extract_request_id(content)
            if trace_id:
                all_trace_ids.append({
                    'trace_id': trace_id,
                    'position': start,
                    'log_row_content': content[:200],  # First 200 chars of log row
                    'full_log_row': content  # Full log row for detailed analysis
                })

        return all_trace_ids

    @classmethod
    def get_unique_trace_ids(cls, trace_results: List[Dict]) -> List[str]:
        """
        Get list of unique trace IDs from trace results.

        Args:
            trace_results: List of trace result dictionaries

        Returns:
            List of unique trace ID strings
        """
        unique_ids = set()
        for result in trace_results:
            trace_id = result.get('trace_id')
            if trace_id:
                unique_ids.add(trace_id)
        return list(unique_ids)

    @classmethod
    def filter_by_patterns(cls, trace_results: List[Dict], patterns: List[str]) -> List[Dict]:
        """
        Filter trace results to only include those where the associated match contains any of the patterns.

        Args:
            trace_results: List of trace result dictionaries
            patterns: List of patterns to filter by

        Returns:
            Filtered list of trace results
        """
        filtered = []
        for result in trace_results:
            match_content = result.get('match', '')
            if any(pattern.lower() in match_content.lower() for pattern in patterns):
                filtered.append(result)
        return filtered

    @classmethod
    def _find_log_row_blocks(cls, text: str) -> list:
        """Find all log-row blocks using regex approach for better handling."""
        blocks = []

        # Use regex to find all log-row blocks
        # This pattern captures the entire log-row including nested content
        pattern = r'<log-row>(.*?)</log-row>'

        for match in re.finditer(pattern, text, re.DOTALL):
            start_pos = match.start()
            end_pos = match.end()
            full_content = match.group(0)  # Include the log-row tags
            blocks.append((start_pos, end_pos, full_content))

        return blocks

    @classmethod
    def _extract_request_id(cls, content: str) -> str | None:
        """Extract first request-id from content."""
        # Look for request-id pattern, handling whitespace and newlines
        match = re.search(r'<request-id>\s*([^<\s]+)\s*</request-id>', content, re.DOTALL)
        return match.group(1) if match else None