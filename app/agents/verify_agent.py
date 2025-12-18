# agents/verify_agent.py

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from ollama import Client
import re
import json
import csv
from datetime import datetime as dt
from dataclasses import dataclass
from enum import Enum
import os
from app.config import settings
from app.services.llm_gateway.gateway import CachePolicy, CacheableValue, get_llm_cache_gateway

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


class RelevanceLevel(Enum):
    """Enumeration for relevance levels"""
    HIGHLY_RELEVANT = "highly_relevant"
    RELEVANT = "relevant"
    POTENTIALLY_RELEVANT = "potentially_relevant"
    NOT_RELEVANT = "not_relevant"
    IGNORED = "ignored"
    UNKNOWN = "unknown"


@dataclass
class ContextRule:
    """Data class for context rules"""
    id: str
    context: str
    important: str
    ignore: str
    description: Optional[str] = None


@dataclass
class RelevanceResult:
    """Data class for relevance analysis results"""
    file_path: str
    trace_id: str
    relevance_level: RelevanceLevel
    relevance_score: float  # 0-100
    confidence_score: float  # 0-100
    matching_elements: List[str]
    non_matching_elements: List[str]
    key_findings: List[str]
    recommendation: str
    analysis_timestamp: str
    processing_time_ms: float
    applied_rules: List[str]  # Which context rules were applied
    ignored_patterns: List[str]  # Patterns that caused ignoring


