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
    Verifies log quality, ranks relevance, and provides analysis opinion.

    Responsibilities:
    1. Check if found logs are sufficient or need further searching
    2. Rank log outputs by relevance to the original context
    3. Provide summary of findings
    4. Give opinion on what likely happened based on the logs
    """

    def __init__(self, client: Client, model: str, output_dir: str = "verification_output"):
        self.client = client
        self.model = model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"VerifyAgent initialized with model: {model}, output directory: {self.output_dir}")

    def analyze_and_verify(
            self,
            original_context: str,
            search_results: Dict,
            trace_data: Dict,
            parameters: Dict,
            save_output: bool = True,
            output_prefix: str = None
    ) -> Dict:
        """
        Complete verification and analysis of log search results.

        Args:
            original_context: The original user query/context
            search_results: Results from log searching
            trace_data: Comprehensive trace data from all log files
            parameters: Extracted parameters from original context
            save_output: Whether to save results to files (default: True)
            output_prefix: Custom prefix for output files (default: timestamp)

        Returns:
            Dictionary with verification results, rankings, summary, and opinion
        """
        logger.info("Starting comprehensive log verification and analysis...")

        # Step 1: Assess log quality and completeness
        quality_assessment = self._assess_log_quality(
            original_context, search_results, trace_data, parameters
        )

        # Step 2: Rank trace logs by relevance
        ranked_traces = self._rank_traces_by_relevance(
            original_context, trace_data, parameters
        )

        # Step 3: Generate comprehensive summary
        summary = self._generate_summary(
            original_context, search_results, trace_data, ranked_traces
        )

        # Step 4: Provide expert opinion on what happened
        expert_opinion = self._generate_expert_opinion(
            original_context, trace_data, ranked_traces, parameters
        )

        # Step 5: Determine if further searching is needed
        further_search_needed = self._determine_further_search_need(
            quality_assessment, ranked_traces, original_context
        )

        # Compile final results
        results = {
            'verification_status': 'COMPLETE',
            'analysis_timestamp': dt.now().isoformat(),
            'original_context': original_context,
            'parameters': parameters,
            'quality_assessment': quality_assessment,
            'ranked_traces': ranked_traces,
            'summary': summary,
            'expert_opinion': expert_opinion,
            'further_search_needed': further_search_needed,
            'confidence_score': quality_assessment.get('overall_confidence', 0),
            'recommendations': self._generate_recommendations(quality_assessment, further_search_needed),
            'metadata': {
                'total_files_searched': search_results.get('total_files', 0),
                'total_matches': search_results.get('total_matches', 0),
                'unique_traces': len(trace_data.get('all_trace_data', {})),
                'model_used': self.model
            }
        }

        # Save output to files if requested
        if save_output:
            self._save_analysis_results(results, output_prefix)

        return results

    def _assess_log_quality(
            self,
            original_context: str,
            search_results: Dict,
            trace_data: Dict,
            parameters: Dict
    ) -> Dict:
        """
        Assess the quality and completeness of found logs.
        """
        logger.info("Assessing log quality and completeness...")

        prompt = f"""
You are an expert log analyst. Assess the quality and completeness of the log search results.

ORIGINAL CONTEXT:
{original_context}

SEARCH PARAMETERS:
- Time Frame: {parameters.get('time_frame', 'Not specified')}
- Domain: {parameters.get('domain', 'Not specified')}
- Query Keys: {parameters.get('query_keys', 'Not specified')}

SEARCH RESULTS SUMMARY:
- Total log files searched: {search_results.get('total_files', 0)}
- Files with matches: {len(search_results.get('log_files', []))}
- Total matches found: {search_results.get('total_matches', 0)}
- Unique trace IDs found: {len(trace_data.get('all_trace_data', {}))}

TRACE DATA OVERVIEW:
{self._format_trace_overview(trace_data)}

Please assess the log quality on these dimensions:

1. COMPLETENESS (0-100): Do we have enough log data to understand what happened?
2. RELEVANCE (0-100): How relevant are the found logs to the original query?
3. COVERAGE (0-100): Do logs cover the expected transaction flow?
4. CLARITY (0-100): Are the logs clear enough to draw conclusions?

