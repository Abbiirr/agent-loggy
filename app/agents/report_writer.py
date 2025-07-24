# agents/report_writer.py - Handles all report generation and file writing

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import re
from datetime import datetime as dt

logger = logging.getLogger(__name__)


class ReportWriter:
    """
    Handles all report generation and file writing for banking log analysis.
    Separated from VerifyAgent to maintain single responsibility principle.
    """

    def __init__(self, output_dir: str = "comprehensive_analysis", model_name: str = "unknown"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model_name = model_name
        logger.info(f"ReportWriter initialized with output directory: {self.output_dir}")

    def create_comprehensive_trace_file(
            self,
            trace_id: str,
            trace_analysis: Dict,
            trace_data: Dict,
            original_context: str,
            parameters: Dict,
            overall_quality: Dict,
            output_prefix: str = None
    ) -> str:
        """Create a comprehensive file with analysis + full logs for a single trace."""

        timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
        safe_trace_id = re.sub(r'[^\w\-_]', '_', trace_id)
        prefix = output_prefix or "comprehensive"

        filename = f"{prefix}_trace_{safe_trace_id}_{timestamp}.txt"
        file_path = self.output_dir / filename

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                self._write_comprehensive_trace_content(
                    f, trace_id, trace_analysis, trace_data,
                    original_context, parameters, overall_quality
                )

            logger.info(f"Comprehensive trace file created: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Error creating comprehensive file for trace {trace_id}: {e}")
            raise

    def create_master_summary_file(
            self,
            original_context: str,
            search_results: Dict,
            trace_analyses: Dict,
            overall_quality: Dict,
            parameters: Dict,
            created_files: List[str],
            output_prefix: str = None
    ) -> str:
        """Create a master summary file with overview of all traces."""

        timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
        prefix = output_prefix or "master_summary"
        filename = f"{prefix}_{timestamp}.txt"
        file_path = self.output_dir / filename

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                self._write_master_summary_content(
                    f, original_context, search_results, trace_analyses,
                    overall_quality, parameters, created_files
                )

            logger.info(f"Master summary file created: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Error creating master summary: {e}")
            raise

    def create_individual_trace_report(
            self,
            trace_id: str,
            trace_entries: List[Dict[str, Any]],
            dispute_text: str,
            search_params: Dict[str, Any],
            expert_analysis: Dict[str, Any]
    ) -> str:
        """Generate a comprehensive report for a single trace."""

        timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
        safe_trace_id = re.sub(r'[^\w\-_]', '_', trace_id)[:12]
        filename = f"trace_report_{safe_trace_id}_{timestamp}.txt"
        file_path = self.output_dir / filename

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                self._write_individual_trace_report(
                    f, trace_id, trace_entries, dispute_text, search_params, expert_analysis
                )

            logger.info(f"Individual trace report created: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Error creating individual trace report for {trace_id}: {e}")
            raise

    def create_master_analysis_summary(
            self,
            trace_groups: Dict[str, List[Dict[str, Any]]],
            all_entries: List[Dict[str, Any]],
            dispute_text: str,
            search_params: Dict[str, Any],
            trace_analyses: Dict[str, Dict[str, Any]]
    ) -> str:
        """Generate master summary report for multiple traces."""

        timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
        filename = f"master_summary_{timestamp}.txt"
        file_path = self.output_dir / filename

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                self._write_master_analysis_summary(
                    f, trace_groups, all_entries, dispute_text, search_params, trace_analyses
                )

            logger.info(f"Master analysis summary created: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Error creating master analysis summary: {e}")
            raise

    def _write_comprehensive_trace_content(
            self,
            file_handle,
            trace_id: str,
            trace_analysis: Dict,
            trace_data: Dict,
            original_context: str,
            parameters: Dict,
            overall_quality: Dict
    ):
        """Write the complete content for a comprehensive trace file."""

        f = file_handle

        # =====================================
        # HEADER SECTION
        # =====================================
        f.write("COMPREHENSIVE BANKING LOG ANALYSIS\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Trace ID: {trace_id}\n")
        f.write(f"Analysis Model: {self.model_name}\n")
        f.write("=" * 60 + "\n\n")

        # =====================================
        # EXECUTIVE SUMMARY
        # =====================================
        f.write("EXECUTIVE SUMMARY\n")
        f.write("-" * 20 + "\n")
        f.write(f"Relevance Score: {trace_analysis.get('relevance_score', 0)}/100\n")
        f.write(f"Confidence Level: {trace_analysis.get('confidence_level', 'UNKNOWN')}\n")
        f.write(f"Primary Issue: {trace_analysis.get('primary_issue', 'UNKNOWN')}\n")
        f.write(f"Total Log Entries: {trace_data.get('total_entries', 0)}\n")
        f.write(f"Source Files: {len(trace_data.get('source_files', []))}\n")
        f.write(f"Recommendation: {trace_analysis.get('recommendation', 'Further investigation needed')}\n")
        f.write("\n")

        # =====================================
        # ORIGINAL DISPUTE CONTEXT
        # =====================================
        f.write("ORIGINAL DISPUTE\n")
        f.write("-" * 17 + "\n")
        f.write(f"{original_context}\n\n")

        # =====================================
        # SEARCH PARAMETERS
        # =====================================
        f.write("SEARCH PARAMETERS\n")
        f.write("-" * 18 + "\n")
        f.write(f"Time Frame: {parameters.get('time_frame', 'N/A')}\n")
        f.write(f"Domain: {parameters.get('domain', 'N/A')}\n")
        f.write(f"Account Numbers: {', '.join(str(k) for k in parameters.get('query_keys', []))}\n")
        f.write("\n")

        # =====================================
        # DETAILED ANALYSIS
        # =====================================
        f.write("DETAILED ANALYSIS\n")
        f.write("-" * 18 + "\n")
        f.write(f"Key Finding: {trace_analysis.get('key_finding', 'No specific finding identified')}\n")
        f.write(f"Timeline Summary: {trace_analysis.get('timeline_summary', 'Timeline analysis not available')}\n")
        f.write("\n")

        # Critical Indicators
        indicators = trace_analysis.get('critical_indicators', [])
        if indicators:
            f.write("Critical Indicators:\n")
            for i, indicator in enumerate(indicators, 1):
                f.write(f"  {i}. {indicator}\n")
        else:
            f.write("Critical Indicators: None identified\n")
        f.write("\n")

        # Concerns
        concerns = trace_analysis.get('concerns', [])
        if concerns:
            f.write("Concerns/Red Flags:\n")
            for i, concern in enumerate(concerns, 1):
                f.write(f"  {i}. {concern}\n")
        else:
            f.write("Concerns/Red Flags: None identified\n")
        f.write("\n")

        # =====================================
        # TRACE TIMELINE
        # =====================================
        f.write("TRANSACTION TIMELINE\n")
        f.write("-" * 20 + "\n")
        timeline = trace_data.get('timeline', [])
        if timeline:
            f.write(f"Total Events: {len(timeline)}\n")
            f.write("Chronological Flow:\n\n")

            for i, event in enumerate(timeline, 1):
                source_file = event.get('source_file', 'Unknown')
                f.write(f"{i:2d}. {event.get('timestamp', 'N/A')}")
                f.write(f" | {event.get('level', 'INFO'):5s}")
                f.write(f" | {event.get('operation', 'Unknown Operation')}")
                f.write(f" | {Path(source_file).name if source_file != 'Unknown' else 'Unknown'}\n")
        else:
            f.write("No timeline events available\n")
        f.write("\n")

        # =====================================
        # SOURCE FILES
        # =====================================
        f.write("SOURCE LOG FILES\n")
        f.write("-" * 17 + "\n")
        source_files = trace_data.get('source_files', [])
        if source_files:
            for i, file_path in enumerate(source_files, 1):
                f.write(f"{i}. {file_path}\n")
        else:
            f.write("No source files identified\n")
        f.write("\n")

        # =====================================
        # COMPLETE LOG ENTRIES
        # =====================================
        f.write("COMPLETE LOG ENTRIES (Chronological Order)\n")
        f.write("=" * 50 + "\n\n")

        log_entries = trace_data.get('log_entries', [])
        if log_entries:
            # Sort by timestamp for chronological order
            sorted_entries = sorted(log_entries, key=lambda x: x.get('timestamp', ''))

            for i, entry in enumerate(sorted_entries, 1):
                source_file = entry.get('source_file', 'Unknown')
                f.write(f"LOG ENTRY {i}\n")
                f.write("-" * 15 + "\n")
                f.write(f"Source: {Path(source_file).name if source_file != 'Unknown' else 'Unknown'}\n")
                f.write(f"Timestamp: {entry.get('timestamp', 'N/A')}\n")
                f.write(f"Thread: {entry.get('thread_name', 'N/A')}\n")
                f.write(f"Level: {entry.get('log_level', 'N/A')}\n")
                f.write("\nFull Log Content:\n")
                f.write("-" * 20 + "\n")

                # Write the original XML content
                if 'original_xml' in entry:
                    f.write(entry['original_xml'])
                elif 'raw_content' in entry:
                    f.write(entry['raw_content'])
                else:
                    f.write("<!-- Original XML content not available -->\n")

                f.write("\n" + "=" * 60 + "\n\n")
        else:
            f.write("No log entries available for this trace.\n\n")

        # =====================================
        # TECHNICAL DETAILS
        # =====================================
        f.write("TECHNICAL ANALYSIS DETAILS\n")
        f.write("-" * 27 + "\n")
        f.write(f"Overall Data Quality: {overall_quality.get('overall_confidence', 0)}/100\n")
        f.write(f"Completeness Score: {overall_quality.get('completeness_score', 0)}/100\n")
        f.write(f"Relevance Score: {overall_quality.get('relevance_score', 0)}/100\n")
        f.write(f"Coverage Score: {overall_quality.get('coverage_score', 0)}/100\n")
        f.write("\n")

        # =====================================
        # FOOTER
        # =====================================
        f.write("=" * 60 + "\n")
        f.write("END OF COMPREHENSIVE ANALYSIS\n")
        f.write(f"File generated by Enhanced VerifyAgent v2.0\n")
        f.write(f"Analysis completed: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n")

    def _write_master_summary_content(
            self,
            file_handle,
            original_context: str,
            search_results: Dict,
            trace_analyses: Dict,
            overall_quality: Dict,
            parameters: Dict,
            created_files: List[str]
    ):
        """Write the content for the master summary file."""

        f = file_handle

        # Header
        f.write("MASTER ANALYSIS SUMMARY\n")
        f.write("=" * 40 + "\n")
        f.write(f"Generated: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Traces Analyzed: {len(trace_analyses)}\n")
        f.write(f"Overall Confidence: {overall_quality.get('overall_confidence', 0)}/100\n")
        f.write("=" * 40 + "\n\n")

        # Original Context
        f.write("ORIGINAL DISPUTE:\n")
        f.write("-" * 17 + "\n")
        f.write(f"{original_context}\n\n")

        # Summary Statistics
        f.write("ANALYSIS STATISTICS:\n")
        f.write("-" * 20 + "\n")
        f.write(f"Files Searched: {search_results.get('total_files', 0)}\n")
        f.write(f"Total Matches: {search_results.get('total_matches', 0)}\n")
        f.write(f"Unique Traces: {len(trace_analyses)}\n")
        f.write(f"Comprehensive Files Created: {len(created_files)}\n")
        f.write("\n")

        # Trace Rankings
        if trace_analyses:
            f.write("TRACE RANKINGS (by Relevance):\n")
            f.write("-" * 30 + "\n")

            # Sort traces by relevance score
            sorted_traces = sorted(
                trace_analyses.items(),
                key=lambda x: x[1].get('relevance_score', 0),
                reverse=True
            )

            for i, (trace_id, analysis) in enumerate(sorted_traces, 1):
                relevance = analysis.get('relevance_score', 0)
                issue = analysis.get('primary_issue', 'Unknown')
                confidence = analysis.get('confidence_level', 'Unknown')
                f.write(f"{i}. {trace_id[:20]}... ({relevance}% relevance, {issue}, {confidence} confidence)\n")
            f.write("\n")

        # File Locations
        f.write("COMPREHENSIVE FILES CREATED:\n")
        f.write("-" * 30 + "\n")
        for i, file_path in enumerate(created_files, 1):
            f.write(f"{i}. {Path(file_path).name}\n")
        f.write("\n")

        # Overall Assessment
        f.write("OVERALL ASSESSMENT:\n")
        f.write("-" * 19 + "\n")
        status = overall_quality.get('status', 'Assessment not available')
        f.write(f"Status: {status}\n")

        gaps = overall_quality.get('key_gaps', [])
        if gaps:
            f.write("Key Gaps Identified:\n")
            for gap in gaps:
                f.write(f"  • {gap}\n")
        f.write("\n")

        # Footer
        f.write("=" * 40 + "\n")
        f.write(f"For detailed analysis, review individual trace files above.\n")
        f.write("=" * 40 + "\n")

    def _write_individual_trace_report(
            self,
            file_handle,
            trace_id: str,
            trace_entries: List[Dict[str, Any]],
            dispute_text: str,
            search_params: Dict[str, Any],
            expert_analysis: Dict[str, Any]
    ):
        """Write the complete content for an individual trace report."""
        f = file_handle

        # Header
        f.write("BANKING TRANSACTION TRACE ANALYSIS\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Trace ID: {trace_id}\n")
        f.write(f"Total Log Entries: {len(trace_entries)}\n")
        f.write(f"Analysis Model: {self.model_name}\n")
        f.write("=" * 60 + "\n\n")

        # Original Dispute
        f.write("ORIGINAL CUSTOMER DISPUTE\n")
        f.write("-" * 25 + "\n")
        f.write(f"{dispute_text.strip()}\n\n")

        # Executive Summary
        f.write("EXECUTIVE SUMMARY\n")
        f.write("-" * 17 + "\n")
        f.write(f"Transaction Status: {expert_analysis.get('transaction_outcome', 'Unknown')}\n")
        f.write(f"Confidence Level: {expert_analysis.get('confidence_level', 'Unknown')}\n")
        f.write(f"Primary Issue: {expert_analysis.get('primary_issue', 'Unknown')}\n")
        f.write(f"Customer Claim: {expert_analysis.get('customer_claim_assessment', 'Unknown')}\n")
        f.write(f"Recommendation: {expert_analysis.get('recommendation', 'Further investigation needed')}\n")
        f.write("\n")

        # Expert Analysis & Opinion
        f.write("EXPERT ANALYSIS & OPINION\n")
        f.write("-" * 25 + "\n")
        f.write(f"Key Finding: {expert_analysis.get('key_finding', 'No specific findings identified')}\n\n")
        f.write(
            f"Transaction Summary: {expert_analysis.get('request_summary', 'Transaction analysis not available')}\n\n")
        f.write(
            f"Root Cause Analysis: {expert_analysis.get('root_cause_analysis', 'Root cause analysis not available')}\n\n")

        # Evidence and indicators
        evidence = expert_analysis.get('evidence_found', [])
        if evidence:
            f.write("Evidence Found:\n")
            for i, item in enumerate(evidence, 1):
                f.write(f"  {i}. {item}\n")
        f.write("\n")

        # Event Overview
        f.write("EVENT OVERVIEW\n")
        f.write("-" * 14 + "\n")
        f.write(f"Timeline Summary: {expert_analysis.get('timeline_summary', 'Timeline analysis not available')}\n\n")

        # High-level event flow with new format
        self._write_high_level_event_flow(f, trace_entries)

        # Complete Chronological Logs
        f.write("COMPLETE CHRONOLOGICAL LOG ENTRIES\n")
        f.write("=" * 50 + "\n\n")

        for i, entry in enumerate(trace_entries, 1):
            f.write(f"LOG ENTRY #{i}\n")
            f.write("-" * 15 + "\n")

            # Handle timestamp extraction for both formats
            timestamp = 'N/A'
            if 'timestamp' in entry:
                timestamp = entry['timestamp']
            elif 'values' in entry and entry['values'] and len(entry['values']) > 0:
                try:
                    # For Loki format, timestamp is in values[0][0]
                    timestamp_ns = entry['values'][0][0]
                    if isinstance(timestamp_ns, str) and len(timestamp_ns) > 10:
                        timestamp_sec = int(timestamp_ns) / 1e9
                        from datetime import datetime
                        timestamp = datetime.fromtimestamp(timestamp_sec)
                except:
                    pass

            if hasattr(timestamp, 'strftime'):
                timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

            # Handle service name extraction
            service_name = entry.get('service_name', 'Unknown')
            if service_name == 'Unknown' and 'stream' in entry and 'service_name' in entry['stream']:
                service_name = entry['stream']['service_name']

            # Handle severity/level extraction
            level = entry.get('severity_text', 'Unknown')
            if level == 'Unknown' and 'stream' in entry and 'severity_text' in entry['stream']:
                level = entry['stream']['severity_text']
            elif level == 'Unknown' and 'level' in entry:
                level = entry['level']

            # Extract additional fields
            service_instance_id = entry.get('service_instance_id', 'Unknown')
            if service_instance_id == 'Unknown' and 'stream' in entry and 'service_instance_id' in entry['stream']:
                service_instance_id = entry['stream']['service_instance_id']

            trace_id = entry.get('trace_id', 'Unknown')
            if trace_id == 'Unknown' and 'stream' in entry and 'trace_id' in entry['stream']:
                trace_id = entry['stream']['trace_id']

            service_namespace = entry.get('service_namespace', 'Unknown')
            if service_namespace == 'Unknown' and 'stream' in entry and 'service_namespace' in entry['stream']:
                service_namespace = entry['stream']['service_namespace']

            host_name = entry.get('host_name', 'Unknown')
            if host_name == 'Unknown' and 'stream' in entry and 'host_name' in entry['stream']:
                host_name = entry['stream']['host_name']

            span_id = entry.get('span_id', 'Unknown')
            if span_id == 'Unknown' and 'stream' in entry and 'span_id' in entry['stream']:
                span_id = entry['stream']['span_id']

            # Write header information
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Service: {service_name}\n")
            f.write(f"Service Instance ID: {service_instance_id}\n")
            f.write(f"Service Namespace: {service_namespace}\n")
            f.write(f"Level: {level}\n")
            f.write(f"Host Name: {host_name}\n")
            f.write(f"Trace ID: {trace_id}\n")
            f.write(f"Span ID: {span_id}\n")
            f.write(f"Thread: {entry.get('thread_name', 'Unknown')}\n")
            f.write("\nLog Content:\n")
            f.write("-" * 12 + "\n")

            # Get content - handle multiple formats
            content = 'No content available'
            if 'values' in entry and entry['values'] and len(entry['values']) > 0:
                try:
                    raw_content = entry['values'][0][1]
                    # Format JSON responses for readability if they exist
                    if raw_content and 'Response:' in raw_content:
                        lines = raw_content.split('\n')
                        formatted_lines = []
                        for line in lines:
                            if 'Response:' in line:
                                # Try to format JSON response
                                try:
                                    import json
                                    response_part = line.split('Response:', 1)[1].strip()
                                    if response_part.startswith('{') or response_part.startswith('['):
                                        parsed_json = json.loads(response_part)
                                        formatted_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                                        formatted_lines.append(line.split('Response:', 1)[0] + 'Response:')
                                        formatted_lines.append(formatted_json)
                                    else:
                                        formatted_lines.append(line)
                                except:
                                    formatted_lines.append(line)
                            else:
                                formatted_lines.append(line)
                        content = '\n'.join(formatted_lines)
                    else:
                        content = raw_content
                except:
                    pass
            elif 'message' in entry:
                content = entry['message']
            elif 'raw_content' in entry:
                content = entry['raw_content']
            elif 'original_xml' in entry:
                content = entry['original_xml']

            f.write(content)

            # Add values section for complete information
            if 'values' in entry and entry['values']:
                f.write("\n\nRaw Values:\n")
                f.write("-" * 11 + "\n")
                for idx, value_pair in enumerate(entry['values']):
                    f.write(f"Value {idx + 1}:\n")
                    f.write(f"  Timestamp: {value_pair[0]}\n")
                    f.write(f"  Content: {value_pair[1]}\n")
                    if idx < len(entry['values']) - 1:
                        f.write("\n")

            f.write("\n\n" + "=" * 60 + "\n\n")

        # Footer
        f.write("=" * 60 + "\n")
        f.write("END OF TRACE ANALYSIS\n")
        f.write(f"Analysis completed: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n")

    def _write_master_analysis_summary(
            self,
            file_handle,
            trace_groups: Dict[str, List[Dict[str, Any]]],
            all_entries: List[Dict[str, Any]],
            dispute_text: str,
            search_params: Dict[str, Any],
            trace_analyses: Dict[str, Dict[str, Any]]
    ):
        """Write the content for the master analysis summary."""
        f = file_handle

        # Header
        f.write("COMPREHENSIVE BANKING LOG ANALYSIS - MASTER SUMMARY\n")
        f.write("=" * 60 + "\n")
        f.write(f"Generated: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Traces Analyzed: {len(trace_groups)}\n")
        f.write(f"Total Log Entries: {len(all_entries)}\n")
        f.write(f"Analysis Model: {self.model_name}\n")
        f.write("=" * 60 + "\n\n")

        # Original Dispute
        f.write("ORIGINAL CUSTOMER DISPUTE\n")
        f.write("-" * 25 + "\n")
        f.write(f"{dispute_text.strip()}\n\n")

        # Trace Analysis Summary
        f.write("TRACE ANALYSIS SUMMARY\n")
        f.write("-" * 22 + "\n")

        # Sort traces by relevance
        sorted_traces = sorted(
            trace_analyses.items(),
            key=lambda x: x[1].get('relevance_score', 0),
            reverse=True
        )

        for i, (trace_id, analysis) in enumerate(sorted_traces, 1):
            f.write(f"TRACE {i}: {trace_id}\n")
            f.write("-" * 30 + "\n")
            f.write(f"Relevance Score: {analysis.get('relevance_score', 0)}/100\n")
            f.write(f"Transaction Status: {analysis.get('transaction_outcome', 'Unknown')}\n")
            f.write(f"Key Finding: {analysis.get('key_finding', 'No findings')}\n")
            f.write(f"Recommendation: {analysis.get('recommendation', 'No recommendation')}\n")
            f.write("\n")

        # Comprehensive Timeline
        f.write("COMPREHENSIVE TRANSACTION TIMELINE\n")
        f.write("-" * 34 + "\n")
        f.write("All log entries across all traces in chronological order:\n\n")

        for i, entry in enumerate(all_entries[:100], 1):  # Limit to first 100 for readability
            timestamp = entry.get("timestamp")
            if hasattr(timestamp, 'strftime'):
                ts_str = timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            else:
                ts_str = str(timestamp) if timestamp else "N/A"

            level = entry.get("severity_text", entry.get("level", "N/A"))
            service = entry.get("service_name", "N/A")
            trace_id = entry.get("trace_id", "N/A")
            message = (entry.get("message") or "").replace("\n", " ")[:80]

            f.write(f"{i:3}. {ts_str} | {level:5} | {service:20} | {trace_id[:8]}... | {message}...\n")

        if len(all_entries) > 100:
            f.write(f"... and {len(all_entries) - 100} more entries\n")
        f.write("\n")

        # Footer
        f.write("=" * 60 + "\n")
        f.write("END OF MASTER SUMMARY\n")
        f.write(f"Individual trace reports available in same directory.\n")
        f.write(f"Analysis completed: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n")

    def _extract_key_events(self, trace_entries: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """Extract key events from trace entries with detailed banking system information."""
        key_events = []

        for entry in trace_entries:
            # Skip entries without proper data
            if not entry:
                continue

            # Extract timestamp - handle both direct timestamp and nested values structure
            timestamp = None
            if 'timestamp' in entry:
                timestamp = entry['timestamp']
            elif 'values' in entry and entry['values'] and len(entry['values']) > 0:
                # For Loki format, timestamp might be in values[0][0]
                try:
                    timestamp = entry['values'][0][0]
                    # Convert nanosecond timestamp to datetime if needed
                    if isinstance(timestamp, str) and len(timestamp) > 10:
                        # Assuming nanosecond timestamp
                        timestamp_sec = int(timestamp) / 1e9
                        from datetime import datetime
                        timestamp = datetime.fromtimestamp(timestamp_sec)
                except:
                    pass

            # Format timestamp
            if hasattr(timestamp, 'strftime'):
                timestamp_str = timestamp.strftime('%H:%M:%S.%f')[:-3]
            elif timestamp:
                timestamp_str = str(timestamp)
            else:
                timestamp_str = 'N/A'

            # Extract service name - handle both direct and nested stream structure
            service_name = 'Unknown'
            if 'service_name' in entry:
                service_name = entry['service_name']
            elif 'stream' in entry and 'service_name' in entry['stream']:
                service_name = entry['stream']['service_name']

            # Extract message content
            message = ''
            if 'message' in entry:
                message = entry['message']
            elif 'values' in entry and entry['values'] and len(entry['values']) > 0:
                # For Loki format, message is in values[0][1]
                try:
                    message = entry['values'][0][1]
                except:
                    pass
            elif 'raw_content' in entry:
                message = entry['raw_content']

            if not message:
                continue

            # Extract method name and create formatted entry
            method_info = self._extract_method_info_from_message(message)

            if method_info:
                key_events.append({
                    'timestamp': timestamp_str,
                    'service': service_name,
                    'method': method_info,
                    'raw_message': message  # Keep raw message for debugging
                })

        return key_events

    def _extract_method_info_from_message(self, message: str) -> Optional[str]:
        """Extract method information from log message."""
        if not message:
            return None

        # Pattern 1: "Invocation Returned: com.package.Class.method Response:"
        match = re.search(r'Invocation Returned:\s*([^\s]+)(?:\s+Response)?', message)
        if match:
            method_info = match.group(1).strip()
            # Remove trailing "Response:" if it got captured
            if method_info.endswith('Response:'):
                method_info = method_info[:-9].strip()
            return method_info

        # Pattern 2: "Invoking : \nClass: com.package.Class \nMethod: methodName"
        # This handles multi-line format with actual newlines
        match = re.search(r'Invoking\s*:\s*\nClass:\s*([^\s\n]+)\s*\nMethod:\s*([^\s\n]+)', message)
        if match:
            class_name = match.group(1).strip()
            method_name = match.group(2).strip()
            return f"{class_name}.{method_name}"

        # Pattern 2b: Handle when it's all on one line or with different separators
        match = re.search(r'Class:\s*([^\s]+)\s+Method:\s*([^\s]+)', message)
        if match:
            class_name = match.group(1).strip()
            method_name = match.group(2).strip()
            return f"{class_name}.{method_name}"

        # Pattern 3: "Executed class.method in X milliseconds"
        match = re.search(r'Executed\s+([^\s]+)\s+in\s+\d+\s+milliseconds?', message)
        if match:
            return match.group(1).strip()

        # Pattern 4: Look for general class.method patterns
        match = re.search(r'(com\.[a-zA-Z0-9_.]+\.[A-Z][a-zA-Z0-9_]*\.[a-zA-Z][a-zA-Z0-9_]*)', message)
        if match:
            return match.group(1).strip()

        # Pattern 5: Look for proxy patterns
        match = re.search(r'(jdk\.proxy[0-9]*\.\$Proxy[0-9]+\.[a-zA-Z][a-zA-Z0-9_]*)', message)
        if match:
            return match.group(1).strip()

        # Pattern 6: Handle "REQUEST:" pattern for HTTP requests
        if 'REQUEST:' in message and 'PATH=' in message:
            match = re.search(r'PATH=([^\s,]+)', message)
            if match:
                path = match.group(1).strip()
                return f"HTTP GET {path}"

        # If no specific pattern found but message seems relevant, return a cleaned version
        if any(keyword in message.lower() for keyword in ['invok', 'execut', 'return', 'response', 'request']):
            # Clean up the message for display
            clean_msg = message.replace('\n', ' ').strip()
            # Remove extra spaces
            clean_msg = ' '.join(clean_msg.split())
            return clean_msg

        return None

    def _write_high_level_event_flow(self, file_handle, trace_entries: List[Dict[str, Any]]):
        """Write a formatted high-level event flow section."""
        f = file_handle

        # Extract key events
        key_events = self._extract_key_events(trace_entries)

        if not key_events:
            f.write("No key events found in trace.\n")
            return

        f.write("High-Level Event Flow:\n")
        f.write("-" * 120 + "\n")
        f.write("Time         | Service                      | Method/Operation\n")
        f.write("-" * 120 + "\n")

        for i, event in enumerate(key_events, 1):
            time_str = event['timestamp']
            service = event['service']
            method = event['method']

            # Format for alignment - truncate service name if too long
            time_col = f"{time_str:<12}"
            service_col = f"{service[:28]:<28}"  # Truncate to 28 chars if needed

            # For method, allow it to be longer since it's the last column
            method_col = method

            f.write(f"{time_col} | {service_col} | {method_col}\n")

        f.write("-" * 120 + "\n")
        f.write(f"Total Events: {len(key_events)}\n\n")

    def _classify_banking_event(self, message: str, method_name: str, service_name: str) -> tuple:
        """Classify banking system events and create detailed descriptions."""
        message_lower = message.lower()

        # Payment/Transaction related events
        if 'payment' in service_name.lower():
            if any(keyword in message_lower for keyword in ['mfs', 'transfer', 'payment']):
                if 'status' in message_lower and 'update' in message_lower:
                    return 'payment_status', f"Payment status update process - {method_name or 'Payment service'}"
                elif 'scheduler' in message_lower:
                    return 'payment_schedule', f"Payment scheduler invoked - {method_name or 'Scheduler'}"
                elif 'eligiblefor' in message_lower.replace(' ', ''):
                    return 'payment_check', f"Payment eligibility check - {method_name or 'Eligibility service'}"
                else:
                    return 'payment_process', f"Payment processing - {method_name or 'Payment operation'}"

        # Scheduler related events
        if 'scheduler' in service_name.lower() or 'scheduler' in message_lower:
            if 'findbyreference' in message_lower.replace(' ', ''):
                return 'scheduler_lookup', f"Scheduler configuration lookup - {method_name or 'Config service'}"
            elif 'invocation' in message_lower:
                return 'scheduler_invoke', f"Scheduler invocation - {method_name or 'Scheduler'}"
            elif 'cron' in message_lower:
                return 'scheduler_cron', f"Cron scheduler execution - {method_name or 'Cron service'}"
            else:
                return 'scheduler_process', f"Scheduler operation - {method_name or 'Scheduler service'}"

        # Database/Repository operations
        if any(keyword in message_lower for keyword in ['repository', 'database', 'findby', 'save', 'update']):
            if 'findby' in message_lower:
                return 'db_query', f"Database query operation - {method_name or 'Repository'}"
            elif any(keyword in message_lower for keyword in ['save', 'update', 'insert']):
                return 'db_write', f"Database write operation - {method_name or 'Repository'}"
            else:
                return 'db_operation', f"Database operation - {method_name or 'Database service'}"

        # Service invocation patterns
        if 'invoking' in message_lower:
            return 'service_invoke', f"Service invocation: {method_name or 'Service method'}"
        elif 'executed' in message_lower:
            # Extract execution time if present
            time_match = re.search(r'(\d+)\s*milliseconds?', message)
            time_info = f" ({time_match.group(1)}ms)" if time_match else ""
            return 'service_complete', f"Service execution completed: {method_name or 'Service method'}{time_info}"
        elif 'returned' in message_lower or 'response' in message_lower:
            return 'service_response', f"Service response: {method_name or 'Service method'}"

        # Error and exception handling
        if any(keyword in message_lower for keyword in ['error', 'exception', 'fail', 'timeout']):
            return 'error', f"Error occurred: {message[:80]}..."

        # Success and completion indicators
        if any(keyword in message_lower for keyword in ['success', 'complete', 'finished', 'done']):
            return 'success', f"Process completed successfully: {method_name or 'Operation'}"

        # Initialization and startup
        if any(keyword in message_lower for keyword in ['start', 'begin', 'init', 'create']):
            return 'init', f"Process initiated: {method_name or 'Service startup'}"

        # Consumer/Topic related (for message queues)
        if any(keyword in message_lower for keyword in ['consumer', 'topic', 'message', 'queue']):
            return 'messaging', f"Message processing: {method_name or 'Message consumer'}"

        # Default case - try to extract meaningful info
        if method_name:
            return 'operation', f"Operation: {method_name}"
        elif len(message) > 10:
            # Extract meaningful part of message
            clean_message = re.sub(r'\{.*?\}', '{...}', message)  # Replace JSON with {...}
            return 'activity', clean_message[:100] + ("..." if len(clean_message) > 100 else "")

        return 'unknown', "Unknown operation"