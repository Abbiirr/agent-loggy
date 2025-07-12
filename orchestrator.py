import logging
from pathlib import Path
from ollama import Client
from agents.parameter_agent import ParametersAgent
from agents.file_searcher import FileSearcher
from tools.log_searcher import LogSearcher
from tools.trace_id_extractor import TraceIDExtractor
from tools.full_log_finder import FullLogFinder

logger = logging.getLogger(__name__)


class Orchestrator:
    """Runs ParametersAgent and FileSearcher to find relevant log files."""

    def __init__(self, client: Client, model: str, log_base_dir: str = "./data"):
        self.param_agent = ParametersAgent(client, model)
        self.file_searcher = FileSearcher(Path(log_base_dir), client, model)
        self.log_searcher = LogSearcher(context=2)  # 2 lines of context
        self.full_log_finder = FullLogFinder()  # New tool for finding all logs with a trace ID

    def analyze(self, text: str):
        # Hardcode parameters for testing FileSearcher
        params = {
            'time_frame': '06.11.2024',
            'domain': 'NPSB, BEFTN',
            'query_keys': ['112013800000010', '114412200000042']
        }

        logger.info("Using hardcoded parameters: %s", params)

        # Hardcode log files result instead of searching
        logger.info("Using hardcoded log file result...")
        log_files = [Path("data/trace.log.2024-11-06.12.xz")]

        if log_files:
            logger.info(f"Found {len(log_files)} verified log files:")
            for lf in log_files:
                logger.info(f"  ✓ {lf}")

            # Hardcode log searching in the found file
            target_file = Path("data/trace.log.2024-11-06.12.xz")
            if target_file.exists():
                logger.info(f"Searching in hardcoded file: {target_file}")

                # Search for the query keys in the log file
                patterns = params['query_keys']  # ['112013800000010', '114412200000042']

                try:
                    # Use the enhanced search that automatically extracts trace IDs
                    trace_results = self.log_searcher.search_with_trace_ids(target_file, patterns)
                    logger.info(f"Found {len(trace_results)} matching lines with trace IDs in {target_file.name}")

                    if trace_results:
                        logger.info("Sample matches with trace IDs:")
                        for i, result in enumerate(trace_results[:5]):  # Show first 5 matches
                            match = result['match']
                            trace_id = result['trace_id']
                            logger.info(f"  {i + 1}: {match[:100]}...")  # Truncate long lines
                            if trace_id:
                                logger.info(f"      Trace ID: {trace_id}")
                            else:
                                logger.info(f"      No trace ID found")

                        trace_analysis = None

                        if trace_results:
                            logger.info("Creating trace log files...")

                            # Use FullLogFinder to create trace files
                            file_creation_result = self.full_log_finder.create_trace_files_from_search_results(
                                target_file, trace_results, "trace_outputs"
                            )

                            created_files = file_creation_result['files_created']
                            unique_trace_ids = file_creation_result['unique_trace_ids']

                            logger.info(f"Found {len(unique_trace_ids)} unique trace IDs")
                            logger.info(f"Created {len(created_files)} trace files")

                            for file_path in created_files:
                                logger.info(f"Created: {file_path}")

                            # Set trace_analysis to the first trace for backward compatibility
                            if unique_trace_ids:
                                trace_analysis = self.full_log_finder.find_all_logs_for_trace(target_file,
                                                                                              unique_trace_ids[0])
                                logger.info("Timeline for first trace:")
                                for step in trace_analysis['timeline'][:3]:  # Show first 3 steps
                                    logger.info(f"  {step['sequence']}: {step['timestamp']} - {step['operation']}")

                    return {
                        'parameters': params,
                        'log_files': [str(lf) for lf in log_files],
                        'total_files': len(log_files),
                        'search_results': {
                            'file': str(target_file),
                            'patterns': patterns,
                            'matches': [r['match'] for r in trace_results[:10]],  # Return first 10 matches
                            'total_matches': len(trace_results),
                            'trace_ids': trace_results[:10],  # Return first 10 with trace IDs
                            'trace_analysis': trace_analysis,  # Include trace analysis if available
                            'file_creation_result': file_creation_result if trace_results else None
                        }
                    }
                except Exception as e:
                    logger.error(f"Error searching in {target_file}: {e}")
                    return {
                        'parameters': params,
                        'log_files': [str(lf) for lf in log_files],
                        'total_files': len(log_files),
                        'search_error': str(e)
                    }
            else:
                logger.warning(f"Hardcoded file not found: {target_file}")

        return {
            'parameters': params,
            'log_files': [str(lf) for lf in log_files] if log_files else [],
            'total_files': len(log_files) if log_files else 0
        }