class RAGContextManager:
    """
    Manages RAG context rules from file
    """

    def __init__(self, context_file_path: str = "context_rules.csv"):
        self.context_file_path = Path(context_file_path)
        self.rules: List[ContextRule] = []
        self.load_context_rules()

    def load_context_rules(self):
        """Load context rules from CSV file"""
        if not self.context_file_path.exists():
            self.create_default_context_file()

        try:
            with open(self.context_file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.rules = []
                for row in reader:
                    rule = ContextRule(
                        id=row['id'].strip(),
                        context=row['context'].strip(),
                        important=row['important'].strip(),
                        ignore=row['ignore'].strip(),
                        description=row.get('description', '').strip() or None
                    )
                    self.rules.append(rule)

            logger.info(f"Loaded {len(self.rules)} context rules from {self.context_file_path}")

        except Exception as e:
            logger.error(f"Error loading context rules: {e}")
            self.rules = []

    def create_default_context_file(self):
        """Create a default context rules file"""
        default_rules = [
            {
                'id': '1',
                'context': 'mfs',
                'important': 'processPayment,transferMoney,balanceInquiry',
                'ignore': 'MFS_TRANSFER_STATUS_UPDATE_SCHEDULER_INVOCATION_TOPIC,HEARTBEAT,HEALTH_CHECK',
                'description': 'MFS payment processing - ignore scheduled status updates and health checks'
            },
            {
                'id': '2',
                'context': 'transactions',
                'important': 'transaction_created,payment_processed,amount,merchant',
                'ignore': 'session_cleanup,cache_refresh,log_rotation',
                'description': 'Transaction processing - focus on actual transactions, ignore maintenance'
            },
            {
                'id': '3',
                'context': 'bkash',
                'important': 'bkash_payment,mobile_wallet,OTP_verification',
                'ignore': 'bkash_heartbeat,connection_pool_stats',
                'description': 'bKash payments - ignore connection maintenance'
            }
        ]

        try:
            with open(self.context_file_path, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['id', 'context', 'important', 'ignore', 'description']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(default_rules)

            logger.info(f"Created default context file: {self.context_file_path}")

        except Exception as e:
            logger.error(f"Error creating default context file: {e}")

    def get_relevant_rules(self, domain: str, query_keys: List[str]) -> List[ContextRule]:
        """Get rules relevant to the current query"""
        relevant_rules = []

        for rule in self.rules:
            # Check if rule context matches domain or any query keys
            if (rule.context.lower() == domain.lower() or
                    any(key.lower() in rule.context.lower() for key in query_keys) or
                    any(rule.context.lower() in key.lower() for key in query_keys)):
                relevant_rules.append(rule)

        return relevant_rules

    def should_ignore_trace(self, trace_content: str, relevant_rules: List[ContextRule]) -> Tuple[bool, List[str]]:
        """
        Check if trace should be ignored based on rules
        Returns: (should_ignore, list_of_matching_ignore_patterns)
        """
        ignore_patterns = []

        for rule in relevant_rules:
            if rule.ignore:
                ignore_terms = [term.strip() for term in rule.ignore.split(',') if term.strip()]

                for term in ignore_terms:
                    # Check if this ignore pattern appears in trace
                    if re.search(re.escape(term), trace_content, re.IGNORECASE):
                        ignore_patterns.append(f"{rule.context}:{term}")

                        # Check if this is the ONLY significant activity in the trace
                        # (simple heuristic: if ignore pattern appears frequently relative to total content)
                        ignore_occurrences = len(re.findall(re.escape(term), trace_content, re.IGNORECASE))
                        total_lines = len(trace_content.split('\n'))

                        if ignore_occurrences > 0 and ignore_occurrences >= (total_lines * 0.3):
                            return True, ignore_patterns

        return False, ignore_patterns

    def get_important_patterns(self, relevant_rules: List[ContextRule]) -> List[str]:
        """Get list of important patterns from relevant rules"""
        important_patterns = []

        for rule in relevant_rules:
            if rule.important:
                terms = [term.strip() for term in rule.important.split(',') if term.strip()]
                important_patterns.extend([f"{rule.context}:{term}" for term in terms])

        return important_patterns


class RelevanceAnalyzerAgent:
    """
    Agent responsible for analyzing request traces and determining their relevance
    to the original user query/text based on extracted parameters.
    Enhanced with RAG-based context rules.
    """

    def __init__(self, client: Client, model: str, output_dir: str = "relevance_analysis",
                 context_file: str = "context_rules.csv"):
        self.client = client
        self.model = model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize RAG context manager
        self.rag_manager = RAGContextManager(context_file)

        # Define relevance thresholds
        self.HIGHLY_RELEVANT_THRESHOLD = 80
        self.RELEVANT_THRESHOLD = 60
        self.POTENTIALLY_RELEVANT_THRESHOLD = 40

        logger.info(f"RelevanceAnalyzerAgent initialized with model: {model}")
        logger.info(f"RAG context rules loaded: {len(self.rag_manager.rules)}")

    def analyze_batch_relevance(
            self,
            original_text: str,
            parameters: Dict[str, Any],
            trace_files: List[str],
            batch_size: int = 10,
            cache_policy: Optional[CachePolicy] = None,
    ) -> Dict[str, Any]:
        """
        Analyze relevance of multiple trace files in batches.
        Enhanced with RAG context filtering.
        """
        logger.info(f"Starting batch relevance analysis for {len(trace_files)} files")
        print(f"Starting batch relevance analysis for {len(trace_files)} files")

        # Get relevant context rules for this query
        domain = parameters.get('domain', '')
        query_keys = parameters.get('query_keys', [])
        relevant_rules = self.rag_manager.get_relevant_rules(domain, query_keys)

        logger.info(f"Found {len(relevant_rules)} relevant context rules")
        print(f"Found {len(relevant_rules)} relevant context rules: {[r.context for r in relevant_rules]}")

        all_results = []
        highly_relevant_files = []
        relevant_files = []
        potentially_relevant_files = []
        not_relevant_files = []
        ignored_files = []

        start_time = dt.now()

        # Process files in batches
        for i in range(0, len(trace_files), batch_size):
            batch = trace_files[i:i + batch_size]
            batch_results = []

            for file_path in batch:
                try:
                    result = self.analyze_single_file_relevance(
                        original_text, parameters, file_path, relevant_rules, cache_policy=cache_policy
                    )
                    batch_results.append(result)

                    # Categorize based on relevance level
                    if result.relevance_level == RelevanceLevel.HIGHLY_RELEVANT:
                        highly_relevant_files.append(result)
                    elif result.relevance_level == RelevanceLevel.RELEVANT:
                        relevant_files.append(result)
                    elif result.relevance_level == RelevanceLevel.POTENTIALLY_RELEVANT:
                        potentially_relevant_files.append(result)
                    elif result.relevance_level == RelevanceLevel.IGNORED:
                        ignored_files.append(result)
                    else:
                        not_relevant_files.append(result)

                except Exception as e:
                    logger.error(f"Error analyzing file {file_path}: {e}")
                    print(f"Error analyzing file {file_path}: {e}")
                    continue

            all_results.extend(batch_results)
            logger.info(f"Processed batch {i // batch_size + 1}/{(len(trace_files) + batch_size - 1) // batch_size}")
            print(f"Processed batch {i // batch_size + 1}/{(len(trace_files) + batch_size - 1) // batch_size}")

        end_time = dt.now()
        processing_time = (end_time - start_time).total_seconds()

        # Generate summary report
        summary_report = self._generate_summary_report(
            original_text,
            parameters,
            all_results,
            highly_relevant_files,
            relevant_files,
            potentially_relevant_files,
            not_relevant_files,
            ignored_files,
            processing_time,
            relevant_rules
        )
        print(summary_report)

        return {
            "summary": summary_report,
            "detailed_results": all_results,
            "highly_relevant": [r.file_path for r in highly_relevant_files],
            "relevant": [r.file_path for r in relevant_files],
            "potentially_relevant": [r.file_path for r in potentially_relevant_files],
            "not_relevant": [r.file_path for r in not_relevant_files],
            "ignored": [r.file_path for r in ignored_files],
            "context_rules_applied": [r.context for r in relevant_rules],
            "statistics": {
                "total_files": len(trace_files),
                "processed_files": len(all_results),
                "highly_relevant_count": len(highly_relevant_files),
                "relevant_count": len(relevant_files),
                "potentially_relevant_count": len(potentially_relevant_files),
                "not_relevant_count": len(not_relevant_files),
                "ignored_count": len(ignored_files),
                "processing_time_seconds": processing_time
            }
        }

    def analyze_single_file_relevance(
            self,
            original_text: str,
            parameters: Dict[str, Any],
            file_path: str,
            relevant_rules: List[ContextRule] = None,
            cache_policy: Optional[CachePolicy] = None,
    ) -> RelevanceResult:
        """
        Analyze relevance of a single trace file.
        Enhanced with RAG context filtering.
        """
        start_time = dt.now()
        logger.info(f"Analyzing relevance for file: {file_path}")

        # Read and parse the trace file
        trace_content = self._read_trace_file(file_path)
        if not trace_content:
            return self._create_error_result(file_path, "Failed to read file")

        # Check RAG rules for ignoring
        applied_rules = []
        ignored_patterns = []

        if relevant_rules:
            should_ignore, ignore_patterns = self.rag_manager.should_ignore_trace(trace_content, relevant_rules)
            ignored_patterns = ignore_patterns
            applied_rules = [r.id for r in relevant_rules]

            if should_ignore:
                end_time = dt.now()
                processing_time_ms = (end_time - start_time).total_seconds() * 1000

                return RelevanceResult(
                    file_path=file_path,
                    trace_id=self._extract_trace_id(trace_content),
                    relevance_level=RelevanceLevel.IGNORED,
                    relevance_score=0,
                    confidence_score=95,
                    matching_elements=[],
                    non_matching_elements=ignored_patterns,
                    key_findings=[f"Ignored due to patterns: {', '.join(ignored_patterns)}"],
                    recommendation="IGNORE - Contains only maintenance/scheduled activities",
                    analysis_timestamp=dt.now().isoformat(),
                    processing_time_ms=processing_time_ms,
                    applied_rules=applied_rules,
                    ignored_patterns=ignored_patterns
                )

        # Extract key information from trace
        trace_info = self._extract_trace_info(trace_content)

        # Perform relevance analysis with RAG context
        analysis = self._analyze_relevance_with_rag(
            original_text,
            parameters,
            trace_info,
            trace_content,
            relevant_rules,
            cache_policy=cache_policy,
        )

        # Calculate processing time
        end_time = dt.now()
        processing_time_ms = (end_time - start_time).total_seconds() * 1000

        # Create result object
        result = RelevanceResult(
            file_path=file_path,
            trace_id=trace_info.get('trace_id', 'unknown'),
            relevance_level=self._determine_relevance_level(analysis['relevance_score']),
            relevance_score=analysis['relevance_score'],
            confidence_score=analysis['confidence_score'],
            matching_elements=analysis['matching_elements'],
            non_matching_elements=analysis['non_matching_elements'],
            key_findings=analysis['key_findings'],
            recommendation=analysis['recommendation'],
            analysis_timestamp=dt.now().isoformat(),
            processing_time_ms=processing_time_ms,
            applied_rules=applied_rules,
            ignored_patterns=ignored_patterns
        )

        logger.info(
            f"Completed analysis for {file_path}: {result.relevance_level.value} (score: {result.relevance_score})")
        return result

    def _analyze_relevance_with_rag(
            self,
            original_text: str,
            parameters: Dict[str, Any],
            trace_info: Dict[str, Any],
            full_content: str,
            relevant_rules: List[ContextRule] = None,
            cache_policy: Optional[CachePolicy] = None,
    ) -> Dict[str, Any]:
        """
        Core relevance analysis using LLM enhanced with RAG context.
        """
        # Extract relevant sections from trace
        log_samples = trace_info.get('log_samples', [])
        timeline_summary = trace_info.get('timeline_summary', '')
        service_names = trace_info.get('service_names', [])
        operations = trace_info.get('operations', [])

        # Build RAG context
        rag_context = ""
        if relevant_rules:
            important_patterns = self.rag_manager.get_important_patterns(relevant_rules)

            rag_context = f"""
CONTEXT RULES APPLIED:
{chr(10).join(f"• Rule {rule.id} ({rule.context}): Important={rule.important}, Ignore={rule.ignore}" for rule in relevant_rules)}

IMPORTANT PATTERNS TO LOOK FOR: {', '.join(important_patterns)}

PATTERNS ALREADY FILTERED OUT: {', '.join([f"{rule.context}:{rule.ignore}" for rule in relevant_rules if rule.ignore])}
"""

        prompt = f"""
You are an expert system analyst determining if a request trace is relevant to a user's query.
You have access to context rules that help identify what's important vs what should be ignored.

ORIGINAL USER QUERY: {original_text}

EXTRACTED PARAMETERS:
- Domain: {parameters.get('domain', 'N/A')}
- Query Keys: {parameters.get('query_keys', [])}
- Time Frame: {parameters.get('time_frame', 'N/A')}
- Additional Parameters: {json.dumps({k: v for k, v in parameters.items() if k not in ['domain', 'query_keys', 'time_frame']}, indent=2)}

{rag_context}

 TRACE INFORMATION:
 - Trace ID: {trace_info.get('trace_id', 'unknown')}
 - Total Log Entries: {trace_info.get('total_entries', 0)}
 - Services Involved: {', '.join(service_names[:5])}
 - Key Operations: {', '.join(operations[:10])}

SAMPLE LOG MESSAGES:
{chr(10).join(f"• {msg}" for msg in log_samples[:10])}

TIMELINE SUMMARY:
{timeline_summary}

ANALYSIS REQUIRED:
Determine if this trace is relevant to the user's query by analyzing:
1. Does the trace contain operations related to the query domain ({parameters.get('domain', 'N/A')})?
2. Do the log messages contain the query keys ({parameters.get('query_keys', [])})?
3. Does the timestamp match the requested time frame ({parameters.get('time_frame', 'N/A')})?
4. Are there any operations or data that directly address the user's question?
5. Consider the IMPORTANT PATTERNS defined in the context rules
6. Even if not directly matching, could this trace provide useful context?

IMPORTANT: Use the context rules to boost relevance scores for traces containing important patterns
and to understand what activities are just maintenance/noise.

Provide analysis in JSON format:
{{
    "relevance_score": <0-100>,
    "confidence_score": <0-100>,
    "matching_elements": ["<specific elements that match the query>"],
    "non_matching_elements": ["<elements that don't match>"],
    "key_findings": ["<important discoveries about relevance>"],
    "domain_match": <true/false>,
    "time_match": <true/false>,
    "keyword_matches": ["<specific keyword matches found>"],
    "important_pattern_matches": ["<matches from RAG important patterns>"],
    "recommendation": "<INCLUDE|EXCLUDE|REVIEW - with brief explanation>",
    "reasoning": "<detailed explanation of relevance determination>"
}}
"""

        # Get system prompt from DB or use fallback
        relevance_system_prompt = _get_prompt_from_db("relevance_analysis_system") or \
            "You are an expert at analyzing system logs and determining relevance to user queries. Use provided context rules to make better relevance decisions. Be precise and thorough in your analysis."

        messages = [
            {"role": "system", "content": relevance_system_prompt},
            {"role": "user", "content": prompt}
        ]

        try:
            gateway = get_llm_cache_gateway()

            def compute() -> CacheableValue:
                response = self.client.chat(model=self.model, messages=messages)
                raw_response = response["message"]["content"].strip()
                analysis_local = self._safe_parse_json(raw_response)
                analysis_local = self._validate_analysis_result(analysis_local)
                return CacheableValue(value=analysis_local, cacheable=True)

            analysis, _diag = gateway.cached(
                cache_type="relevance_analysis",
                model=self.model,
                messages=messages,
                options=None,
                default_ttl_seconds=14400,
                policy=cache_policy,
                compute=compute,
            )
            return self._validate_analysis_result(analysis)

        except Exception as e:
            logger.error(f"Error in relevance analysis: {e}")
            return self._default_analysis_result()

    def _extract_trace_id(self, content: str) -> str:
        """Extract trace ID from content"""
        trace_match = re.search(r'Trace ID:\s*([a-f0-9]+)', content)
        return trace_match.group(1) if trace_match else 'unknown'

    def _extract_trace_info(self, content: str) -> Dict[str, Any]:
        """
        Extract key information from trace file content.
        """
        info = {
            'trace_id': 'unknown',
            'timestamp': None,
            'total_entries': 0,
            'service_names': [],
            'operations': [],
            'log_samples': [],
            'timeline_summary': '',
            'has_errors': False,
            'error_messages': []
        }

        try:
            # Extract trace ID
            trace_match = re.search(r'Trace ID:\s*([a-f0-9]+)', content)
            if trace_match:
                info['trace_id'] = trace_match.group(1)

            # Extract timestamp
            timestamp_match = re.search(r'Generated:\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2})', content)
            if timestamp_match:
                info['timestamp'] = timestamp_match.group(1)

            # Extract total entries
            entries_match = re.search(r'Total Log Entries:\s*(\d+)', content)
            if entries_match:
                info['total_entries'] = int(entries_match.group(1))

            # Extract service names
            service_matches = re.findall(r'Service:\s*([^\n]+)', content)
            info['service_names'] = list(set(service_matches))

            # Extract operations/methods
            method_matches = re.findall(r'Method:\s*([^\n]+)', content)
            operation_matches = re.findall(r'Method/Operation[:\s]*([^\n]+)', content)
            info['operations'] = list(set(method_matches + operation_matches))

            # Extract log samples
            log_content_matches = re.findall(r'Log Content:\s*-+\s*([^-]+?)(?=Raw Values:|LOG ENTRY|$)', content,
                                             re.DOTALL)
            info['log_samples'] = [log.strip() for log in log_content_matches if log.strip()][:20]

            # Extract timeline summary
            timeline_match = re.search(r'Timeline Summary:\s*([^\n]+)', content)
            if timeline_match:
                info['timeline_summary'] = timeline_match.group(1)

            # Check for errors
            error_patterns = [
                r'Level:\s*ERROR',
                r'error',
                r'exception',
                r'failed',
                r'failure'
            ]
            for pattern in error_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    info['has_errors'] = True
                    break

            # Extract error messages
            error_matches = re.findall(r'(?:error|exception)[:\s]*([^\n]+)', content, re.IGNORECASE)
            info['error_messages'] = list(set(error_matches))[:10]

        except Exception as e:
            logger.error(f"Error extracting trace info: {e}")

        return info

    def _determine_relevance_level(self, score: float) -> RelevanceLevel:
        """
        Determine relevance level based on score.
        """
        if score >= self.HIGHLY_RELEVANT_THRESHOLD:
            return RelevanceLevel.HIGHLY_RELEVANT
        elif score >= self.RELEVANT_THRESHOLD:
            return RelevanceLevel.RELEVANT
        elif score >= self.POTENTIALLY_RELEVANT_THRESHOLD:
            return RelevanceLevel.POTENTIALLY_RELEVANT
        else:
            return RelevanceLevel.NOT_RELEVANT

    def _read_trace_file(self, file_path: str) -> Optional[str]:
        """
        Read content from trace file.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file {file_path}: {e}")
            return None

    def _generate_summary_report(
            self,
            original_text: str,
            parameters: Dict[str, Any],
            all_results: List[RelevanceResult],
            highly_relevant: List[RelevanceResult],
            relevant: List[RelevanceResult],
            potentially_relevant: List[RelevanceResult],
            not_relevant: List[RelevanceResult],
            ignored: List[RelevanceResult],
            processing_time: float,
            applied_rules: List[ContextRule]
    ) -> Dict[str, Any]:
        """
        Generate a summary report of the relevance analysis.
        Enhanced with RAG context information.
        """
        # Calculate statistics
        analyzed_results = [r for r in all_results if r.relevance_level != RelevanceLevel.IGNORED]
        avg_relevance_score = sum(r.relevance_score for r in analyzed_results) / len(
            analyzed_results) if analyzed_results else 0
        avg_confidence_score = sum(r.confidence_score for r in analyzed_results) / len(
            analyzed_results) if analyzed_results else 0

        # Find most common matching elements
        all_matching_elements = []
        for result in all_results:
            all_matching_elements.extend(result.matching_elements)

        matching_element_counts = {}
        for element in all_matching_elements:
            matching_element_counts[element] = matching_element_counts.get(element, 0) + 1

        top_matching_elements = sorted(
            matching_element_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return {
            "analysis_timestamp": dt.now().isoformat(),
            "original_query": original_text,
            "search_parameters": parameters,
            "applied_context_rules": [
                {
                    "id": rule.id,
                    "context": rule.context,
                    "important": rule.important,
                    "ignore": rule.ignore,
                    "description": rule.description
                }
                for rule in applied_rules
            ],
            "summary_statistics": {
                "total_files_analyzed": len(all_results),
                "highly_relevant_count": len(highly_relevant),
                "relevant_count": len(relevant),
                "potentially_relevant_count": len(potentially_relevant),
                "not_relevant_count": len(not_relevant),
                "ignored_count": len(ignored),
                "average_relevance_score": round(avg_relevance_score, 2),
                "average_confidence_score": round(avg_confidence_score, 2),
                "processing_time_seconds": round(processing_time, 2)
            },
            "top_matching_elements": [
                {"element": elem, "occurrences": count}
                for elem, count in top_matching_elements
            ],
            "ignored_patterns_summary": self._get_ignored_patterns_summary(ignored),
            "recommendations": self._generate_recommendations(
                highly_relevant, relevant, potentially_relevant, ignored, parameters
            )
        }

    def _get_ignored_patterns_summary(self, ignored_results: List[RelevanceResult]) -> Dict[str, int]:
        """Get summary of ignored patterns"""
        pattern_counts = {}
        for result in ignored_results:
            for pattern in result.ignored_patterns:
                pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
        return pattern_counts

    def _generate_recommendations(
            self,
            highly_relevant: List[RelevanceResult],
            relevant: List[RelevanceResult],
            potentially_relevant: List[RelevanceResult],
            ignored: List[RelevanceResult],
            parameters: Dict[str, Any]
    ) -> List[str]:
        """
        Generate recommendations based on analysis results.
        Enhanced with RAG context information.
        """
        recommendations = []

        total_relevant = len(highly_relevant) + len(relevant)
        total_ignored = len(ignored)

        if total_ignored > 0:
            recommendations.append(
                f"RAG Context Rules filtered out {total_ignored} irrelevant traces (maintenance/scheduled activities)")

        if total_relevant == 0:
            recommendations.append("No directly relevant traces found. Consider:")
            recommendations.append("- Expanding the search time frame")
            recommendations.append("- Checking if the query keywords are too specific")
            recommendations.append("- Verifying the domain parameter is correct")
            recommendations.append("- Reviewing the RAG context rules to ensure they're not too restrictive")

            if len(potentially_relevant) > 0:
                recommendations.append(
                    f"- Review the {len(potentially_relevant)} potentially relevant traces for indirect evidence")

        elif total_relevant < 5:
            recommendations.append(f"Found {total_relevant} relevant traces. Consider:")
            recommendations.append("- These traces should be prioritized for detailed analysis")
            recommendations.append("- Check if additional time periods should be searched")

            if total_ignored > total_relevant:
                recommendations.append("- Consider refining RAG rules if too many traces are being ignored")

        else:
            recommendations.append(f"Found {total_relevant} relevant traces:")
            recommendations.append(f"- {len(highly_relevant)} highly relevant traces should be analyzed first")
            recommendations.append("- Focus on traces with highest relevance scores")
            recommendations.append("- Look for patterns across multiple traces")

        return recommendations

    def _safe_parse_json(self, raw: str) -> Dict[str, Any]:
        """
        Safely parse JSON from LLM response.
        """
        text = raw.strip()

        # Remove any markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*$', '', text)

        # Extract JSON block
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            text = match.group(0)

        try:
            return self._safe_parse_json(text)
        except Exception as e:
            logger.error(f"Safe JSON parse error: {e}")
            return self._default_analysis_result()

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

    def _validate_analysis_result(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and ensure all required fields are present in analysis result.
        """
        required_fields = {
            'relevance_score': 50,
            'confidence_score': 50,
            'matching_elements': [],
            'non_matching_elements': [],
            'key_findings': [],
            'recommendation': 'REVIEW - Unable to determine relevance'
        }

        for field, default_value in required_fields.items():
            if field not in analysis:
                analysis[field] = default_value

        # Ensure scores are within valid range
        analysis['relevance_score'] = max(0, min(100, analysis.get('relevance_score', 50)))
        analysis['confidence_score'] = max(0, min(100, analysis.get('confidence_score', 50)))

        return analysis

    def _default_analysis_result(self) -> Dict[str, Any]:
        """
        Default analysis result for errors.
        """
        return {
            'relevance_score': 0,
            'confidence_score': 0,
            'matching_elements': [],
            'non_matching_elements': ['Analysis failed'],
            'key_findings': ['Unable to complete analysis'],
            'domain_match': False,
            'time_match': False,
            'keyword_matches': [],
            'recommendation': 'REVIEW - Analysis error',
            'reasoning': 'Analysis could not be completed due to processing error'
        }

    def _create_error_result(self, file_path: str, error_message: str) -> RelevanceResult:
        """
        Create an error result for failed file processing.
        """
        return RelevanceResult(
            file_path=file_path,
            trace_id='unknown',
            relevance_level=RelevanceLevel.UNKNOWN,
            relevance_score=0,
            confidence_score=0,
            matching_elements=[],
            non_matching_elements=[error_message],
            key_findings=[error_message],
            recommendation='REVIEW - File processing error',
            analysis_timestamp=dt.now().isoformat(),
            processing_time_ms=0,
            applied_rules=[],
            ignored_patterns=[]
        )

    def export_results_to_file(
            self,
            results: Dict[str, Any],
            output_filename: str = None
    ) -> str:
        """
        Export analysis results to a formatted file.
        """
        if output_filename is None:
            output_filename = f"relevance_analysis_{dt.now().strftime('%Y%m%d_%H%M%S')}.json"

        output_path = self.output_dir / output_filename

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, default=str)

            logger.info(f"Results exported to: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Error exporting results: {e}")
            raise

    def reload_context_rules(self):
        """
        Reload context rules from file (useful for runtime updates)
        """
        self.rag_manager.load_context_rules()
        logger.info(f"Reloaded {len(self.rag_manager.rules)} context rules")

    def add_context_rule(self, rule: ContextRule) -> bool:
        """
        Add a new context rule and save to file
        """
        try:
            # Add to memory
            self.rag_manager.rules.append(rule)

            # Append to file
            with open(self.rag_manager.context_file_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    rule.id, rule.context, rule.important,
                    rule.ignore, rule.description or ''
                ])

            logger.info(f"Added new context rule: {rule.id}")
            return True

        except Exception as e:
            logger.error(f"Error adding context rule: {e}")
            return False

    def get_verification_summary_string(self, results_file_path: str) -> str:
        """
        Generate a complete verification summary string with file categorization.

        Args:
            results_file_path: Path to the exported JSON results file

        Returns:
            str: Complete summary string with file lists
        """
        try:
            with open(results_file_path, 'r', encoding='utf-8') as f:
                results = json.load(f)

            # Get the basic summary
            basic_summary = self.parse_results_summary(results)

            # Get file lists
            highly_relevant_files = results.get('highly_relevant', [])
            relevant_files = results.get('relevant', [])
            potentially_relevant_files = results.get('potentially_relevant', [])
            not_relevant_files = results.get('not_relevant', [])
            ignored_files = results.get('ignored', [])

            # Convert file paths to just filenames for cleaner output
            def get_filenames(file_list):
                return [Path(f).name for f in file_list]

            # Combine highly relevant and relevant into "Relevant files"
            all_relevant = get_filenames(highly_relevant_files + relevant_files)
            less_relevant = get_filenames(potentially_relevant_files)
            not_relevant = get_filenames(not_relevant_files + ignored_files)

            # Build the complete string
            summary_string = f"{basic_summary} Relevant files: {all_relevant}, Less Relevant Files: {less_relevant}, Not Relevant Files: {not_relevant}"

            return summary_string

        except Exception as e:
            logger.error(f"Error generating verification summary string from {results_file_path}: {e}")
            return f"Error processing verification results from {results_file_path}"

    def get_verification_summary_string_detailed(self, results_file_path: str) -> str:
        """
        Generate a detailed verification summary string with separate highly relevant category.

        Args:
            results_file_path: Path to the exported JSON results file

        Returns:
            str: Detailed summary string with separate categories
        """
        try:
            with open(results_file_path, 'r', encoding='utf-8') as f:
                results = json.load(f)

            # Get the basic summary
            basic_summary = self.parse_results_summary(results)

            # Get file lists
            highly_relevant_files = results.get('highly_relevant', [])
            relevant_files = results.get('relevant', [])
            potentially_relevant_files = results.get('potentially_relevant', [])
            not_relevant_files = results.get('not_relevant', [])
            ignored_files = results.get('ignored', [])

            # Convert file paths to just filenames for cleaner output
            def get_filenames(file_list):
                return [Path(f).name for f in file_list]

            highly_relevant_names = get_filenames(highly_relevant_files)
            relevant_names = get_filenames(relevant_files)
            less_relevant_names = get_filenames(potentially_relevant_files)
            not_relevant_names = get_filenames(not_relevant_files + ignored_files)

            # Build the complete string with all categories
            summary_string = (f"{basic_summary} "
                              f"Highly Relevant files: {highly_relevant_names}, "
                              f"Relevant files: {relevant_names}, "
                              f"Less Relevant Files: {less_relevant_names}, "
                              f"Not Relevant Files: {not_relevant_names}")

            return summary_string

        except Exception as e:
            logger.error(f"Error generating detailed verification summary string from {results_file_path}: {e}")
            return f"Error processing verification results from {results_file_path}"

    def parse_results_summary(self, results: Dict[str, Any]) -> str:
        """
        Parse analysis results and return a human-readable summary string.

        Args:
            results: The results dictionary from analyze_batch_relevance()

        Returns:
            str: Human-readable summary of the analysis results
        """
        try:
            stats = results.get('statistics', {})

            total_files = stats.get('total_files', 0)
            highly_relevant_count = stats.get('highly_relevant_count', 0)
            relevant_count = stats.get('relevant_count', 0)
            potentially_relevant_count = stats.get('potentially_relevant_count', 0)
            not_relevant_count = stats.get('not_relevant_count', 0)
            ignored_count = stats.get('ignored_count', 0)

            # Build the summary string
            summary_parts = []

            # Total requests
            if total_files > 0:
                summary_parts.append(f"I have found a total of {total_files} requests")
            else:
                return "No requests were analyzed."

            # Relevant categories
            relevant_parts = []

            if highly_relevant_count > 0:
                relevant_parts.append(f"{highly_relevant_count} highly relevant")

            if relevant_count > 0:
                relevant_parts.append(f"{relevant_count} relevant")

            if potentially_relevant_count > 0:
                relevant_parts.append(f"{potentially_relevant_count} potentially relevant")

            if not_relevant_count > 0:
                relevant_parts.append(f"{not_relevant_count} not relevant")

            # Add ignored count if any
            if ignored_count > 0:
                relevant_parts.append(f"{ignored_count} ignored (maintenance/scheduled activities)")

            # Combine parts
            if relevant_parts:
                if len(relevant_parts) == 1:
                    summary_parts.append(f"among them I find {relevant_parts[0]}")
                elif len(relevant_parts) == 2:
                    summary_parts.append(f"among them I find {relevant_parts[0]} and {relevant_parts[1]}")
                else:
                    # More than 2 categories
                    last_part = relevant_parts.pop()
                    summary_parts.append(f"among them I find {', '.join(relevant_parts)}, and {last_part}")

            return ", ".join(summary_parts) + "."

        except Exception as e:
            logger.error(f"Error parsing results summary: {e}")
            return "Unable to generate summary due to parsing error."
