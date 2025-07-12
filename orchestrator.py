import logging
from pathlib import Path
from ollama import Client
from agents.parameter_agent import ParametersAgent
from agents.file_searcher import FileSearcher
from tools.log_searcher import LogSearcher
from tools.trace_id_extractor import TraceIDExtractor
from tools.full_log_finder import FullLogFinder
from agents.verify_agent import VerifyAgent  # This will be the enhanced version
import json

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Enhanced Orchestrator that creates comprehensive files containing both
    verification analysis and complete log content for each trace.
    """

    def __init__(self, client: Client, model: str, log_base_dir: str = "./data"):
        self.param_agent = ParametersAgent(client, model)
        self.file_searcher = FileSearcher(Path(log_base_dir), client, model)
        self.log_searcher = LogSearcher(context=2)  # 2 lines of context
        self.full_log_finder = FullLogFinder()
        # Use enhanced VerifyAgent with different output directory
        self.verify_agent = VerifyAgent(client, model, output_dir="comprehensive_analysis")

    def analyze(self, text: str):
        """
        Complete analysis pipeline that creates comprehensive files for each trace
        containing both verification analysis and complete log content.
        """

        # Step 1: Run Parameter Agent
        logger.info("Step 1: Running Parameter Agent...")
        params = self.param_agent.run(text)
        # print(json.dumps(params, indent=2, ensure_ascii=False))
        logger.info(f"Extracted parameters: {params}")

        # Step 2: Run File Searcher
        logger.info("Step 2: Running File Searcher...")
        log_files = self.file_searcher.find_and_verify(params)
        # print("\n")
        # print("Log files found:\n", json.dumps([str(f) for f in log_files], indent=2, ensure_ascii=False))

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

            # Step 4: Compile comprehensive trace data for each trace ID
            logger.info(f"Step 4: Compiling comprehensive data for each of the {len(unique_trace_ids)} trace IDs...")

            all_trace_data = {}

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
                    logger.info(f"✓ Compiled {len(combined_entries)} total entries for trace {trace_id}")
                    logger.info(f"  Source files: {', '.join([Path(f).name for f in source_files])}")
                else:
                    logger.warning(f"No comprehensive data found for trace ID {trace_id}")

            logger.info("Step 4 Complete: Comprehensive trace data compilation finished")

            # Step 5: Create comprehensive files using Enhanced VerifyAgent
            logger.info("Step 5: Creating comprehensive analysis files with Enhanced VerifyAgent...")

            search_results = {
                'files_searched': [str(lf) for lf in log_files],
                'patterns': patterns,
                'total_files': len(log_files),
                'total_matches': len(all_trace_results),
                'unique_trace_ids': unique_trace_ids,
                'message': f'Found {len(unique_trace_ids)} unique trace IDs in {len(log_files)} files'
            }

            trace_data_for_verification = {
                'all_trace_data': all_trace_data
            }

            logger.info(f"Enhanced VerifyAgent will analyze {len(all_trace_data)} traces")

            # Use the enhanced method that creates comprehensive files
            comprehensive_results = self.verify_agent.analyze_and_create_comprehensive_files(
                original_context=text,
                search_results=search_results,
                trace_data=trace_data_for_verification,
                parameters=params,
                output_prefix="banking_analysis"
            )

            logger.info("Step 5 Complete: Enhanced verification and file creation finished")
            logger.info(
                f"Created {len(comprehensive_results.get('comprehensive_files_created', []))} comprehensive files")
            logger.info(f"Master summary: {comprehensive_results.get('master_summary_file', 'N/A')}")

            # Display created files
            created_files = comprehensive_results.get('comprehensive_files_created', [])
            if created_files:
                logger.info("Comprehensive files created:")
                for i, file_path in enumerate(created_files, 1):
                    logger.info(f"  {i}. {Path(file_path).name}")

            # Final result structure
            return {
                'parameters': params,
                'log_files': [str(lf) for lf in log_files],
                'total_files': len(log_files),
                'search_results': search_results,
                'trace_data_summary': {
                    'unique_trace_ids': unique_trace_ids,
                    'total_unique_traces': len(unique_trace_ids),
                    'comprehensive_search': True,
                    'files_searched_per_trace': len(log_files),
                    'total_log_entries': sum(td.get('total_entries', 0) for td in all_trace_data.values())
                },
                'comprehensive_analysis_results': comprehensive_results,
                'output_summary': {
                    'comprehensive_files_created': created_files,
                    'master_summary_file': comprehensive_results.get('master_summary_file'),
                    'output_directory': str(self.verify_agent.output_dir),
                    'total_traces_analyzed': comprehensive_results.get('total_traces_analyzed', 0),
                    'overall_confidence': comprehensive_results.get('confidence_score', 0)
                }
            }

        except Exception as e:
            logger.error(f"Error during enhanced log analysis: {e}")
            return {
                'parameters': params,
                'log_files': [str(lf) for lf in log_files],
                'total_files': len(log_files),
                'analysis_error': str(e),
                'message': 'Analysis failed due to processing error'
            }

    def get_analysis_summary(self, analysis_result: dict) -> str:
        """
        Generate a human-readable summary of the analysis results.
        """

        if 'analysis_error' in analysis_result:
            return f"Analysis failed: {analysis_result['analysis_error']}"

        if not analysis_result.get('comprehensive_analysis_results'):
            return "No comprehensive analysis results available"

        comprehensive_results = analysis_result['comprehensive_analysis_results']
        output_summary = analysis_result.get('output_summary', {})

        summary_lines = [
            "BANKING LOG ANALYSIS SUMMARY",
            "=" * 35,
            f"Traces Analyzed: {comprehensive_results.get('total_traces_analyzed', 0)}",
            f"Overall Confidence: {comprehensive_results.get('confidence_score', 0)}/100",
            f"Files Created: {len(output_summary.get('comprehensive_files_created', []))}",
            f"Output Directory: {output_summary.get('output_directory', 'N/A')}",
            "",
            "FILES CREATED:",
            "-" * 15
        ]

        created_files = output_summary.get('comprehensive_files_created', [])
        for i, file_path in enumerate(created_files, 1):
            summary_lines.append(f"{i}. {Path(file_path).name}")

        if output_summary.get('master_summary_file'):
            summary_lines.append(f"Master Summary: {Path(output_summary['master_summary_file']).name}")

        summary_lines.extend([
            "",
            "Each comprehensive file contains:",
            "• Executive summary and analysis",
            "• Original dispute context",
            "• Detailed findings and recommendations",
            "• Complete chronological timeline",
            "• Full original log entries in XML format",
            "• Technical analysis details"
        ])

        return "\n".join(summary_lines)

    def list_output_files(self) -> list:
        """
        List all files in the comprehensive analysis output directory.
        """
        try:
            output_dir = self.verify_agent.output_dir
            if output_dir.exists():
                files = list(output_dir.glob("*.txt"))
                return [str(f) for f in sorted(files)]
            else:
                return []
        except Exception as e:
            logger.error(f"Error listing output files: {e}")
            return []