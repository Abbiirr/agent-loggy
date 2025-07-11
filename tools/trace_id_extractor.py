import re


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