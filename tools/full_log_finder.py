# tools/full_log_finder.py

import re
from pathlib import Path
from typing import List, Dict, Union, Optional
from tools.log_searcher import LogSearcher
from tools.trace_id_extractor import TraceIDExtractor


class FullLogFinder:
    """
    Find all log entries that contain a specific trace ID (request-id).
    """

    def __init__(self):
        self.log_searcher = LogSearcher(context=0)  # No context needed for trace searches

    def find_all_logs_for_trace(
            self,
            log_file_path: Union[str, Path],
            trace_id: str
    ) -> Dict:
        """
        Find all log entries that contain the specified trace ID.

        Args:
            log_file_path: Path to the log file
            trace_id: The trace ID (request-id) to search for

        Returns:
            Dictionary with trace_id, total_entries, log_entries, and timeline
        """
        log_file_path = Path(log_file_path)

        # Read full content
        full_content = self.log_searcher.read_full_content(log_file_path)

        # Find all log-row blocks that contain this trace ID
        matching_log_rows = self._find_log_rows_with_trace_id(full_content, trace_id)

        # Parse each log row into structured data
        parsed_entries = []
        for log_row_content in matching_log_rows:
            parsed_entry = self._parse_log_row(log_row_content)
            if parsed_entry:
                parsed_entries.append(parsed_entry)

        # Sort by timestamp
        parsed_entries.sort(key=lambda x: x.get('timestamp', ''))

        # Create timeline
        timeline = self._create_timeline(parsed_entries)

        return {
            'trace_id': trace_id,
            'log_file': str(log_file_path),
            'total_entries': len(parsed_entries),
            'log_entries': parsed_entries,
            'timeline': timeline,
            'first_entry': parsed_entries[0] if parsed_entries else None,
            'last_entry': parsed_entries[-1] if parsed_entries else None
        }

    def find_traces_for_multiple_ids(
            self,
            log_file_path: Union[str, Path],
            trace_ids: List[str]
    ) -> Dict:
        """
        Find all log entries for multiple trace IDs.

        Args:
            log_file_path: Path to the log file
            trace_ids: List of trace IDs to search for

        Returns:
            Dictionary with results for each trace ID
        """
        results = {}

        for trace_id in trace_ids:
            results[trace_id] = self.find_all_logs_for_trace(log_file_path, trace_id)

        # Add summary
        summary = {
            'total_trace_ids': len(trace_ids),
            'trace_ids_found': len([r for r in results.values() if r['total_entries'] > 0]),
            'total_log_entries': sum(r['total_entries'] for r in results.values())
        }

        return {
            'summary': summary,
            'traces': results
        }

    def get_trace_flow(
            self,
            log_file_path: Union[str, Path],
            trace_id: str
    ) -> List[Dict]:
        """
        Get the flow/sequence of operations for a specific trace ID.

        Args:
            log_file_path: Path to the log file
            trace_id: The trace ID to trace

        Returns:
            List of operation steps in chronological order
        """
        trace_result = self.find_all_logs_for_trace(log_file_path, trace_id)
        log_entries = trace_result['log_entries']

        flow = []
        for i, entry in enumerate(log_entries):
            step = {
                'step': i + 1,
                'timestamp': entry.get('timestamp'),
                'thread': entry.get('thread_name'),
                'log_level': entry.get('log_level'),
                'logger': entry.get('logger'),
                'message_summary': self._summarize_message(entry.get('message', ''))
            }
            flow.append(step)

        return flow

    def _find_log_rows_with_trace_id(self, content: str, trace_id: str) -> List[str]:
        """
        Find all <log-row> blocks that contain the specified trace ID.
        """
        matching_rows = []

        # Pattern to match log-row blocks
        log_row_pattern = r'<log-row>(.*?)</log-row>'

        for match in re.finditer(log_row_pattern, content, re.DOTALL):
            log_row_content = match.group(0)  # Full log-row including tags

            # Check if this log row contains the trace ID
            if f'<request-id>{trace_id}</request-id>' in log_row_content:
                matching_rows.append(log_row_content)

        return matching_rows

    # tools/full_log_finder.py

    import re
    from pathlib import Path
    from typing import List, Dict, Union, Optional
    from tools.log_searcher import LogSearcher
    from tools.trace_id_extractor import TraceIDExtractor

    class FullLogFinder:
        """
        Find all log entries that contain a specific trace ID (request-id).
        """

        def __init__(self):
            self.log_searcher = LogSearcher(context=0)  # No context needed for trace searches

        def find_all_logs_for_trace(
                self,
                log_file_path: Union[str, Path],
                trace_id: str
        ) -> Dict:
            """
            Find all log entries that contain the specified trace ID.

            Args:
                log_file_path: Path to the log file
                trace_id: The trace ID (request-id) to search for

            Returns:
                Dictionary with trace_id, total_entries, log_entries, and timeline
            """
            log_file_path = Path(log_file_path)

            # Read full content
            full_content = self.log_searcher.read_full_content(log_file_path)

            # Find all log-row blocks that contain this trace ID
            matching_log_rows = self._find_log_rows_with_trace_id(full_content, trace_id)

            # Parse each log row into structured data
            parsed_entries = []
            for log_row_content in matching_log_rows:
                parsed_entry = self._parse_log_row(log_row_content)
                if parsed_entry:
                    parsed_entries.append(parsed_entry)

            # Sort by timestamp
            parsed_entries.sort(key=lambda x: x.get('timestamp', ''))

            # Create timeline
            timeline = self._create_timeline(parsed_entries)

            return {
                'trace_id': trace_id,
                'log_file': str(log_file_path),
                'total_entries': len(parsed_entries),
                'log_entries': parsed_entries,
                'timeline': timeline,
                'first_entry': parsed_entries[0] if parsed_entries else None,
                'last_entry': parsed_entries[-1] if parsed_entries else None
            }

        def find_traces_for_multiple_ids(
                self,
                log_file_path: Union[str, Path],
                trace_ids: List[str]
        ) -> Dict:
            """
            Find all log entries for multiple trace IDs.

            Args:
                log_file_path: Path to the log file
                trace_ids: List of trace IDs to search for

            Returns:
                Dictionary with results for each trace ID
            """
            results = {}

            for trace_id in trace_ids:
                results[trace_id] = self.find_all_logs_for_trace(log_file_path, trace_id)

            # Add summary
            summary = {
                'total_trace_ids': len(trace_ids),
                'trace_ids_found': len([r for r in results.values() if r['total_entries'] > 0]),
                'total_log_entries': sum(r['total_entries'] for r in results.values())
            }

            return {
                'summary': summary,
                'traces': results
            }

        def get_trace_flow(
                self,
                log_file_path: Union[str, Path],
                trace_id: str
        ) -> List[Dict]:
            """
            Get the flow/sequence of operations for a specific trace ID.

            Args:
                log_file_path: Path to the log file
                trace_id: The trace ID to trace

            Returns:
                List of operation steps in chronological order
            """
            trace_result = self.find_all_logs_for_trace(log_file_path, trace_id)
            log_entries = trace_result['log_entries']

            flow = []
            for i, entry in enumerate(log_entries):
                step = {
                    'step': i + 1,
                    'timestamp': entry.get('timestamp'),
                    'thread': entry.get('thread_name'),
                    'log_level': entry.get('log_level'),
                    'logger': entry.get('logger'),
                    'message_summary': self._summarize_message(entry.get('message', ''))
                }
                flow.append(step)

            return flow

        def _find_log_rows_with_trace_id(self, content: str, trace_id: str) -> List[str]:
            """
            Find all <log-row> blocks that contain the specified trace ID.
            """
            matching_rows = []

            # Pattern to match log-row blocks
            log_row_pattern = r'<log-row>(.*?)</log-row>'

            for match in re.finditer(log_row_pattern, content, re.DOTALL):
                log_row_content = match.group(0)  # Full log-row including tags

                # Check if this log row contains the trace ID
                if f'<request-id>{trace_id}</request-id>' in log_row_content:
                    matching_rows.append(log_row_content)

            return matching_rows

    def _parse_log_row(self, log_row_content: str) -> Optional[Dict]:
        """
        Parse a log-row XML into structured data while preserving original content.
        """
        try:
            parsed = {}

            # Store the original XML content
            parsed['original_xml'] = log_row_content

            # Extract each field using regex for timeline/summary purposes
            fields = {
                'timestamp': r'<dateTime>(.*?)</dateTime>',
                'request_id': r'<request-id>(.*?)</request-id>',
                'process_id': r'<processId>(.*?)</processId>',
                'thread_name': r'<threadName>(.*?)</threadName>',
                'thread_id': r'<threadId>(.*?)</threadId>',
                'thread_priority': r'<threadPriority>(.*?)</threadPriority>',
                'logger': r'<logger>(.*?)</logger>',
                'log_level': r'<log-level>(.*?)</log-level>',
                'message': r'<log-message>\s*(.*?)\s*</log-message>'
            }

            for field_name, pattern in fields.items():
                match = re.search(pattern, log_row_content, re.DOTALL)
                if match:
                    parsed[field_name] = match.group(1).strip()
                else:
                    parsed[field_name] = None

            # Clean up message (remove extra whitespace) for timeline only
            if parsed.get('message'):
                parsed['message'] = re.sub(r'\s+', ' ', parsed['message']).strip()

            return parsed

        except Exception as e:
            # If parsing fails, return basic info with original content
            return {
                'original_xml': log_row_content,
                'raw_content': log_row_content[:200] + '...' if len(log_row_content) > 200 else log_row_content,
                'parse_error': str(e)
            }

    def _create_timeline(self, log_entries: List[Dict]) -> List[Dict]:
        """
        Create a simplified timeline of events.
        """
        timeline = []

        for i, entry in enumerate(log_entries):
            timeline_entry = {
                'sequence': i + 1,
                'timestamp': entry.get('timestamp'),
                'level': entry.get('log_level'),
                'thread': entry.get('thread_name'),
                'operation': self._extract_operation(entry.get('message', ''))
            }
            timeline.append(timeline_entry)

        return timeline

    def _extract_operation(self, message: str) -> str:
        """
        Extract the main operation from a log message.
        """
        if not message:
            return 'Unknown'

        # Look for common patterns
        patterns = [
            r'Invoking Service.*?Method:\s*(\w+)',  # Service method calls
            r'(Starting|Ending|Processing|Executing)\s+(\w+)',  # Operation verbs
            r'Class:\s*.*?\.(\w+)',  # Class names
        ]

        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return match.group(1) if len(match.groups()) == 1 else f"{match.group(1)} {match.group(2)}"

        # Fallback: return first few words
        words = message.split()[:3]
        return ' '.join(words) if words else 'Unknown'

    def _summarize_message(self, message: str) -> str:
        """
        Create a brief summary of the log message.
        """
        if not message:
            return 'No message'

        # Truncate long messages
        if len(message) > 100:
            return message[:97] + '...'

        return message

    def search_by_pattern_in_trace_logs(
            self,
            log_file_path: Union[str, Path],
            trace_id: str,
            search_pattern: str
    ) -> List[Dict]:
        """
        Search for a specific pattern within all logs of a trace ID.

        Args:
            log_file_path: Path to the log file
            trace_id: The trace ID to search within
            search_pattern: Pattern to search for in the messages

        Returns:
            List of matching log entries
        """
        trace_result = self.find_all_logs_for_trace(log_file_path, trace_id)
        log_entries = trace_result['log_entries']

        matching_entries = []
        pattern = re.compile(search_pattern, re.IGNORECASE)

        for entry in log_entries:
            message = entry.get('message', '')
            if pattern.search(message):
                matching_entries.append(entry)

        return matching_entries

    def create_trace_files(
            self,
            log_file_path: Union[str, Path],
            trace_ids: List[str],
            output_dir: str = "trace_outputs"
    ) -> List[str]:
        """
        Create individual text files for each trace ID containing all their logs.

        Args:
            log_file_path: Path to the log file
            trace_ids: List of trace IDs to process
            output_dir: Directory to save the trace files

        Returns:
            List of created file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        created_files = []

        for trace_id in trace_ids:
            # Find all logs for this trace ID
            trace_data = self.find_all_logs_for_trace(log_file_path, trace_id)

            if trace_data['total_entries'] > 0:
                # Create filename with trace ID (sanitize for filesystem)
                safe_trace_id = re.sub(r'[^\w\-_]', '_', trace_id)
                trace_file = output_path / f"trace_{safe_trace_id}.txt"

                # Write all logs for this trace to the file
                with open(trace_file, 'w', encoding='utf-8') as f:
                    self._write_trace_file_content(f, trace_data)

                created_files.append(str(trace_file))

        return created_files

    def _write_trace_file_content(self, file_handle, trace_data: Dict):
        """
        Write the formatted content for a trace file, preserving original XML format.

        Args:
            file_handle: Open file handle to write to
            trace_data: Trace data dictionary from find_all_logs_for_trace
        """
        f = file_handle

        # Header Section
        f.write(f"TRACE ID: {trace_data['trace_id']}\n")
        f.write(f"TOTAL ENTRIES: {trace_data['total_entries']}\n")
        f.write(f"LOG FILE: {trace_data['log_file']}\n")
        f.write("=" * 80 + "\n\n")

        # Timeline Summary (keep this for quick overview)
        f.write("TIMELINE SUMMARY:\n")
        f.write("-" * 40 + "\n")
        for step in trace_data['timeline']:
            f.write(f"{step['sequence']:2d}. {step['timestamp']} - {step['operation']} [{step['level']}]\n")
        f.write("\n" + "=" * 80 + "\n\n")

        # Original XML Log Entries
        f.write("ORIGINAL LOG ENTRIES:\n")
        f.write("-" * 40 + "\n\n")

        for i, entry in enumerate(trace_data['log_entries'], 1):
            f.write(f"ENTRY {i}:\n")
            # Write the original XML content
            if 'original_xml' in entry:
                f.write(entry['original_xml'])
            elif 'raw_content' in entry:
                f.write(entry['raw_content'])
            else:
                # Fallback - shouldn't happen with updated parsing
                f.write("<!-- Original XML not available -->\n")
            f.write("\n" + "-" * 60 + "\n\n")

    def create_trace_files_from_search_results(
            self,
            log_file_path: Union[str, Path],
            search_results: List[Dict],
            output_dir: str = "trace_outputs"
    ) -> Dict:
        """
        Create trace files from search results that contain trace IDs.

        Args:
            log_file_path: Path to the log file
            search_results: List of search results with 'trace_id' field
            output_dir: Directory to save the trace files

        Returns:
            Dictionary with summary and created files
        """
        # Extract unique trace IDs from search results
        unique_trace_ids = []
        for result in search_results:
            trace_id = result.get('trace_id')
            if trace_id and trace_id not in unique_trace_ids:
                unique_trace_ids.append(trace_id)

        # Create files for each unique trace ID
        created_files = self.create_trace_files(log_file_path, unique_trace_ids, output_dir)

        return {
            'unique_trace_ids': unique_trace_ids,
            'total_unique_traces': len(unique_trace_ids),
            'files_created': created_files,
            'output_directory': output_dir
        }

    def _write_comprehensive_trace_file(self, file_handle, trace_data):
        """
        Write a comprehensive trace file that includes entries from multiple log files.
        Logs are sorted by timestamp for chronological order.
        """
        f = file_handle

        # Header Section
        f.write(f"COMPREHENSIVE TRACE ANALYSIS\n")
        f.write(f"TRACE ID: {trace_data['trace_id']}\n")
        f.write(f"TOTAL ENTRIES: {trace_data['total_entries']}\n")
        f.write(f"FILES SEARCHED: {trace_data['files_searched']}\n")
        f.write(f"FILES WITH ENTRIES: {trace_data['files_with_entries']}\n")
        f.write(f"SOURCE FILES: {', '.join([Path(f).name for f in trace_data['source_files']])}\n")
        f.write("=" * 80 + "\n\n")

        # Timeline Summary across all files (already sorted)
        f.write("COMPREHENSIVE TIMELINE (All Files):\n")
        f.write("-" * 50 + "\n")
        for i, step in enumerate(trace_data['timeline'], 1):
            source_file = step.get('source_file', 'Unknown')
            f.write(
                f"{i:2d}. {step['timestamp']} - {step['operation']} [{step['level']}] ({Path(source_file).name if source_file != 'Unknown' else 'Unknown'})\n")
        f.write("\n" + "=" * 80 + "\n\n")

        # Sort ALL log entries by timestamp chronologically
        f.write("LOG ENTRIES (Chronological Order):\n")
        f.write("-" * 50 + "\n\n")

        # Sort all entries by timestamp
        sorted_entries = sorted(trace_data['log_entries'], key=lambda x: x.get('timestamp', ''))

        for i, entry in enumerate(sorted_entries, 1):
            source_file = entry.get('source_file', 'Unknown')
            f.write(f"ENTRY {i} - {Path(source_file).name}:\n")
            f.write(f"Timestamp: {entry.get('timestamp', 'N/A')}\n")
            f.write("-" * 40 + "\n")

            if 'original_xml' in entry:
                f.write(entry['original_xml'])
            elif 'raw_content' in entry:
                f.write(entry['raw_content'])
            else:
                f.write("<!-- Original XML not available -->\n")
            f.write("\n" + "=" * 60 + "\n\n")

        # OPTIONAL: Also show entries grouped by source file (for reference)
        f.write("LOG ENTRIES BY SOURCE FILE (Reference):\n")
        f.write("-" * 50 + "\n\n")

        # Group entries by source file
        entries_by_file = {}
        for entry in sorted_entries:  # Use the sorted entries
            source_file = entry.get('source_file', 'Unknown')
            if source_file not in entries_by_file:
                entries_by_file[source_file] = []
            entries_by_file[source_file].append(entry)

        # Write entries for each file
        for source_file, entries in entries_by_file.items():
            f.write(f"SOURCE FILE: {Path(source_file).name}\n")
            f.write(f"ENTRIES: {len(entries)}\n")
            f.write("-" * 30 + "\n")

            for i, entry in enumerate(entries, 1):
                f.write(f"File Entry {i}: {entry.get('timestamp', 'N/A')}\n")
                if 'original_xml' in entry:
                    f.write(entry['original_xml'])
                elif 'raw_content' in entry:
                    f.write(entry['raw_content'])
                else:
                    f.write("<!-- Original XML not available -->\n")
                f.write("\n" + "-" * 40 + "\n\n")

            f.write("\n" + "=" * 60 + "\n\n")

    def create_comprehensive_trace_file(
            self,
            trace_data: Dict,
            output_dir: str = "trace_outputs"
    ) -> str:
        """
        Create a comprehensive trace file from compiled trace data.

        Args:
            trace_data: Comprehensive trace data dictionary
            output_dir: Directory to save the trace file

        Returns:
            Path to the created file
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        trace_id = trace_data['trace_id']
        safe_trace_id = re.sub(r'[^\w\-_]', '_', trace_id)
        trace_file = output_path / f"comprehensive_trace_{safe_trace_id}.txt"

        with open(trace_file, 'w', encoding='utf-8') as f:
            self._write_comprehensive_trace_file(f, trace_data)

        return str(trace_file)
