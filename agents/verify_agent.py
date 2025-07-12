# agents/verify_agent.py

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from ollama import Client
import re, json
from datetime import datetime as dt

logger = logging.getLogger(__name__)


class VerifyAgent:
    """
    Verifies log quality, ranks relevance, and provides concise analysis opinion.

    Responsibilities:
    1. Check if found logs are sufficient or need further searching
    2. Rank log outputs by relevance to the original context
    3. Provide concise summary of findings
    4. Give concise opinion on what likely happened based on the logs
    """

    def __init__(self, client: Client, model: str, output_dir: str = "verification_output"):
        self.client = client
        self.model = model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"VerifyAgent initialized with model: {model}, output directory: {self.output_dir}")

    def analyze_and_verify_concise(
            self,
            original_context: str,
            search_results: Dict,
            trace_data: Dict,
            parameters: Dict,
            output_prefix: str = None
    ) -> Dict:
        """
        Complete verification and analysis with concise single-file output.

        Args:
            original_context: The original user query/context
            search_results: Results from log searching
            trace_data: Comprehensive trace data from all log files
            parameters: Extracted parameters from original context
            output_prefix: Custom prefix for output file

        Returns:
            Dictionary with concise analysis results and file path
        """
        logger.info("Starting concise log verification and analysis...")

        # Step 1: Assess log quality (concise)
        quality_assessment = self._assess_log_quality_concise(
            original_context, search_results, trace_data, parameters
        )

        # Step 2: Rank top 3 traces by relevance (concise)
        ranked_traces = self._rank_traces_concise(
            original_context, trace_data, parameters
        )

        # Step 3: Generate concise summary
        summary = self._generate_summary_concise(
            original_context, search_results, trace_data, ranked_traces
        )

        # Step 4: Provide concise expert opinion
        expert_opinion = self._generate_expert_opinion_concise(
            original_context, trace_data, ranked_traces, parameters
        )

        # Step 5: Determine next steps
        next_steps = self._determine_next_steps_concise(
            quality_assessment, ranked_traces, original_context
        )

        # Compile concise results
        results = {
            'analysis_timestamp': dt.now().isoformat(),
            'original_context': original_context,
            'parameters': parameters,
            'quality_assessment': quality_assessment,
            'ranked_traces': ranked_traces[:3],  # Top 3 only
            'summary': summary,
            'expert_opinion': expert_opinion,
            'next_steps': next_steps,
            'confidence_score': quality_assessment.get('overall_confidence', 0),
            'further_search_needed': {
                'decision': next_steps.get('decision', 'FURTHER_INVESTIGATION_REQUIRED'),
                'confidence_level': next_steps.get('confidence_level', 'LOW'),
                'priority_actions': next_steps.get('priority_actions', [])
            },
            'metadata': {
                'total_files_searched': search_results.get('total_files', 0),
                'total_matches': search_results.get('total_matches', 0),
                'unique_traces': len(trace_data.get('all_trace_data', {})),
                'model_used': self.model
            }
        }

        # Save concise output and add file path to results
        output_path = self._save_concise_analysis(results, output_prefix)
        results['output_file_path'] = output_path

        logger.info(f"Concise analysis completed. Confidence: {results['confidence_score']}/100")
        logger.info(f"Output saved to: {output_path}")
        return results

    def _assess_log_quality_concise(
            self,
            original_context: str,
            search_results: Dict,
            trace_data: Dict,
            parameters: Dict
    ) -> Dict:
        """
        Assess log quality with concise output.
        """
        logger.info("Assessing log quality (concise)...")

        prompt = f"""
Rate log search quality for banking dispute analysis. Answer with JSON only.

CONTEXT: {original_context[:150]}
SEARCH: {search_results.get('total_files', 0)} files, {search_results.get('total_matches', 0)} matches, {len(trace_data.get('all_trace_data', {}))} traces

Rate 0-100:
COMPLETENESS: Enough data to understand the issue?
RELEVANCE: Data relates to the dispute?
COVERAGE: Transaction flow covered?

JSON format only:
{{
    "completeness_score": <number>,
    "relevance_score": <number>,
    "coverage_score": <number>,
    "overall_confidence": <average of above 3>,
    "status": "<one line assessment>",
    "key_gaps": ["<gap1>", "<gap2>"]
}}
"""

        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "Banking log analyst. Respond with valid JSON only. No text before or after JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            raw_response = response["message"]["content"].strip()
            assessment = self._safe_parse_json(raw_response, self._parse_quality_fallback)
            logger.info(f"Quality assessment: {assessment.get('overall_confidence', 0)}/100")
            return assessment

        except Exception as e:
            logger.error(f"Error in quality assessment: {e}")
            return self._get_default_quality()

    def _rank_traces_concise(
            self,
            original_context: str,
            trace_data: Dict,
            parameters: Dict
    ) -> List[Dict]:
        """
        Rank top 3 traces by relevance with concise output.
        """
        logger.info("Ranking traces (concise)...")

        all_trace_data = trace_data.get('all_trace_data', {})
        if not all_trace_data:
            return []

        ranked_traces = []

        for trace_id, data in list(all_trace_data.items())[:5]:  # Limit to top 5 for processing
            prompt = f"""
Rate trace relevance for banking dispute. JSON only.

DISPUTE: {original_context[:120]}
ACCOUNTS: {parameters.get('query_keys', [])}
DATE: {parameters.get('time_frame', '')}

TRACE: {trace_id} - {data.get('total_entries', 0)} entries, {len(data.get('timeline', []))} events

Rate relevance 0-100 and identify key finding.

JSON only:
{{
    "relevance_score": <number>,
    "key_finding": "<one sentence finding>",
    "indicators": ["<indicator1>", "<indicator2>"],
    "concerns": ["<concern1>", "<concern2>"]
}}
"""

            try:
                response = self.client.chat(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "Banking log analyst. JSON only. No explanations."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )

                raw_response = response["message"]["content"].strip()
                ranking = self._safe_parse_json(raw_response, self._parse_ranking_fallback)

                ranked_traces.append({
                    'trace_id': trace_id,
                    'trace_data': data,
                    'relevance_score': ranking.get('relevance_score', 50),
                    'key_finding': ranking.get('key_finding', 'No specific finding'),
                    'indicators': ranking.get('indicators', []),
                    'concerns': ranking.get('concerns', [])
                })

            except Exception as e:
                logger.error(f"Error ranking trace {trace_id}: {e}")
                ranked_traces.append({
                    'trace_id': trace_id,
                    'trace_data': data,
                    'relevance_score': 40,
                    'key_finding': 'Ranking failed - manual review needed',
                    'indicators': [],
                    'concerns': ['Analysis error']
                })

        # Sort by relevance (highest first) and return top 3
        ranked_traces.sort(key=lambda x: x['relevance_score'], reverse=True)
        return ranked_traces[:3]

    def _generate_summary_concise(
            self,
            original_context: str,
            search_results: Dict,
            trace_data: Dict,
            ranked_traces: List[Dict]
    ) -> str:
        """
        Generate 2-3 sentence summary.
        """
        logger.info("Generating concise summary...")

        top_trace_info = ""
        if ranked_traces:
            top = ranked_traces[0]
            top_trace_info = f"Top trace has {top['relevance_score']}% relevance."

        prompt = f"""
Write EXACTLY 2-3 sentences summarizing this banking dispute analysis.

DISPUTE: {original_context[:150]}
RESULTS: Found {len(ranked_traces)} traces from {search_results.get('total_files', 0)} log files. {top_trace_info}

Write only the summary sentences. No explanations, no thinking, no additional text.
Format: "Sentence 1. Sentence 2. Sentence 3."
"""

        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a banking analyst. Write ONLY 2-3 factual sentences. Do not include <think> tags or explanations. Just the summary."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            summary = response["message"]["content"].strip()

            # Remove any thinking tags if they appear
            summary = self._clean_response_text(summary)

            # Ensure it's concise (max 400 chars)
            if len(summary) > 400:
                summary = summary[:397] + "..."

            return summary

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return f"Analyzed {len(ranked_traces)} traces from {search_results.get('total_files', 0)} log files for banking transaction dispute."

    def _generate_expert_opinion_concise(
            self,
            original_context: str,
            trace_data: Dict,
            ranked_traces: List[Dict],
            parameters: Dict
    ) -> str:
        """
        Generate 2-3 sentence expert opinion.
        """
        logger.info("Generating concise expert opinion...")

        if not ranked_traces:
            return "Insufficient trace data for expert analysis."

        top_trace = ranked_traces[0]

        prompt = f"""
As a banking expert, write EXACTLY 2-3 sentences analyzing this transaction dispute.

DISPUTE: {original_context[:150]}
FINDING: {top_trace.get('key_finding', 'Limited data available')}
RELEVANCE: {top_trace['relevance_score']}/100

Write your expert assessment in exactly 2-3 sentences. Include:
1. Most likely cause (system issue, user error, processing delay, or unclear)
2. Your confidence level and reasoning

Format: "Sentence 1. Sentence 2. Sentence 3."
No explanations, no thinking process, just the assessment.
"""

        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior banking expert. Write ONLY 2-3 clear sentences with your assessment. No <think> tags or explanations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            opinion = response["message"]["content"].strip()

            # Remove any thinking tags if they appear
            opinion = self._clean_response_text(opinion)

            # Ensure it's concise (max 400 chars)
            if len(opinion) > 400:
                opinion = opinion[:397] + "..."

            return opinion

        except Exception as e:
            logger.error(f"Error generating expert opinion: {e}")
            return "Expert analysis requires manual review due to processing error."

    def _determine_next_steps_concise(
            self,
            quality_assessment: Dict,
            ranked_traces: List[Dict],
            original_context: str
    ) -> Dict:
        """
        Determine next steps with concise recommendations.
        """
        logger.info("Determining next steps (concise)...")

        confidence = quality_assessment.get('overall_confidence', 0)
        trace_count = len(ranked_traces)
        top_relevance = ranked_traces[0]['relevance_score'] if ranked_traces else 0

        # Simplified decision logic
        if confidence >= 75 and top_relevance >= 70:
            decision = "ANALYSIS_COMPLETE"
            priority_actions = [
                "Review findings with stakeholders",
                "Document resolution steps"
            ]
        elif confidence >= 50 and trace_count > 0:
            decision = "ADDITIONAL_SEARCH_RECOMMENDED"
            priority_actions = [
                "Search expanded time range",
                "Include application logs"
            ]
        else:
            decision = "FURTHER_INVESTIGATION_REQUIRED"
            priority_actions = [
                "Expand search parameters",
                "Check system monitoring logs",
                "Contact technical team"
            ]

        return {
            'decision': decision,
            'confidence_level': 'HIGH' if confidence >= 75 else 'MEDIUM' if confidence >= 50 else 'LOW',
            'priority_actions': priority_actions[:2]  # Top 2 only
        }

    def _save_concise_analysis(self, results: Dict, output_prefix: str = None) -> str:
        """
        Save concise single-file analysis.
        """
        timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
        prefix = output_prefix or f"concise_analysis_{timestamp}"
        file_path = self.output_dir / f"{prefix}.txt"

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # Header
                f.write("BANKING LOG ANALYSIS - CONCISE REPORT\n")
                f.write("=" * 55 + "\n")
                f.write(f"Date: {dt.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"Confidence: {results.get('confidence_score', 0)}/100\n")
                f.write(f"Status: {results.get('next_steps', {}).get('decision', 'N/A')}\n\n")

                # Context (first line)
                context = results.get('original_context', '').strip()
                context_line = context.split('.')[0] + '.' if context else 'N/A'
                if len(context_line) > 120:
                    context_line = context_line[:117] + "..."
                f.write(f"DISPUTE: {context_line}\n\n")

                # Key Metrics
                f.write("KEY METRICS:\n")
                f.write("-" * 15 + "\n")
                qa = results.get('quality_assessment', {})
                f.write(f"• Data Quality: {qa.get('completeness_score', 0)}% complete, "
                        f"{qa.get('relevance_score', 0)}% relevant, "
                        f"{qa.get('coverage_score', 0)}% coverage\n")

                traces = results.get('ranked_traces', [])
                f.write(f"• Found {len(traces)} relevant traces")
                if traces:
                    f.write(f", top relevance: {traces[0]['relevance_score']}%\n")
                else:
                    f.write("\n")

                metadata = results.get('metadata', {})
                f.write(f"• Searched {metadata.get('total_files_searched', 0)} files, "
                        f"{metadata.get('total_matches', 0)} matches\n\n")

                # Summary
                f.write("ANALYSIS SUMMARY:\n")
                f.write("-" * 18 + "\n")
                f.write(f"{results.get('summary', 'Summary not available.')}\n\n")

                # Expert Opinion
                f.write("EXPERT ASSESSMENT:\n")
                f.write("-" * 19 + "\n")
                f.write(f"{results.get('expert_opinion', 'Expert assessment not available.')}\n\n")

                # Top Findings
                if traces:
                    f.write("TOP FINDINGS:\n")
                    f.write("-" * 14 + "\n")
                    for i, trace in enumerate(traces[:2], 1):
                        f.write(f"{i}. {trace.get('key_finding', 'No finding')} "
                                f"(Trace: {trace['trace_id'][:8]}..., "
                                f"Relevance: {trace['relevance_score']}%)\n")
                    f.write("\n")

                # Next Steps
                next_steps = results.get('next_steps', {})
                f.write("NEXT STEPS:\n")
                f.write("-" * 12 + "\n")
                f.write(f"Decision: {next_steps.get('decision', 'N/A')}\n")
                f.write(f"Confidence: {next_steps.get('confidence_level', 'N/A')}\n")
                actions = next_steps.get('priority_actions', [])
                for i, action in enumerate(actions, 1):
                    f.write(f"{i}. {action}\n")
                f.write("\n")

                # Log Files
                f.write("LOG FILES ANALYZED:\n")
                f.write("-" * 20 + "\n")
                all_files = set()
                for trace in traces:
                    trace_data = trace.get('trace_data', {})
                    files = trace_data.get('source_files', [])
                    all_files.update(files)

                if all_files:
                    for i, file_path in enumerate(sorted(all_files), 1):
                        display_path = self._format_file_path(file_path)
                        f.write(f"{i}. {display_path}\n")
                else:
                    f.write("No source files identified\n")
                f.write("\n")

                # Search Parameters
                params = results.get('parameters', {})
                f.write("SEARCH CONTEXT:\n")
                f.write("-" * 16 + "\n")
                f.write(f"Time Frame: {params.get('time_frame', 'N/A')}\n")
                f.write(f"Domain: {params.get('domain', 'N/A')}\n")
                f.write(f"Accounts: {', '.join(params.get('query_keys', []))}\n")

                # Footer
                f.write("\n" + "=" * 55 + "\n")
                f.write(f"Analysis Model: {metadata.get('model_used', 'N/A')}\n")

            logger.info(f"Concise analysis saved to: {file_path}")
            return str(file_path)

        except Exception as e:
            logger.error(f"Error saving concise analysis: {e}")
            raise

    def _format_file_path(self, file_path: str) -> str:
        """Format file path for display."""
        if len(file_path) <= 80:
            return file_path

        # Show last part of path
        parts = file_path.split('/')
        if len(parts) > 1:
            return ".../" + "/".join(parts[-2:])
        else:
            return "..." + file_path[-77:]

    def _safe_parse_json(self, raw: str, fallback_fn):
        """Parse JSON with fallback."""
        text = raw.strip()

        # Remove thinking tags
        if text.lower().startswith("<think>") and text.lower().endswith("</think>"):
            text = text[len("<think>"):-len("</think>")].strip()

        # Extract JSON
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return fallback_fn(text)

    def _parse_quality_fallback(self, text: str) -> Dict:
        """Fallback quality assessment parser."""
        numbers = re.findall(r'\b(\d{1,3})\b', text)
        valid_scores = [int(n) for n in numbers if 0 <= int(n) <= 100]
        scores = (valid_scores + [60, 60, 60])[:3]

        return {
            "completeness_score": scores[0],
            "relevance_score": scores[1],
            "coverage_score": scores[2],
            "overall_confidence": sum(scores) // 3,
            "status": "Assessment completed from text analysis",
            "key_gaps": ["Detailed assessment unavailable"]
        }

    def _parse_ranking_fallback(self, text: str) -> Dict:
        """Fallback ranking parser."""
        score_match = re.search(r'(\d{1,3})', text)
        score = int(score_match.group(1)) if score_match and 0 <= int(score_match.group(1)) <= 100 else 50

        return {
            "relevance_score": score,
            "key_finding": "Analysis completed from text",
            "indicators": ["Text analysis applied"],
            "concerns": ["Detailed parsing unavailable"]
        }

    def _clean_response_text(self, text: str) -> str:
        """
        Clean LLM response text by removing thinking tags and extra content.
        """
        # Remove <think> tags and their content
        import re
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)

        # Remove any remaining XML-like tags
        text = re.sub(r'<[^>]+>', '', text)

        # Clean up extra whitespace
        text = ' '.join(text.split())

        return text.strip()

    def _get_default_quality(self) -> Dict:
        """Default quality assessment."""
        return {
            "completeness_score": 50,
            "relevance_score": 50,
            "coverage_score": 50,
            "overall_confidence": 50,
            "status": "Default assessment applied",
            "key_gaps": ["Assessment processing error"]
        }