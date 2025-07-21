# agents/verify_agent.py - Enhanced version with combined output

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from ollama import Client
import re, json
from datetime import datetime as dt

logger = logging.getLogger(__name__)


class VerifyAgent:
    """
    Enhanced VerifyAgent that creates comprehensive files containing both
    verification analysis and complete log content for each trace.
    """

    def __init__(self, client: Client, model: str, output_dir: str = "comprehensive_analysis"):
        self.client = client
        self.model = model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"VerifyAgent initialized with model: {model}, output directory: {self.output_dir}")

    def analyze_and_create_comprehensive_files(
            self,
            original_context: str,
            search_results: Dict,
            trace_data: Dict,
            parameters: Dict,
            output_prefix: str = None
    ) -> Dict:
        """
        Create comprehensive files for each trace containing both analysis and full logs.

        Args:
            original_context: The original user query/context
            search_results: Results from log searching
            trace_data: Comprehensive trace data from all log files
            parameters: Extracted parameters from original context
            output_prefix: Custom prefix for output files

        Returns:
            Dictionary with analysis results and created file paths
        """
        logger.info("Creating comprehensive analysis files for each trace...")

        all_trace_data = trace_data.get('all_trace_data', {})
        if not all_trace_data:
            logger.warning("No trace data available for analysis")
            return self._create_empty_result()

        # Step 1: Perform overall quality assessment
        overall_quality = self._assess_overall_quality(original_context, search_results, trace_data, parameters)

        # Step 2: Create comprehensive file for each trace
        created_files = []
        trace_analyses = {}

        for trace_id, comprehensive_trace_data in all_trace_data.items():
            logger.info(f"Creating comprehensive file for trace: {trace_id}")

            # Analyze this specific trace
            trace_analysis = self._analyze_single_trace(
                trace_id, comprehensive_trace_data, original_context, parameters
            )

            # Create comprehensive file and resolve to absolute path
            relative_path = self._create_comprehensive_trace_file(
                trace_id, trace_analysis, comprehensive_trace_data,
                original_context, parameters, overall_quality, output_prefix
            )
            logger.info("Comprehensive file created: %s", relative_path)
            abs_path = str(Path(relative_path).resolve())
            logger.info("Found absolute path for comprehensive file: %s", abs_path)

            created_files.append(abs_path)
            trace_analyses[trace_id] = trace_analysis
            logger.info(f"✓ Created comprehensive file: {abs_path}")

            # Create master summary file and resolve absolute path
        master_summary_relative = self._create_master_summary_file(
            original_context, search_results, trace_analyses,
            overall_quality, parameters, created_files, output_prefix
        )
        master_summary_path = str(Path(master_summary_relative).resolve())

        results = {
            'analysis_timestamp': dt.now().isoformat(),
            'original_context': original_context,
            'parameters': parameters,
            'overall_quality_assessment': overall_quality,
            'trace_analyses': trace_analyses,
            'comprehensive_files_created': created_files,
            'master_summary_file': master_summary_path,
            'total_traces_analyzed': len(trace_analyses),
            'confidence_score': overall_quality.get('overall_confidence', 0),
            'metadata': {
                'total_files_searched': search_results.get('total_files', 0),
                'total_matches': search_results.get('total_matches', 0),
                'unique_traces': len(all_trace_data),
                'model_used': self.model
            }
        }

        logger.info(f"Comprehensive analysis completed for {len(created_files)} traces")
        logger.info(f"Master summary: {master_summary_path}")
        return results

    def _analyze_single_trace(
            self,
            trace_id: str,
            trace_data: Dict,
            original_context: str,
            parameters: Dict
    ) -> Dict:
        """Analyze a single trace for relevance and findings by inspecting actual log content."""

        # Extract key log messages and timeline for analysis
        log_entries = trace_data.get('log_entries', [])
        timeline = trace_data.get('timeline', [])

        # Get sample log messages for context
        sample_messages = []
        for entry in log_entries[:10]:  # First 10 entries
            message = entry.get('message', '')
            if message and len(message) > 20:  # Only meaningful messages
                sample_messages.append(message[:200])  # First 200 chars

        # Get timeline summary
        timeline_steps = []
        for step in timeline[:15]:  # First 15 timeline events
            operation = step.get('operation', 'Unknown')
            timestamp = step.get('timestamp', 'N/A')
            level = step.get('level', 'INFO')
            timeline_steps.append(f"{timestamp} [{level}] {operation}")

        prompt = f"""
    You are a senior banking systems analyst investigating a transaction dispute. Analyze this trace by examining the actual log content to understand what happened during this transaction request.

    ORIGINAL DISPUTE: {original_context[:300]}

    SEARCH PARAMETERS:
    - Time Frame: {parameters.get('time_frame', 'N/A')}
    - Account Numbers: {parameters.get('query_keys', [])}
    - Domain/System: {parameters.get('domain', 'N/A')}

    TRACE ANALYSIS DATA:
    - Trace ID: {trace_id}
    - Total Log Entries: {trace_data.get('total_entries', 0)}
    - Source Log Files: {len(trace_data.get('source_files', []))}
    - Timeline Events: {len(timeline)}

    ACTUAL LOG MESSAGES (Sample):
    {chr(10).join(f"• {msg}" for msg in sample_messages[:8])}

    CHRONOLOGICAL TIMELINE:
    {chr(10).join(f"  {step}" for step in timeline_steps[:12])}

    DEEP ANALYSIS REQUIRED:
    Based on the actual log content above, analyze what really happened in this transaction request:

    1. What was the transaction attempting to do?
    2. Did it complete successfully or fail? At what stage?
    3. What specific errors, warnings, or issues occurred?
    4. What was the final outcome/status?
    5. How does this relate to the customer's complaint?
    6. What evidence supports or contradicts the customer's claim?

    Provide detailed forensic analysis in JSON format:

    {{
        "relevance_score": <0-100>,
        "transaction_summary": "<what the transaction was attempting to do>",
        "transaction_outcome": "<successful|failed|timeout|partial|unknown>",
        "failure_point": "<where it failed if applicable>",
        "key_finding": "<one sentence conclusion about what happened>",
        "primary_issue": "<system_error|user_error|processing_delay|insufficient_data|normal_flow|network_issue|validation_error|timeout>",
        "confidence_level": "<HIGH|MEDIUM|LOW>",
        "evidence_found": ["<specific evidence from logs>", "<evidence 2>"],
        "critical_indicators": ["<technical indicators>", "<indicator 2>"],
        "error_messages": ["<actual error messages found>"],
        "timeline_summary": "<step-by-step what happened>",
        "customer_claim_assessment": "<supported|contradicted|partially_supported|insufficient_evidence>",
        "root_cause_analysis": "<likely root cause based on logs>",
        "recommendation": "<specific next action needed>",
        "technical_details": "<technical findings for engineers>"
    }}
    """

        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior banking systems analyst with expertise in transaction processing, log analysis, and dispute resolution. Analyze the provided log data thoroughly to understand exactly what happened during this transaction. Focus on technical details and evidence-based conclusions."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            raw_response = response["message"]["content"].strip()
            analysis = self._safe_parse_json(raw_response, self._default_trace_analysis)

            # Add computed fields
            analysis['trace_id'] = trace_id
            analysis['total_entries'] = trace_data.get('total_entries', 0)
            analysis['source_files_count'] = len(trace_data.get('source_files', []))
            analysis['log_sample_size'] = len(sample_messages)
            analysis['timeline_events_analyzed'] = len(timeline_steps)

            return analysis

        except Exception as e:
            logger.error(f"Error analyzing trace {trace_id}: {e}")
            return self._default_trace_analysis(trace_id)

    def _create_comprehensive_trace_file(
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

            return str(file_path)

        except Exception as e:
            logger.error(f"Error creating comprehensive file for trace {trace_id}: {e}")
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
        f.write(f"Analysis Model: {self.model}\n")
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

    def _create_master_summary_file(
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

            logger.info(f"Master summary created: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Error creating master summary: {e}")
            raise

    # Helper methods (keeping existing ones and adding new ones)

    def _assess_overall_quality(self, original_context: str, search_results: Dict, trace_data: Dict,
                                parameters: Dict) -> Dict:
        """Assess overall quality of the search and analysis."""

        prompt = f"""
Rate overall log search quality for banking dispute. JSON only.

CONTEXT: {original_context[:150]}
RESULTS: {search_results.get('total_files', 0)} files, {search_results.get('total_matches', 0)} matches, {len(trace_data.get('all_trace_data', {}))} traces

Rate 0-100 for:
- COMPLETENESS: Sufficient data to understand issue?
- RELEVANCE: Data relates to the dispute?
- COVERAGE: Transaction flow adequately covered?

JSON format:
{{
    "completeness_score": <number>,
    "relevance_score": <number>,
    "coverage_score": <number>,
    "overall_confidence": <average>,
    "status": "<one line assessment>",
    "key_gaps": ["<gap1>", "<gap2>"]
}}
"""

        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Banking analyst. JSON only."},
                    {"role": "user", "content": prompt}
                ]
            )

            raw_response = response["message"]["content"].strip()
            return self._safe_parse_json(raw_response, self._default_quality_assessment)

        except Exception as e:
            logger.error(f"Error in overall quality assessment: {e}")
            return self._default_quality_assessment()

    def _safe_parse_json(self, raw: str, fallback_fn):
        """Parse JSON safely with fallback."""
        text = raw.strip()

        # Remove thinking tags if present
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # Extract JSON block
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            text = match.group(0)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            if callable(fallback_fn):
                return fallback_fn()
            else:
                return fallback_fn

    def _default_trace_analysis(self, trace_id: str = None) -> Dict:
        """Default trace analysis structure."""
        return {
            "trace_id": trace_id or "unknown",
            "relevance_score": 50,
            "key_finding": "Analysis could not be completed",
            "primary_issue": "insufficient_data",
            "confidence_level": "LOW",
            "critical_indicators": ["Analysis processing error"],
            "concerns": ["Unable to complete automated analysis"],
            "timeline_summary": "Timeline analysis not available",
            "recommendation": "Manual review required"
        }

    def _default_quality_assessment(self) -> Dict:
        """Default quality assessment structure."""
        return {
            "completeness_score": 50,
            "relevance_score": 50,
            "coverage_score": 50,
            "overall_confidence": 50,
            "status": "Default assessment applied due to processing error",
            "key_gaps": ["Assessment processing error"]
        }

    def _create_empty_result(self) -> Dict:
        """Create empty result structure when no data is available."""
        return {
            'analysis_timestamp': dt.now().isoformat(),
            'comprehensive_files_created': [],
            'master_summary_file': None,
            'total_traces_analyzed': 0,
            'confidence_score': 0,
            'message': 'No trace data available for analysis'
        }

    def generate_comprehensive_report(
        self,
        trace_ids: List[str],
        entries: List[Dict[str, Any]],
        dispute_text: str,
        search_params: Dict[str, Any],
        search_results: Dict[str, Any],
        output_path: str,
        max_traces: Optional[int] = None
    ) -> str:
        """
        Write a comprehensive report that includes:
          1) an overall quality assessment from the AI,
          2) per-trace deep analyses from the AI,
          3) the full chronological log timeline.

        Parameters:
        - trace_ids: all IDs we investigated
        - entries: flat list of log-entry dicts (can mix multiple trace_ids)
        - dispute_text: original user text
        - search_params: dict of parameters used for searching
        - search_results: dict of raw search results (e.g., total files, matches)
        - output_path: where to write the final report
        - max_traces: if set, limits how many trace_ids to analyze
        """
        # 1) Optionally cap the number of traces
        if max_traces is not None:
            trace_ids = trace_ids[:max_traces]

        # 2) Sort entries by timestamp (None => earliest)
        entries_sorted = sorted(entries, key=lambda e: e.get('timestamp') or dt.min)

        # 3) Overall AI quality assessment
        overall_quality = self._assess_overall_quality(
            original_context=dispute_text,
            search_results=search_results,
            trace_data={
                "all_trace_data": {
                    tid: {
                        "log_entries": [e for e in entries if e["trace_id"] == tid],
                        "timeline": [],
                        "source_files": []
                    }
                    for tid in trace_ids
                }
            },
            parameters=search_params
        )

        # 4) Per‑trace AI analyses
        trace_analyses: Dict[str, Dict[str, Any]] = {}
        for tid in trace_ids:
            trace_data = {
                "log_entries": [e for e in entries if e["trace_id"] == tid],
                "timeline": [],
                "source_files": []
            }
            trace_analyses[tid] = self._analyze_single_trace(
                trace_id=tid,
                trace_data=trace_data,
                original_context=dispute_text,
                parameters=search_params
            )

        # 5) Write the combined report
        gen_time = dt.now().strftime("%Y-%m-%d %H:%M:%S")
        ids_line = ", ".join(trace_ids)

        with open(output_path, 'w', encoding='utf-8') as out:
            # HEADER
            out.write("COMPREHENSIVE BANKING LOG ANALYSIS\n")
            out.write("=" * 60 + "\n")
            out.write(f"Generated:    {gen_time}\n")
            out.write(f"Trace IDs:    {ids_line}\n")
            out.write(f"Analysis LLM: {self.model}\n")
            out.write("=" * 60 + "\n\n")

            # EXECUTIVE SUMMARY (AI QUALITY ASSESSMENT)
            out.write("EXECUTIVE SUMMARY (AI QUALITY ASSESSMENT)\n")
            out.write("-" * 40 + "\n")
            for k, v in overall_quality.items():
                out.write(f"{k.replace('_', ' ').title():20}: {v}\n")
            out.write(f"{'Total Entries':20}: {len(entries_sorted)}\n\n")

            # ORIGINAL DISPUTE & SEARCH PARAMETERS
            out.write("ORIGINAL DISPUTE\n")
            out.write("-" * 20 + "\n")
            out.write(dispute_text.strip() + "\n\n")

            out.write("SEARCH PARAMETERS\n")
            out.write("-" * 20 + "\n")
            for k, v in search_params.items():
                out.write(f"{k:20}: {v}\n")
            out.write("\n")

            # PER‑TRACE AI ANALYSIS
            out.write("PER‑TRACE AI ANALYSIS\n")
            out.write("-" * 20 + "\n")
            for tid, analysis in trace_analyses.items():
                out.write(f"Trace ID {tid} Analysis JSON:\n")
                out.write(json.dumps(analysis, indent=2) + "\n\n")

            # TRANSACTION TIMELINE (ALL LOGS)
            out.write("TRANSACTION TIMELINE (ALL LOGS)\n")
            out.write("-" * 40 + "\n")
            for i, e in enumerate(entries_sorted, 1):
                ts = e["timestamp"].strftime("%Y-%m-%d/%H:%M:%S") if e.get("timestamp") else "N/A"
                lvl = e.get("level", "N/A")
                svc = e.get("service_name", "N/A")
                msg = (e.get("message") or "").replace("\n", " ")[:80]
                out.write(f"{i:3}. {ts} | {lvl:5} | {svc:20} | {msg}...\n")
            out.write("\n")

        return output_path
