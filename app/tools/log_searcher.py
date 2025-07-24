# tools/log_searcher.py

import re
import lzma
import gzip
import zipfile
from pathlib import Path
from typing import List, Union, Pattern, Dict


class LogSearcher:
    """
    Open a log file (compressed or not), search for patterns, and extract matching lines.

    Supported formats:
      - .xz  (LZMA)
      - .gz  (Gzip)
      - .zip (Zip archive; searches every .log inside)
      - plain text
    """

    def __init__(self, context: int = 0):
        """
        Args:
            context: number of lines of context to include before/after a match
        """
        self.context = context

    def _open(self, path: Path):
        """Open file in text mode, wrapping decompression if needed."""
        suffix = path.suffix.lower()
        if suffix == ".xz":
            return lzma.open(path, "rt", errors="ignore")
        elif suffix == ".gz":
            return gzip.open(path, "rt", errors="ignore")
        elif suffix == ".zip":
            # stream all .log files in the archive
            zf = zipfile.ZipFile(path)

            def gen_lines():
                for info in zf.infolist():
                    if info.filename.lower().endswith(".log"):
                        with zf.open(info, "r") as f:
                            for raw in f:
                                yield raw.decode(errors="ignore")

            return gen_lines()
        else:
            # fallback to plain text
            return open(path, "rt", errors="ignore")

    def read_full_content(self, path: Union[str, Path]) -> str:
        """
        Read the full content of a log file, handling compression.

        Args:
            path: filesystem path to the log file

        Returns:
            Full content of the log file as a string
        """
        path = Path(path)
        try:
            suffix = path.suffix.lower()
            if suffix == ".xz":
                with lzma.open(path, 'rt', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            elif suffix == ".gz":
                with gzip.open(path, 'rt', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            elif suffix == ".zip":
                # For zip files, concatenate all .log files
                content = ""
                with zipfile.ZipFile(path) as zf:
                    for info in zf.infolist():
                        if info.filename.lower().endswith(".log"):
                            with zf.open(info, "r") as f:
                                content += f.read().decode(errors="ignore")
                return content
            else:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
        except Exception as e:
            raise Exception(f"Error reading log file {path}: {e}")

    def search(
            self,
            path: Union[str, Path],
            patterns: List[Union[str, Pattern]],
    ) -> List[str]:
        """
        Search the given file for any of the provided patterns.

        Args:
            path: filesystem path to the log file.
            patterns: list of string regexes or compiled Pattern objects.

        Returns:
            A list of matched lines (including context lines if self.context > 0).
        """
        path = Path(path)
        # compile string patterns
        regexes = [
            p if isinstance(p, re.Pattern) else re.compile(p, re.IGNORECASE)
            for p in patterns
        ]

        # open and set up iterator
        source = self._open(path)
        if hasattr(source, "readline"):
            iterator = source
        else:
            # generator of lines
            iterator = source

        window = []
        results = []
        for idx, line in enumerate(iterator):
            text = line.rstrip("\n\r")
            window.append(text)
            if len(window) > self.context + 1:
                window.pop(0)

            for rx in regexes:
                if rx.search(text):
                    # include context if requested
                    if self.context:
                        results.extend(window)
                    else:
                        results.append(text)
                    break

        # close file if needed
        if hasattr(source, "close"):
            source.close()
        return results

    def search_with_trace_ids(
            self,
            path: Union[str, Path],
            patterns: List[Union[str, Pattern]],
    ) -> List[Dict]:
        """
        Search and automatically extract trace IDs for each match.

        Args:
            path: filesystem path to the log file
            patterns: list of string regexes or compiled Pattern objects

        Returns:
            List of dictionaries with 'match', 'trace_id', 'line_number'
        """
        from app.tools.trace_id_extractor import TraceIDExtractor

        path = Path(path)

        # Read full content first
        full_content = self.read_full_content(path)

        # Compile patterns
        regexes = [
            p if isinstance(p, re.Pattern) else re.compile(p, re.IGNORECASE)
            for p in patterns
        ]

        # Split content into lines while tracking positions
        lines = full_content.split('\n')
        results = []
        current_position = 0

        for line_num, line in enumerate(lines, 1):
            # Check if this line matches any pattern
            for rx in regexes:
                if rx.search(line):
                    # Extract trace ID for this match
                    trace_id = TraceIDExtractor.extract(full_content, current_position)

                    results.append({
                        'match': line,
                        'trace_id': trace_id,
                        'line_number': line_num,
                        'position': current_position
                    })
                    break

            # Update position for next line (+1 for the \n character)
            current_position += len(line) + 1

        return results

    def search_detailed(
            self,
            path: Union[str, Path],
            patterns: List[Union[str, Pattern]],
    ) -> Dict:
        """
        Comprehensive search that returns matches with trace IDs.

        Args:
            path: filesystem path to the log file
            patterns: list of string regexes or compiled Pattern objects

        Returns:
            Dictionary with 'matches', 'trace_results', 'patterns_used', 'file_info'
        """
        path = Path(path)

        # Get basic matches
        matches = self.search(path, patterns)

        # Get matches with trace IDs
        trace_results = self.search_with_trace_ids(path, patterns)

        # File info
        file_info = {
            'path': str(path),
            'size': path.stat().st_size,
            'total_lines': len(matches) if matches else 0
        }

        return {
            'matches': matches,
            'trace_results': trace_results,
            'patterns_used': patterns,
            'file_info': file_info,
            'total_matches': len(matches)
        }