RESPOND WITH VALID JSON ONLY. Calculate the overall_confidence as a number (not a formula):
{{
    "completeness_score": <number>,
    "relevance_score": <number>,
    "coverage_score": <number>,
    "clarity_score": <number>,
    "overall_confidence": <calculated average number>,
    "quality_summary": "<brief summary>",
    "missing_elements": ["<missing element 1>", "<missing element 2>"],
    "strengths": ["<strength 1>", "<strength 2>"]
}}
"""

        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert log analyst. You MUST respond with valid JSON only. Do not include any text before or after the JSON. Your response should start with { and end with }."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            raw = response["message"]["content"]
            logger.info(f"Raw LLM response: {raw!r}")

            assessment = self._safe_parse_json(raw, self._parse_quality_assessment_from_text)
            logger.info(f"Quality assessment complete. Overall confidence: {assessment.get('overall_confidence', 0)}")
            return assessment

        except Exception as e:
            logger.error(f"Error in quality assessment: {e}")
            return {
                "completeness_score": 50,
                "relevance_score": 50,
                "coverage_score": 50,
                "clarity_score": 50,
                "overall_confidence": 50,
                "quality_summary": "Assessment failed - manual review needed",
                "missing_elements": ["Assessment error occurred"],
                "strengths": ["Logs were successfully retrieved"]
            }

    def _rank_traces_by_relevance(
            self,
            original_context: str,
            trace_data: Dict,
            parameters: Dict
    ) -> List[Dict]:
        """
        Rank trace logs by relevance to the original context.
        """
        logger.info("Ranking traces by relevance...")

        all_trace_data = trace_data.get('all_trace_data', {})
        if not all_trace_data:
            return []

        ranked_traces = []

        for trace_id, data in all_trace_data.items():
            # Create trace summary for ranking
            trace_summary = self._create_trace_summary(trace_id, data)

            prompt = f"""
You are an expert log analyst. Rank this trace's relevance to the original query.

ORIGINAL CONTEXT:
{original_context}

SEARCH PARAMETERS:
- Query Keys: {parameters.get('query_keys', [])}
- Domain: {parameters.get('domain', '')}
- Time Frame: {parameters.get('time_frame', '')}

TRACE SUMMARY:
Trace ID: {trace_id}
Total Entries: {data.get('total_entries', 0)}
Source Files: {', '.join([Path(f).name for f in data.get('source_files', [])])}
Timeline Length: {len(data.get('timeline', []))}

FIRST FEW TIMELINE ENTRIES:
{self._format_timeline_snippet(data.get('timeline', [])[:5])}

Rate this trace's relevance (0-100) and provide reasoning.

RESPOND WITH VALID JSON ONLY:
{{
    "relevance_score": <number 0-100>,
    "reasoning": "<explanation>",
    "key_indicators": ["<indicator 1>", "<indicator 2>"],
    "concerns": ["<concern 1>", "<concern 2>"]
}}
"""

            try:
                response = self.client.chat(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert log analyst. You MUST respond with valid JSON only. Do not include any text before or after the JSON. Your response should start with { and end with }."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                raw = response["message"]["content"]
                logger.info(f"Raw LLM response: {raw!r}")

                import json
                ranking = self._safe_parse_json(raw, self._parse_quality_assessment_from_text)

                ranked_traces.append({
                    'trace_id': trace_id,
                    'trace_data': data,
                    'relevance_score': ranking.get('relevance_score', 0),
                    'reasoning': ranking.get('reasoning', ''),
                    'key_indicators': ranking.get('key_indicators', []),
                    'concerns': ranking.get('concerns', []),
                    'trace_summary': trace_summary
                })

            except Exception as e:
                logger.error(f"Error ranking trace {trace_id}: {e}")
                ranked_traces.append({
                    'trace_id': trace_id,
                    'trace_data': data,
                    'relevance_score': 50,
                    'reasoning': 'Ranking failed - manual review needed',
                    'key_indicators': [],
                    'concerns': ['Ranking error occurred'],
                    'trace_summary': trace_summary
                })

        # Sort by relevance score (highest first)
        ranked_traces.sort(key=lambda x: x['relevance_score'], reverse=True)

        logger.info(f"Ranked {len(ranked_traces)} traces by relevance")
        return ranked_traces

    def _generate_summary(
            self,
            original_context: str,
            search_results: Dict,
            trace_data: Dict,
            ranked_traces: List[Dict]
    ) -> str:
        """
        Generate a comprehensive summary of findings.
        """
        logger.info("Generating comprehensive summary...")

        prompt = f"""
You are an expert log analyst. Provide a comprehensive summary of the log analysis findings.

ORIGINAL CONTEXT:
{original_context}

SEARCH RESULTS:
- Files searched: {search_results.get('total_files', 0)}
- Total matches: {search_results.get('total_matches', 0)}
- Unique traces found: {len(ranked_traces)}

TOP RANKED TRACES:
{self._format_top_traces_summary(ranked_traces[:3])}

Provide a clear, professional summary covering:
1. What was searched for
2. What was found
3. Key patterns or issues identified
4. Overall assessment

