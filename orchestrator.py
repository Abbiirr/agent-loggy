import logging
import re
from pathlib import Path
from ollama import Client
from agents.parameter_agent import ParametersAgent
from agents.file_searcher import FileSearcher
from agents.verify_agent import VerifyAgent
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
        self.full_log_finder = FullLogFinder()
        self.verify_agent = VerifyAgent(client, model)

    def analyze(self, text: str):
        # Step 1: Run Parameter Agent
        logger.info("Step 1: Running Parameter Agent...")
        params = self.param_agent.run(text)
        logger.info(f"Extracted parameters: {params}")

        # Step 2: Run File Searcher
        logger.info("Step 2: Running File Searcher...")
        log_files = self.file_searcher.find_and_verify(params)
        print("Log files found:", log_files)

        if not log_files:
            logger.warning("No log files found by File Searcher")
            return {
                'parameters': params,
                'log_files': [],
                'total_files': 0,
                'message': 'No relevant log files found'
            }

        logger.info(f"Found {len(log_files)} verified log files:")
        for lf in log_files:
            logger.info(f"  ✓ {lf}")

        # Step 3: Search ALL log files to collect unique trace IDs
        logger.info(f"Step 3: Searching ALL {len(log_files)} log files to collect trace IDs...")

        patterns = params.get('query_keys', [])
        if not patterns:
            logger.warning("No query keys found in parameters")
            return {
                'parameters': params,
                'log_files': [str(lf) for lf in log_files],
                'total_files': len(log_files),
                'message': 'No query keys to search for'
            }

        try:
            all_trace_results = []
            unique_trace_ids = []

            # Search each log file for trace IDs
            for log_file in log_files:
                logger.info(f"Searching {log_file.name} for patterns: {patterns}")
                trace_results = self.log_searcher.search_with_trace_ids(log_file, patterns)
                logger.info(f"Found {len(trace_results)} matching lines with trace IDs in {log_file.name}")

                # Collect all results
                all_trace_results.extend(trace_results)

                # Extract unique trace IDs
                for result in trace_results:
                    trace_id = result.get('trace_id')
                    if trace_id and trace_id not in unique_trace_ids:
                        unique_trace_ids.append(trace_id)
                        logger.info(f"  Found new trace ID: {trace_id}")

            logger.info(f"Step 3 Complete: Found {len(unique_trace_ids)} unique trace IDs across all files")

            if not unique_trace_ids:
                logger.info("No trace IDs found in any log files")
                return {
                    'parameters': params,
                    'log_files': [str(lf) for lf in log_files],
                    'total_files': len(log_files),
                    'search_results': {
                        'files_searched': [str(lf) for lf in log_files],
                        'patterns': patterns,
                        'total_matches': len(all_trace_results),
                        'unique_trace_ids': [],
                        'message': 'No trace IDs found in any log files'
                    }
                }

            # Display summary of found trace IDs
            logger.info("Unique trace IDs found:")
            for i, trace_id in enumerate(unique_trace_ids, 1):
                logger.info(f"  {i}: {trace_id}")

            # Step 4: Search ALL log files for each unique trace ID to compile comprehensive logs
            logger.info(f"Step 4: Searching ALL log files for each of the {len(unique_trace_ids)} trace IDs...")

            all_trace_data = {}
            all_created_files = []

            for trace_id in unique_trace_ids:
                logger.info(f"Compiling comprehensive logs for trace ID: {trace_id}")
                trace_files_data = []

                # Search this trace ID in ALL log files
                for log_file in log_files:
                    logger.info(f"  Checking {log_file.name} for trace {trace_id}...")
                    trace_data = self.full_log_finder.find_all_logs_for_trace(log_file, trace_id)

                    if trace_data['total_entries'] > 0:
                        logger.info(f"    ✓ Found {trace_data['total_entries']} entries in {log_file.name}")
                        trace_files_data.append({
                            'file': log_file,
                            'data': trace_data
                        })
                    else:
                        logger.info(f"    ✗ No entries found in {log_file.name}")

                # Compile comprehensive trace data from all files
                if trace_files_data:
                    combined_entries = []
                    combined_timeline = []
                    source_files = []

                    for file_data in trace_files_data:
                        file_path = file_data['file']
                        data = file_data['data']
                        source_files.append(str(file_path))

                        # Add entries with source file info
                        for entry in data['log_entries']:
                            entry['source_file'] = str(file_path)
                            combined_entries.append(entry)

                        # Add timeline entries with source file info
                        for timeline_entry in data['timeline']:
                            timeline_entry['source_file'] = str(file_path)
                            combined_timeline.append(timeline_entry)

                    # Sort by timestamp for chronological order
                    combined_entries.sort(key=lambda x: x.get('timestamp', ''))
                    combined_timeline.sort(key=lambda x: x.get('timestamp', ''))

                    # Create comprehensive trace data
                    comprehensive_trace_data = {
                        'trace_id': trace_id,
                        'total_entries': len(combined_entries),
                        'log_entries': combined_entries,
                        'timeline': combined_timeline,
                        'source_files': source_files,
                        'files_searched': len(log_files),
                        'files_with_entries': len(trace_files_data)
                    }

                    all_trace_data[trace_id] = comprehensive_trace_data

                    # Create comprehensive trace file using FullLogFinder
                    logger.info(f"Creating comprehensive trace file for {trace_id}...")
                    trace_file = self.full_log_finder.create_comprehensive_trace_file(
                        comprehensive_trace_data, "trace_outputs"
                    )

                    all_created_files.append(str(trace_file))
                    logger.info(f"✓ Created: {trace_file}")
                    logger.info(f"  Total entries: {comprehensive_trace_data['total_entries']}")
                    logger.info(f"  Source files: {', '.join([Path(f).name for f in source_files])}")
                else:
                    logger.warning(f"No comprehensive data found for trace ID {trace_id}")

            # Generate final summary for search results
            search_results = {
                'files_searched': [str(lf) for lf in log_files],
                'patterns': patterns,
                'matches': [r['match'] for r in all_trace_results[:10]],
                'total_matches': len(all_trace_results),
                'trace_ids': all_trace_results[:10],
                'unique_trace_ids': unique_trace_ids,
                'total_files': len(log_files)
            }

            file_creation_result = {
                'unique_trace_ids': unique_trace_ids,
                'total_unique_traces': len(unique_trace_ids),
                'files_created': all_created_files,
                'output_directory': "trace_outputs",
                'comprehensive_search': True,
                'files_searched_per_trace': len(log_files),
                'all_trace_data': all_trace_data
            }

            logger.info("Step 4 Complete: Comprehensive trace analysis finished")
            logger.info(f"Created {len(all_created_files)} comprehensive trace files")

            # Set trace_analysis to the first comprehensive trace for backward compatibility
            trace_analysis = None
            if unique_trace_ids and unique_trace_ids[0] in all_trace_data:
                trace_analysis = all_trace_data[unique_trace_ids[0]]

            # Step 5: Verify and Analyze Results
            logger.info("Step 5: Running Verify Agent...")

            verification_results = self.verify_agent.analyze_and_verify(
                original_context=text,  # Original user input
                search_results=search_results,
                trace_data={'all_trace_data': all_trace_data},
                parameters=params
            )

            logger.info(f"Verification complete. Confidence: {verification_results['confidence_score']}/100")
            logger.info(f"Further search needed: {verification_results['further_search_needed']['decision']}")

            # Return comprehensive results
            return {
                'parameters': params,
                'log_files': [str(lf) for lf in log_files],
                'total_files': len(log_files),
                'search_results': search_results,
                'file_creation_result': file_creation_result,
                'trace_analysis': trace_analysis,
                'verification_results': verification_results
            }

        except Exception as e:
            logger.error(f"Error during log analysis: {e}")
            return {
                'parameters': params,
                'log_files': [str(lf) for lf in log_files],
                'total_files': len(log_files),
                'search_error': str(e)
            }