# Example usage and context file creation utility
def create_sample_context_file(filename: str = "context_rules.csv"):
    """
    Create a sample context rules file with common patterns
    """
    sample_rules = [
        {
            'id': '1',
            'context': 'mfs',
            'important': 'processPayment,transferMoney,balanceInquiry,transaction_created,payment_processed',
            'ignore': 'MFS_TRANSFER_STATUS_UPDATE_SCHEDULER_INVOCATION_TOPIC,HEARTBEAT,HEALTH_CHECK,STATUS_SYNC',
            'description': 'MFS payment processing - ignore scheduled status updates and health checks'
        },
        {
            'id': '2',
            'context': 'transactions',
            'important': 'transaction_created,payment_processed,amount,merchant,transfer_completed',
            'ignore': 'session_cleanup,cache_refresh,log_rotation,connection_pool_stats',
            'description': 'Transaction processing - focus on actual transactions, ignore maintenance'
        },
        {
            'id': '3',
            "context": "bkash",
            "important": "checkBkashProductInfo,checkBkashInfo,executeBkashTransaction,checkBkashTransactionStatus,mapToBkashProductInfoCbsRequest,mapToBkashCustomerKYCRequest,mapToBkashTransactionResponse,mapToBkashTransactionStatusResponse",
            "ignore": "getActiveProvidersList,loadFieldDefinitions,fetchMfsConfig,fetchExternalApiDefinitions,updateDefinitionFields,extractBkashInfoCheckResponseParams,verifyProductResponseStatus,verifyApiResponseStatus,verifyProductTrustLevel,prepareTransactionStatusCheckRequest",
            "description": "bKash MFS service – focus on product info lookup, customer KYC, transaction initiation and status checks; ignore config loading, mapping helpers, and validation helpers"
        },
        {
            'id': '4',
            'context': 'merchant',
            'important': 'merchant_payment,pos_transaction,merchant_settlement,qr_payment',
            'ignore': 'merchant_heartbeat,daily_summary_job,merchant_sync_task',
            'description': 'Merchant transactions - ignore scheduled sync and summary jobs'
        },
        {
            'id': '5',
            'context': 'npsb',
            'important': 'npsb_transfer,interbank_transfer,swift_message,settlement',
            'ignore': 'npsb_heartbeat,system_health_check,connection_test',
            'description': 'NPSB interbank transfers - ignore system health monitoring'
        },
        {
            'id': '6',
            'context': 'beftn',
            'important': 'beftn_transfer,batch_processing,file_upload,transfer_confirmation',
            'ignore': 'batch_scheduler,file_cleanup,archive_old_files',
            'description': 'BEFTN bulk transfers - ignore batch scheduling and cleanup'
        },
        {
            "id": "7",
            "context": "upay",
            "important": "info_check,kyc_verification,transaction,external_transaction,status_check,payment,auth_token",
            "ignore": "getActiveProvidersList,loadFieldDefinitions,fetchMfsConfig,fetchExternalApiDefinitions,updateDefinitionFields,extractInfoCheckResponseParams,verifyApiResponseStatus,putAuthHeaders",
            "description": "UPAY MFS service – focus on KYC verification, transaction processing and status checks; ignore config loading and helper methods"
        }
    ]

    try:
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['id', 'context', 'important', 'ignore', 'description']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(sample_rules)

        print(f"Created sample context file: {filename}")
        print("You can edit this file to customize the rules for your specific use case.")

    except Exception as e:
        print(f"Error creating sample context file: {e}")