Keep it concise but comprehensive (3-5 paragraphs).
"""

        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert log analyst. Provide a clear, comprehensive summary. Be concise but thorough."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            summary = response["message"]["content"].strip()
            logger.info("Summary generated successfully")
            return summary

        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return "Summary generation failed - manual review of logs recommended."

    def _generate_expert_opinion(
            self,
            original_context: str,
            trace_data: Dict,
            ranked_traces: List[Dict],
            parameters: Dict
    ) -> str:
        """
        Generate expert opinion on what likely happened based on the logs.
        """
        logger.info("Generating expert opinion...")

        if not ranked_traces:
            return "Insufficient data to form expert opinion - no relevant traces found."

        # Focus on the most relevant trace
        top_trace = ranked_traces[0]

        prompt = f"""
You are a senior banking systems expert and log analyst. Based on the log analysis, provide your expert opinion on what likely happened.

ORIGINAL CONTEXT:
{original_context}

PARAMETERS:
- Time Frame: {parameters.get('time_frame', '')}
- Domain: {parameters.get('domain', '')}
- Account Numbers: {parameters.get('query_keys', [])}

MOST RELEVANT TRACE ANALYSIS:
Trace ID: {top_trace['trace_id']}
Relevance Score: {top_trace['relevance_score']}/100
Key Indicators: {', '.join(top_trace['key_indicators'])}
Timeline: {len(top_trace['trace_data'].get('timeline', []))} events
Source Files: {', '.join([Path(f).name for f in top_trace['trace_data'].get('source_files', [])])}

TIMELINE ANALYSIS:
{self._format_detailed_timeline(top_trace['trace_data'].get('timeline', []))}

As a banking systems expert, provide your professional opinion on:
1. What most likely happened in this transaction
2. Whether this appears to be a system issue, user error, or normal processing
3. Potential root causes based on the log patterns
4. Risk assessment and impact

