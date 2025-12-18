# agents/analyze_agent.py - Refactored version focusing on analysis generation

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from ollama import Client
import re, json
from datetime import datetime as dt

from app.config import settings
from app.services.llm_gateway.gateway import CachePolicy, CacheableValue, get_llm_cache_gateway
from .report_writer import ReportWriter

logger = logging.getLogger(__name__)


def _get_prompt_from_db(prompt_name: str, variables: Optional[Dict] = None) -> Optional[str]:
    """
    Helper to get prompt from database if feature flag is enabled.
    Returns None if not available or feature disabled.
    """
    if not settings.USE_DB_PROMPTS:
        return None
    try:
        from app.services.prompt_service import get_prompt_service
        prompt_service = get_prompt_service()
        result = prompt_service.render_prompt(prompt_name, variables)
        if result:
            logger.debug(f"Using database prompt for {prompt_name}")
        return result
    except Exception as e:
        logger.warning(f"Failed to get prompt '{prompt_name}' from database: {e}")
        return None


class AnalyzeAgent:
    """
    Enhanced VerifyAgent focused on analysis generation.
    Report writing functionality has been separated to ReportWriter class.
    """

    def __init__(self, client: Client, model: str, output_dir: str = "comprehensive_analysis"):
        self.client = client
        self.model = model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize the report writer
        self.report_writer = ReportWriter(output_dir, model)

        logger.info(f"VerifyAgent initialized with model: {model}, output directory: {self.output_dir}")

    def analyze_and_create_comprehensive_files(
            self,
            original_context: str,
            search_results: Dict,
            trace_data: Dict,
            parameters: Dict,
            output_prefix: str = None,
            cache_policy: Optional[CachePolicy] = None,
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
        overall_quality = self._assess_overall_quality(
            original_context, search_results, trace_data, parameters, cache_policy=cache_policy
        )

        # Step 2: Create comprehensive file for each trace
        created_files = []
        trace_analyses = {}

        for trace_id, comprehensive_trace_data in all_trace_data.items():
            logger.info(f"Creating comprehensive file for trace: {trace_id}")

            # Analyze this specific trace
            trace_analysis = self._analyze_single_trace(
                trace_id, comprehensive_trace_data, original_context, parameters, cache_policy=cache_policy
            )

            # Create comprehensive file using report writer
            relative_path = self.report_writer.create_comprehensive_trace_file(
                trace_id, trace_analysis, comprehensive_trace_data,
                original_context, parameters, overall_quality, output_prefix
            )

            abs_path = str(Path(relative_path).resolve())
            created_files.append(abs_path)
            trace_analyses[trace_id] = trace_analysis
            logger.info(f"✓ Created comprehensive file: {abs_path}")

        # Create master summary file using report writer
        master_summary_relative = self.report_writer.create_master_summary_file(
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

    def analyze_log_files(
            self,
            log_file_paths: List[str],
            dispute_text: str,
            search_params: Dict[str, Any] = None,
            cache_policy: Optional[CachePolicy] = None,
    ) -> Dict[str, Any]:
        """
        Analyze log files and generate individual trace reports plus a master summary.

        Args:
            log_file_paths: List of paths to log files to analyze
            dispute_text: The original customer dispute text
            search_params: Optional search parameters used

        Returns:
            Dict containing:
            - "individual_reports": List of paths to individual trace reports
            - "master_report": Path to master summary report
            - "analysis_summary": Summary statistics
        """
        if search_params is None:
            search_params = {}

        logger.info(f"Starting analysis of {len(log_file_paths)} log files")

        # 1) Parse all log files and extract entries
        all_entries = []
        for file_path in log_file_paths:
            try:
                entries = self._parse_log_file(file_path)
                all_entries.extend(entries)
                logger.info(f"Parsed {len(entries)} entries from {file_path}")
            except Exception as e:
                logger.error(f"Error parsing {file_path}: {e}")
                continue

        # 2) Sort entries chronologically and group by trace_id
        all_entries_sorted = sorted(all_entries, key=lambda e: e.get('timestamp') or dt.min)
        trace_groups = self._group_entries_by_trace(all_entries_sorted)

        logger.info(f"Found {len(trace_groups)} unique traces with {len(all_entries_sorted)} total entries")

        # 3) Generate individual trace reports
        individual_reports = []
        trace_analyses = {}

        for trace_id, trace_entries in trace_groups.items():
            try:
                # Generate analysis for this trace
                trace_analysis = self._analyze_single_trace_from_entries(
                    trace_id, trace_entries, dispute_text, search_params, cache_policy=cache_policy
                )
                trace_analyses[trace_id] = trace_analysis

                # Generate individual report using report writer
                report_path = self.report_writer.create_individual_trace_report(
                    trace_id, trace_entries, dispute_text, search_params, trace_analysis
                )
                individual_reports.append(report_path)

                logger.info(f"✓ Created report for trace {trace_id}: {report_path}")

            except Exception as e:
                logger.error(f"Error creating report for trace {trace_id}: {e}")
                continue

        # 4) Generate master summary report using report writer
        try:
            master_report_path = self.report_writer.create_master_analysis_summary(
                trace_groups, all_entries_sorted, dispute_text, search_params, trace_analyses
            )
            logger.info(f"✓ Created master summary: {master_report_path}")

        except Exception as e:
            logger.error(f"Error creating master summary: {e}")
            master_report_path = None

        # 5) Return results
        result = {
            "individual_reports": individual_reports,
            "master_report": master_report_path,
            "analysis_summary": {
                "total_traces": len(trace_groups),
                "total_entries": len(all_entries_sorted),
                "files_processed": len(log_file_paths),
                "reports_created": len(individual_reports)
            }
        }

        logger.info(f"Analysis complete: {len(individual_reports)} individual reports + 1 master report")
        return result

    def _analyze_single_trace(
            self,
            trace_id: str,
            trace_data: Dict,
            original_context: str,
            parameters: Dict,
            cache_policy: Optional[CachePolicy] = None,
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
        "request_summary": "<what the request was attempting to do or what was it about>",
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

        # Get system prompt from DB or use fallback
        system_prompt = _get_prompt_from_db("trace_analysis_system") or \
            "You are a senior banking systems analyst with expertise in transaction processing, log analysis, and dispute resolution. Analyze the provided log data thoroughly to understand exactly what happened during this transaction. Focus on technical details and evidence-based conclusions."

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]

        try:
            gateway = get_llm_cache_gateway()

            def compute() -> CacheableValue:
                response = self.client.chat(model=self.model, messages=messages)
                raw_response = response["message"]["content"].strip()
                analysis_local = self._safe_parse_json(raw_response, self._default_trace_analysis)
                return CacheableValue(value=analysis_local, cacheable=True)

            analysis, _diag = gateway.cached(
                cache_type="trace_analysis",
                model=self.model,
                messages=messages,
                options=None,
                default_ttl_seconds=14400,
                policy=cache_policy,
                compute=compute,
            )

            analysis = dict(analysis or {})
            analysis["trace_id"] = trace_id
            analysis["total_entries"] = trace_data.get("total_entries", 0)
            analysis["source_files_count"] = len(trace_data.get("source_files", []))
            analysis["log_sample_size"] = len(sample_messages)
            analysis["timeline_events_analyzed"] = len(timeline_steps)
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing trace {trace_id}: {e}")
            return self._default_trace_analysis(trace_id)

    def _analyze_single_trace_from_entries(
            self,
            trace_id: str,
            trace_entries: List[Dict[str, Any]],
            dispute_text: str,
            search_params: Dict[str, Any],
            cache_policy: Optional[CachePolicy] = None,
    ) -> Dict[str, Any]:
        """Generate AI analysis for a single trace from trace entries."""

        # Extract sample messages
        sample_messages = []
        for entry in trace_entries[:10]:
            message = entry.get('message', '') or entry.get('raw_content', '')
            if message and len(message.strip()) > 10:
                sample_messages.append(message[:200])

        prompt = f"""
You are a senior banking systems analyst investigating a customer dispute.

CUSTOMER DISPUTE: {dispute_text[:300]}

TRACE DETAILS:
- Trace ID: {trace_id}
- Total Log Entries: {len(trace_entries)}

SAMPLE LOG MESSAGES:
{chr(10).join(f"• {msg}" for msg in sample_messages[:8])}

Analyze this trace and provide your expert assessment in JSON format:

{{
    "relevance_score": <0-100>,
    "request_summary": "<what the request was attempting to do or what was it about>",
    "request_outcome": "<successful|failed|timeout|partial|unknown>",
    "key_finding": "<main conclusion about what happened>",
    "primary_issue": "<system_error|user_error|network_issue|timeout|validation_error|normal_flow|other>",
    "confidence_level": "<HIGH|MEDIUM|LOW>",
    "evidence_found": ["<specific evidence from logs>"],
    "timeline_summary": "<step-by-step summary of what happened>",
    "customer_claim_assessment": "<supported|contradicted|partially_supported|insufficient_evidence>",
    "root_cause_analysis": "<likely root cause based on logs>",
    "recommendation": "<specific next steps needed>"
}}
"""

        # Get system prompt from DB or use fallback
        entries_system_prompt = _get_prompt_from_db("entries_analysis_system") or \
            "You are a senior banking systems analyst. Provide thorough, evidence-based analysis."

        messages = [
            {"role": "system", "content": entries_system_prompt},
            {"role": "user", "content": prompt}
        ]

        try:
            gateway = get_llm_cache_gateway()

            def compute() -> CacheableValue:
                response = self.client.chat(model=self.model, messages=messages)
                raw_response = response["message"]["content"].strip()
                analysis_local = self._safe_parse_json(raw_response, self._default_trace_analysis)
                return CacheableValue(value=analysis_local, cacheable=True)

            analysis, _diag = gateway.cached(
                cache_type="trace_entries_analysis",
                model=self.model,
                messages=messages,
                options=None,
                default_ttl_seconds=14400,
                policy=cache_policy,
                compute=compute,
            )

            analysis = dict(analysis or {})
            analysis["trace_id"] = trace_id
            analysis["total_entries"] = len(trace_entries)
            return analysis

        except Exception as e:
            logger.error(f"Error analyzing trace {trace_id}: {e}")
            return self._default_trace_analysis(trace_id)

    def _assess_overall_quality(
        self,
        original_context: str,
        search_results: Dict,
        trace_data: Dict,
        parameters: Dict,
        cache_policy: Optional[CachePolicy] = None,
    ) -> Dict:
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

        # Get system prompt from DB or use fallback
        quality_system_prompt = _get_prompt_from_db("quality_assessment_system") or \
            "Banking analyst. JSON only."

        messages = [
            {"role": "system", "content": quality_system_prompt},
            {"role": "user", "content": prompt}
        ]

        try:
            gateway = get_llm_cache_gateway()

            def compute() -> CacheableValue:
                response = self.client.chat(model=self.model, messages=messages)
                raw_response = response["message"]["content"].strip()
                result_local = self._safe_parse_json(raw_response, self._default_quality_assessment)
                return CacheableValue(value=result_local, cacheable=True)

            result, _diag = gateway.cached(
                cache_type="quality_assessment",
                model=self.model,
                messages=messages,
                options=None,
                default_ttl_seconds=7200,
                policy=cache_policy,
                compute=compute,
            )
            return result

        except Exception as e:
            logger.error(f"Error in overall quality assessment: {e}")
            return self._default_quality_assessment()

    def _parse_log_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Parse a single log file and return list of log entries."""
        import json
        from datetime import datetime

        entries = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Check if this is Loki format
            if 'data' in data and 'result' in data['data']:
                results = data['data']['result']

                for result in results:
                    if 'stream' in result and 'values' in result:
                        stream_metadata = result['stream']
                        values = result['values']

                        for value_pair in values:
                            if len(value_pair) >= 2:
                                timestamp_ns = value_pair[0]
                                message = value_pair[1]

                                # Convert nanosecond timestamp to datetime
                                timestamp = None
                                try:
                                    if isinstance(timestamp_ns, str):
                                        timestamp_sec = int(timestamp_ns) / 1e9
                                        timestamp = datetime.fromtimestamp(timestamp_sec)
                                except:
                                    timestamp = timestamp_ns

                                # Create entry with both stream metadata and values
                                entry = {
                                    'timestamp': timestamp,
                                    'message': message,
                                    'service_name': stream_metadata.get('service_name', 'Unknown'),
                                    'severity_text': stream_metadata.get('severity_text', 'INFO'),
                                    'trace_id': stream_metadata.get('trace_id'),
                                    'span_id': stream_metadata.get('span_id'),
                                    'host_name': stream_metadata.get('host_name'),
                                    'service_namespace': stream_metadata.get('service_namespace'),
                                    # Store original structure for compatibility
                                    'stream': stream_metadata,
                                    'values': [value_pair],
                                    'raw_content': message
                                }

                                entries.append(entry)

            # If not Loki format, try other parsing methods
            else:
                # Fallback to existing parse_loki_json if available
                from app.tools.loki.loki_log_analyser import parse_loki_json
                entries = parse_loki_json([file_path])

        except Exception as e:
            logger.error(f"Error parsing log file {file_path}: {e}")

        return entries

    def _group_entries_by_trace(self, entries: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Group log entries by trace_id."""
        trace_groups = {}
        for entry in entries:
            trace_id = entry.get('trace_id')
            if trace_id:
                if trace_id not in trace_groups:
                    trace_groups[trace_id] = []
                trace_groups[trace_id].append(entry)
        return trace_groups

    def _safe_parse_json(self, raw: str, fallback_fn=None):
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
            elif fallback_fn:
                return fallback_fn
            else:
                return self._default_trace_analysis()

    def _default_trace_analysis(self, trace_id: str = None) -> Dict:
        """Default trace analysis structure."""
        return {
            "trace_id": trace_id or "unknown",
            "relevance_score": 50,
            "request_summary": "Analysis could not be completed",
            "transaction_outcome": "unknown",
            "key_finding": "Analysis could not be completed",
            "primary_issue": "insufficient_data",
            "confidence_level": "LOW",
            "evidence_found": ["Analysis processing error"],
            "critical_indicators": ["Analysis processing error"],
            "concerns": ["Unable to complete automated analysis"],
            "timeline_summary": "Timeline analysis not available",
            "customer_claim_assessment": "insufficient_evidence",
            "root_cause_analysis": "Analysis processing error",
            "recommendation": "Manual review required",
            "technical_details": "Analysis processing error"
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