# Example usage
if __name__ == "__main__":
    from ollama import Client

    # Create sample context file first
    create_sample_context_file("../app_settings/context_rules.csv")

    # Initialize the agent
    client = Client(host='http://10.112.30.10:11434')
    agent = RelevanceAnalyzerAgent(
        client,
        model=settings.MODEL,
        context_file="../app_settings/context_rules.csv"
    )

    # Example parameters
    original_text = "Can you find any bkash transactions on july 24 2025?"
    parameters = {
        "domain": "transactions",
        "query_keys": ["bkash"],
        "time_frame": "2025-07-24"
    }

    # Example trace files
    trace_dir = "../comprehensive_analysis"
    trace_files = [
        os.path.join(trace_dir, f)
        for f in os.listdir(trace_dir)
        if f.startswith("trace_report_") and f.endswith(".txt")
    ]

    # Analyze relevance with RAG context
    results = agent.analyze_batch_relevance(
        original_text=original_text,
        parameters=parameters,
        trace_files=trace_files
    )

    # Export results
    output_file = agent.export_results_to_file(results)

    print(f"\nAnalysis complete. Results saved to: {output_file}")
    print(f"Highly relevant files: {len(results['highly_relevant'])}")
    print(f"Relevant files: {len(results['relevant'])}")
    print(f"Potentially relevant files: {len(results['potentially_relevant'])}")
    print(f"Not relevant files: {len(results['not_relevant'])}")
    print(f"Ignored files (by RAG rules): {len(results['ignored'])}")

    # Show which context rules were applied
    print(f"\nContext rules applied: {results['context_rules_applied']}")

    # Show ignored patterns summary
    if 'ignored_patterns_summary' in results['summary']:
        print(f"\nIgnored patterns summary:")
        for pattern, count in results['summary']['ignored_patterns_summary'].items():
            print(f"  {pattern}: {count} files")