Be specific and technical where appropriate, but also provide clear conclusions.
"""

        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a senior banking systems expert and log analyst. Provide detailed, technical analysis with clear conclusions. Be specific about system behavior and potential issues."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )

            opinion = response["message"]["content"].strip()
            logger.info("Expert opinion generated successfully")
            return opinion

        except Exception as e:
            logger.error(f"Error generating expert opinion: {e}")
            return "Expert opinion generation failed - manual analysis by banking systems expert recommended."

    def _determine_further_search_need(
            self,
            quality_assessment: Dict,
            ranked_traces: List[Dict],
            original_context: str
    ) -> Dict:
        """
        Determine if further searching is needed based on quality and findings.
        """
        logger.info("Determining need for further searching...")

        confidence = quality_assessment.get('overall_confidence', 0)
        trace_count = len(ranked_traces)
        top_relevance = ranked_traces[0]['relevance_score'] if ranked_traces else 0

        # Decision logic
        if confidence >= 80 and trace_count > 0 and top_relevance >= 70:
            decision = "NO_FURTHER_SEARCH"
            reason = "High confidence in findings with relevant traces"
        elif confidence >= 60 and trace_count > 0:
            decision = "OPTIONAL_SEARCH"
            reason = "Moderate confidence - additional search may provide more clarity"
        else:
            decision = "FURTHER_SEARCH_NEEDED"
            reason = "Low confidence or insufficient relevant data found"

        recommendations = []
        if decision == "FURTHER_SEARCH_NEEDED":
            recommendations.extend([
                "Expand time range for search",
                "Include additional log types",
                "Search for related transaction IDs",
                "Check system logs for the same time period"
            ])
        elif decision == "OPTIONAL_SEARCH":
            recommendations.extend([
                "Consider searching adjacent time periods",
                "Look for related transactions if needed"
            ])

        return {
            'decision': decision,
            'reason': reason,
            'confidence_threshold': confidence,
            'recommendations': recommendations
        }

    def _format_trace_overview(self, trace_data: Dict) -> str:
        """Format trace data overview for prompts."""
        all_trace_data = trace_data.get('all_trace_data', {})
        if not all_trace_data:
            return "No trace data available"

        overview = []
        for trace_id, data in all_trace_data.items():
            overview.append(
                f"- Trace {trace_id}: {data.get('total_entries', 0)} entries across {len(data.get('source_files', []))} files")

        return "\n".join(overview)

    def _create_trace_summary(self, trace_id: str, data: Dict) -> str:
        """Create a brief summary of a trace."""
        timeline = data.get('timeline', [])
        first_op = timeline[0]['operation'] if timeline else 'Unknown'
        last_op = timeline[-1]['operation'] if timeline else 'Unknown'

        return f"Trace {trace_id}: {data.get('total_entries', 0)} entries, {first_op} → {last_op}"

    def _format_timeline_snippet(self, timeline: List[Dict]) -> str:
        """Format a snippet of timeline for prompts."""
        if not timeline:
            return "No timeline data"

        lines = []
        for i, step in enumerate(timeline):
            lines.append(
                f"{i + 1}. {step.get('timestamp', 'N/A')} - {step.get('operation', 'Unknown')} [{step.get('level', 'N/A')}]")

        return "\n".join(lines)

    def _format_top_traces_summary(self, top_traces: List[Dict]) -> str:
        """Format summary of top traces for prompts."""
        if not top_traces:
            return "No traces found"

        lines = []
        for i, trace in enumerate(top_traces, 1):
            lines.append(f"{i}. {trace['trace_summary']} (Relevance: {trace['relevance_score']}/100)")

        return "\n".join(lines)

    def _format_detailed_timeline(self, timeline: List[Dict]) -> str:
        """Format detailed timeline for expert opinion."""
        if not timeline:
            return "No timeline available"

        lines = []
        for step in timeline:
            source = Path(step.get('source_file', 'Unknown')).name if step.get('source_file') else 'Unknown'
            lines.append(
                f"{step.get('timestamp', 'N/A')} - {step.get('operation', 'Unknown')} [{step.get('level', 'N/A')}] ({source})")

        return "\n".join(lines)

    def _generate_recommendations(self, quality_assessment: Dict, further_search: Dict) -> List[str]:
        """Generate actionable recommendations based on analysis."""
        recommendations = []

        # Quality-based recommendations
        if quality_assessment.get('completeness_score', 0) < 70:
            recommendations.append("Consider expanding search time range")

        if quality_assessment.get('coverage_score', 0) < 70:
            recommendations.append("Search additional log types (application, integration)")

        # Search-based recommendations
        recommendations.extend(further_search.get('recommendations', []))

        # General recommendations
        recommendations.extend([
            "Review trace files for detailed transaction flow",
            "Cross-reference findings with system monitoring data",
            "Document findings for future reference"
        ])

        return list(set(recommendations))  # Remove duplicates

    def _parse_quality_assessment_from_text(self, text: str) -> Dict:
        """
        Parse quality assessment from free-form text when JSON parsing fails.
        Uses keyword matching and number extraction.
        """
        logger.info("Parsing quality assessment from text...")

        import re

        # Extract numbers that look like scores (0-100)
        numbers = re.findall(r'\b(\d{1,3})\b', text)
        valid_scores = [int(n) for n in numbers if 0 <= int(n) <= 100]

        # Default scores if not enough found
        default_scores = [70, 70, 70, 70]
        scores = (valid_scores + default_scores)[:4]

        # Extract text content for summary
        summary_text = text[:300] if text else "Assessment completed from text analysis"

        # Look for specific indicators
        missing_elements = []
        strengths = []

        if "missing" in text.lower() or "lack" in text.lower():
            missing_elements.append("Some elements may be missing (detected from text)")
        if "complete" in text.lower() or "comprehensive" in text.lower():
            strengths.append("Comprehensive data found")
        if "clear" in text.lower() or "detailed" in text.lower():
            strengths.append("Clear log entries")

        return {
            "completeness_score": scores[0],
            "relevance_score": scores[1],
            "coverage_score": scores[2],
            "clarity_score": scores[3],
            "overall_confidence": sum(scores) // 4,
            "quality_summary": summary_text,
            "missing_elements": missing_elements if missing_elements else ["Parsed from text - details may be limited"],
            "strengths": strengths if strengths else ["Logs successfully retrieved and analyzed"]
        }

    def _parse_ranking_from_text(self, text: str) -> Dict:
        """
        Parse ranking from free-form text when JSON parsing fails.
        """
        logger.info("Parsing ranking from text...")

        import re

        # Look for relevance score
        score_match = re.search(r'(?:relevance|score|rating).*?(\d{1,3})', text, re.IGNORECASE)
        score = int(score_match.group(1)) if score_match and 0 <= int(score_match.group(1)) <= 100 else 70

        # Extract reasoning (first 200 chars)
        reasoning = text[:200] if text else "Ranking completed from text analysis"

        # Look for indicators and concerns
        indicators = []
        concerns = []

        if "relevant" in text.lower():
            indicators.append("Relevance indicators found")
        if "match" in text.lower():
            indicators.append("Pattern matches detected")
        if "concern" in text.lower() or "issue" in text.lower():
            concerns.append("Potential issues identified")
        if "error" in text.lower() or "problem" in text.lower():
            concerns.append("Error patterns detected")

        return {
            "relevance_score": score,
            "reasoning": reasoning,
            "key_indicators": indicators if indicators else ["Text analysis completed"],
            "concerns": concerns if concerns else ["No specific concerns identified"]
        }

    def _get_default_quality_assessment(self) -> Dict:
        """Get default quality assessment when all parsing fails."""
        return {
            "completeness_score": 60,
            "relevance_score": 60,
            "coverage_score": 60,
            "clarity_score": 60,
            "overall_confidence": 60,
            "quality_summary": "Assessment completed with default values - manual review recommended",
            "missing_elements": ["Unable to parse detailed assessment"],
            "strengths": ["Logs were successfully retrieved"]
        }

    def _get_default_ranking(self) -> Dict:
        """Get default ranking when all parsing fails."""
        return {
            "relevance_score": 60,
            "reasoning": "Ranking completed with default values - manual review recommended",
            "key_indicators": ["Default analysis applied"],
            "concerns": ["Unable to parse detailed ranking"]
        }

    def _create_fallback_quality_assessment(self, response_text: str) -> Dict:
        """Create a fallback quality assessment when JSON parsing fails."""
        # This method is now replaced by _parse_quality_assessment_from_text
        return self._parse_quality_assessment_from_text(response_text)

    def _create_fallback_ranking(self, response_text: str) -> Dict:
        """Create a fallback ranking when JSON parsing fails."""
        # This method is now replaced by _parse_ranking_from_text
        return self._parse_ranking_from_text(response_text)

    def _fix_json_math_expressions(self, json_str: str) -> str:
        """
        Fix mathematical expressions in JSON strings that prevent parsing.
        """
        import re

        # Common patterns to fix
        patterns = [
            # Fix: (50 + 70 + 40 + 60) / 4 -> 55
            (r'"overall_confidence":\s*\((\d+)\s*\+\s*(\d+)\s*\+\s*(\d+)\s*\+\s*(\d+)\)\s*/\s*4',
             lambda
                 m: f'"overall_confidence": {(int(m.group(1)) + int(m.group(2)) + int(m.group(3)) + int(m.group(4))) // 4}'),

            # Fix: (num1 + num2 + num3) / 3 -> average
            (r'"overall_confidence":\s*\((\d+)\s*\+\s*(\d+)\s*\+\s*(\d+)\)\s*/\s*3',
             lambda m: f'"overall_confidence": {(int(m.group(1)) + int(m.group(2)) + int(m.group(3))) // 3}'),

            # Fix any remaining math expressions with numbers
            (r'"overall_confidence":\s*\([^)]+\)\s*/\s*\d+',
             '"overall_confidence": 60'),

            # Fix any field with mathematical expressions
            (r':\s*\([^)]*\d+[^)]*\)[^,}]*', ': 60')
        ]

        for pattern, replacement in patterns:
            if callable(replacement):
                json_str = re.sub(pattern, replacement, json_str)
            else:
                json_str = re.sub(pattern, replacement, json_str)

        logger.info(f"Fixed JSON: {json_str[:200]}...")
        return json_str

    def _safe_parse_json(self, raw: str, parse_fallback_fn):
        """
        Try to turn raw LLM output into a dict:
        1. Strip <think>…</think>
        2. Pull out the first {...} block
        3. json.loads; if it fails, try fix_json_math_expressions
        4. If still fails, delegate to parse_fallback_fn(raw)
        """
        text = raw.strip()

        # 1) strip <think> tags
        if text.lower().startswith("<think>") and text.lower().endswith("</think>"):
            text = text[len("<think>"):-len("</think>")].strip()

        # 2) extract first JSON object
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)

        # 3) try standard JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 4) try fixing math expressions
            fixed = self._fix_json_math_expressions(text)
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                # 5) fallback to your text parser
                return parse_fallback_fn(text)

    def _save_analysis_results(self, results: Dict, output_prefix: str = None) -> Dict[str, str]:
        """
        Save analysis results to multiple file formats.

        Args:
            results: Complete analysis results dictionary
            output_prefix: Custom prefix for output files

        Returns:
            Dictionary mapping file types to their saved paths
        """
        timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
        prefix = output_prefix or f"log_analysis_{timestamp}"

        saved_files = {}

        try:
            # 1. Save complete results as JSON
            json_path = self.output_dir / f"{prefix}_complete_analysis.json"
            self._save_json_results(results, json_path)
            saved_files['complete_json'] = str(json_path)

            # 2. Save human-readable summary report
            summary_path = self.output_dir / f"{prefix}_summary_report.txt"
            self._save_summary_report(results, summary_path)
            saved_files['summary_report'] = str(summary_path)

            # 3. Save expert opinion as separate file
            opinion_path = self.output_dir / f"{prefix}_expert_opinion.txt"
            self._save_expert_opinion(results, opinion_path)
            saved_files['expert_opinion'] = str(opinion_path)

            # 4. Save trace rankings as CSV
            rankings_path = self.output_dir / f"{prefix}_trace_rankings.csv"
            self._save_trace_rankings_csv(results, rankings_path)
            saved_files['trace_rankings'] = str(rankings_path)

            # 5. Save detailed trace data as JSON
            traces_path = self.output_dir / f"{prefix}_detailed_traces.json"
            self._save_detailed_traces(results, traces_path)
            saved_files['detailed_traces'] = str(traces_path)

            # 6. Save executive summary (short version)
            exec_summary_path = self.output_dir / f"{prefix}_executive_summary.txt"
            self._save_executive_summary(results, exec_summary_path)
            saved_files['executive_summary'] = str(exec_summary_path)

            logger.info(f"Analysis results saved to {len(saved_files)} files in {self.output_dir}")

            # Add file paths to results
            results['output_files'] = saved_files

        except Exception as e:
            logger.error(f"Error saving analysis results: {e}")
            saved_files['error'] = str(e)

        return saved_files

    def _save_json_results(self, results: Dict, file_path: Path):
        """Save complete results as formatted JSON."""
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Complete JSON results saved to: {file_path}")

    def _save_summary_report(self, results: Dict, file_path: Path):
        """Save human-readable summary report."""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("LOG ANALYSIS VERIFICATION REPORT\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Analysis Timestamp: {results.get('analysis_timestamp', 'N/A')}\n")
            f.write(f"Model Used: {results.get('metadata', {}).get('model_used', 'N/A')}\n")
            f.write(f"Confidence Score: {results.get('confidence_score', 0)}/100\n\n")

            f.write("ORIGINAL CONTEXT:\n")
            f.write("-" * 40 + "\n")
            f.write(f"{results.get('original_context', 'N/A')}\n\n")

            f.write("SEARCH PARAMETERS:\n")
            f.write("-" * 40 + "\n")
            params = results.get('parameters', {})
            f.write(f"Time Frame: {params.get('time_frame', 'N/A')}\n")
            f.write(f"Domain: {params.get('domain', 'N/A')}\n")
            f.write(f"Query Keys: {params.get('query_keys', 'N/A')}\n\n")

            f.write("SEARCH RESULTS SUMMARY:\n")
            f.write("-" * 40 + "\n")
            metadata = results.get('metadata', {})
            f.write(f"Total Files Searched: {metadata.get('total_files_searched', 0)}\n")
            f.write(f"Total Matches Found: {metadata.get('total_matches', 0)}\n")
            f.write(f"Unique Traces Found: {metadata.get('unique_traces', 0)}\n\n")

            f.write("QUALITY ASSESSMENT:\n")
            f.write("-" * 40 + "\n")
            qa = results.get('quality_assessment', {})
            f.write(f"Completeness: {qa.get('completeness_score', 0)}/100\n")
            f.write(f"Relevance: {qa.get('relevance_score', 0)}/100\n")
            f.write(f"Coverage: {qa.get('coverage_score', 0)}/100\n")
            f.write(f"Clarity: {qa.get('clarity_score', 0)}/100\n")
            f.write(f"Overall Confidence: {qa.get('overall_confidence', 0)}/100\n\n")
            f.write(f"Summary: {qa.get('quality_summary', 'N/A')}\n\n")

            f.write("TOP RANKED TRACES:\n")
            f.write("-" * 40 + "\n")
            traces = results.get('ranked_traces', [])[:5]  # Top 5
            for i, trace in enumerate(traces, 1):
                f.write(f"{i}. Trace ID: {trace.get('trace_id', 'N/A')}\n")
                f.write(f"   Relevance: {trace.get('relevance_score', 0)}/100\n")
                f.write(f"   Summary: {trace.get('trace_summary', 'N/A')}\n")
                f.write(f"   Reasoning: {trace.get('reasoning', 'N/A')}\n\n")

            f.write("ANALYSIS SUMMARY:\n")
            f.write("-" * 40 + "\n")
            f.write(f"{results.get('summary', 'N/A')}\n\n")

            f.write("RECOMMENDATIONS:\n")
            f.write("-" * 40 + "\n")
            for rec in results.get('recommendations', []):
                f.write(f"• {rec}\n")
            f.write("\n")

            f.write("FURTHER SEARCH ASSESSMENT:\n")
            f.write("-" * 40 + "\n")
            search_needed = results.get('further_search_needed', {})
            f.write(f"Decision: {search_needed.get('decision', 'N/A')}\n")
            f.write(f"Reason: {search_needed.get('reason', 'N/A')}\n\n")

        logger.info(f"Summary report saved to: {file_path}")

    def _save_expert_opinion(self, results: Dict, file_path: Path):
        """Save expert opinion as separate text file."""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("EXPERT OPINION - LOG ANALYSIS\n")
            f.write("=" * 80 + "\n\n")

            f.write(f"Analysis Date: {results.get('analysis_timestamp', 'N/A')}\n")
            f.write(f"Confidence Level: {results.get('confidence_score', 0)}/100\n\n")

            f.write("CONTEXT:\n")
            f.write("-" * 20 + "\n")
            f.write(f"{results.get('original_context', 'N/A')}\n\n")

            f.write("EXPERT ANALYSIS:\n")
            f.write("-" * 20 + "\n")
            f.write(f"{results.get('expert_opinion', 'N/A')}\n\n")

            # Add top trace details
            traces = results.get('ranked_traces', [])
            if traces:
                top_trace = traces[0]
                f.write("PRIMARY TRACE ANALYZED:\n")
                f.write("-" * 30 + "\n")
                f.write(f"Trace ID: {top_trace.get('trace_id', 'N/A')}\n")
                f.write(f"Relevance Score: {top_trace.get('relevance_score', 0)}/100\n")
                f.write(f"Key Indicators: {', '.join(top_trace.get('key_indicators', []))}\n")
                f.write(f"Concerns: {', '.join(top_trace.get('concerns', []))}\n\n")

        logger.info(f"Expert opinion saved to: {file_path}")

    def _save_trace_rankings_csv(self, results: Dict, file_path: Path):
        """Save trace rankings as CSV file."""
        traces = results.get('ranked_traces', [])
        if not traces:
            logger.warning("No traces to save to CSV")
            return

        with open(file_path, 'w', encoding='utf-8') as f:
            # CSV Header
            f.write("Rank,Trace_ID,Relevance_Score,Total_Entries,Source_Files,Key_Indicators,Concerns,Reasoning\n")

            for i, trace in enumerate(traces, 1):
                trace_data = trace.get('trace_data', {})
                source_files = '; '.join([Path(f).name for f in trace_data.get('source_files', [])])
                indicators = '; '.join(trace.get('key_indicators', []))
                concerns = '; '.join(trace.get('concerns', []))
                reasoning = trace.get('reasoning', '').replace('\n', ' ').replace(',', ';')

                f.write(f"{i},"
                        f"{trace.get('trace_id', 'N/A')},"
                        f"{trace.get('relevance_score', 0)},"
                        f"{trace_data.get('total_entries', 0)},"
                        f"\"{source_files}\","
                        f"\"{indicators}\","
                        f"\"{concerns}\","
                        f"\"{reasoning}\"\n")

        logger.info(f"Trace rankings CSV saved to: {file_path}")

    def _save_detailed_traces(self, results: Dict, file_path: Path):
        """Save detailed trace data as JSON."""
        traces_data = {}
        for trace in results.get('ranked_traces', []):
            trace_id = trace.get('trace_id')
            if trace_id:
                traces_data[trace_id] = {
                    'ranking_info': {
                        'relevance_score': trace.get('relevance_score'),
                        'reasoning': trace.get('reasoning'),
                        'key_indicators': trace.get('key_indicators'),
                        'concerns': trace.get('concerns'),
                        'trace_summary': trace.get('trace_summary')
                    },
                    'trace_data': trace.get('trace_data', {})
                }

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(traces_data, f, indent=2, ensure_ascii=False, default=str)

        logger.info(f"Detailed traces saved to: {file_path}")

    def _save_executive_summary(self, results: Dict, file_path: Path):
        """Save brief executive summary."""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("EXECUTIVE SUMMARY - LOG ANALYSIS\n")
            f.write("=" * 50 + "\n\n")

            f.write(f"Date: {results.get('analysis_timestamp', 'N/A')}\n")
            f.write(f"Confidence: {results.get('confidence_score', 0)}/100\n\n")

            # Key findings
            qa = results.get('quality_assessment', {})
            f.write("KEY FINDINGS:\n")
            f.write(f"• Found {results.get('metadata', {}).get('unique_traces', 0)} unique traces\n")
            f.write(f"• Overall quality: {qa.get('overall_confidence', 0)}/100\n")
            f.write(f"• Data completeness: {qa.get('completeness_score', 0)}/100\n\n")

            # Top recommendation
            recommendations = results.get('recommendations', [])
            if recommendations:
                f.write(f"TOP RECOMMENDATION: {recommendations[0]}\n\n")

            # Search decision
            search_needed = results.get('further_search_needed', {})
            f.write(f"FURTHER SEARCH: {search_needed.get('decision', 'N/A')}\n")
            f.write(f"REASON: {search_needed.get('reason', 'N/A')}\n\n")

            # Brief summary (first 300 chars)
            summary = results.get('summary', '')
            if len(summary) > 300:
                summary = summary[:300] + "..."
            f.write(f"SUMMARY: {summary}\n")

        logger.info(f"Executive summary saved to: {file_path}")

    def save_custom_report(self, results: Dict, template_type: str = "detailed",
                           output_path: str = None) -> str:
        """
        Save a custom formatted report.

        Args:
            results: Analysis results dictionary
            template_type: Type of report ("detailed", "brief", "technical")
            output_path: Custom output path

        Returns:
            Path to saved report
        """
        timestamp = dt.now().strftime("%Y%m%d_%H%M%S")
        if not output_path:
            output_path = self.output_dir / f"custom_report_{template_type}_{timestamp}.txt"
        else:
            output_path = Path(output_path)

        try:
            if template_type == "technical":
                self._save_technical_report(results, output_path)
            elif template_type == "brief":
                self._save_brief_report(results, output_path)
            else:  # detailed
                self._save_summary_report(results, output_path)

            logger.info(f"Custom {template_type} report saved to: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Error saving custom report: {e}")
            raise

    def _save_technical_report(self, results: Dict, file_path: Path):
        """Save technical report with detailed trace analysis."""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("TECHNICAL LOG ANALYSIS REPORT\n")
            f.write("=" * 60 + "\n\n")

            # Technical metadata
            f.write("TECHNICAL DETAILS:\n")
            f.write("-" * 30 + "\n")
            metadata = results.get('metadata', {})
            f.write(f"Analysis Model: {metadata.get('model_used', 'N/A')}\n")
            f.write(f"Files Processed: {metadata.get('total_files_searched', 0)}\n")
            f.write(f"Pattern Matches: {metadata.get('total_matches', 0)}\n")
            f.write(f"Trace Objects: {metadata.get('unique_traces', 0)}\n\n")

            # Quality metrics
            qa = results.get('quality_assessment', {})
            f.write("QUALITY METRICS:\n")
            f.write("-" * 30 + "\n")
            for metric in ['completeness_score', 'relevance_score', 'coverage_score', 'clarity_score']:
                f.write(f"{metric.replace('_', ' ').title()}: {qa.get(metric, 0)}/100\n")
            f.write(f"Composite Score: {qa.get('overall_confidence', 0)}/100\n\n")

            # Detailed trace analysis
            f.write("TRACE ANALYSIS:\n")
            f.write("-" * 30 + "\n")
            for i, trace in enumerate(results.get('ranked_traces', [])[:3], 1):
                f.write(f"Trace {i}: {trace.get('trace_id', 'N/A')}\n")
                f.write(f"  Relevance: {trace.get('relevance_score', 0)}/100\n")
                trace_data = trace.get('trace_data', {})
                f.write(f"  Events: {trace_data.get('total_entries', 0)}\n")
                f.write(f"  Timeline: {len(trace_data.get('timeline', []))}\n")
                f.write(f"  Sources: {len(trace_data.get('source_files', []))}\n\n")

    def _save_brief_report(self, results: Dict, file_path: Path):
        """Save brief summary report."""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("BRIEF LOG ANALYSIS REPORT\n")
            f.write("=" * 40 + "\n\n")

            f.write(f"Analysis Date: {results.get('analysis_timestamp', 'N/A')}\n")
            f.write(f"Confidence: {results.get('confidence_score', 0)}/100\n\n")

            # One-line summary
            qa = results.get('quality_assessment', {})
            f.write(f"Status: {qa.get('quality_summary', 'Analysis completed')}\n\n")

            # Top findings
            traces = results.get('ranked_traces', [])
            if traces:
                top_trace = traces[0]
                f.write(f"Primary Finding: {top_trace.get('trace_summary', 'N/A')}\n")
                f.write(f"Relevance: {top_trace.get('relevance_score', 0)}/100\n\n")

            # Next steps
            search_needed = results.get('further_search_needed', {})
            f.write(f"Next Steps: {search_needed.get('decision', 'N/A')}\n")
            f.write(f"Reason: {search_needed.get('reason', 'N/A')}\n")