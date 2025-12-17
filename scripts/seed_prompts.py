#!/usr/bin/env python
"""
Seed script to migrate hardcoded prompts to the database.

Run this script after applying the prompts_versioned migration:
    uv run python scripts/seed_prompts.py
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.db.session import get_db_session
from app.models.prompt import PromptVersioned, PromptHistory


# Prompts extracted from the codebase
PROMPTS_TO_SEED = [
    {
        "prompt_name": "parameter_extraction_system",
        "agent_name": "parameter_agent",
        "prompt_type": "system",
        "variables": {"allowed_query_keys": "list", "excluded_query_keys": "list", "allowed_domains": "list", "excluded_domains": "list"},
        "prompt_content": """You are a strict parameter extractor.
Return ONLY valid JSON with this exact schema:
{"time_frame": "YYYY-MM-DD or null", "domain": "domain_name", "query_keys": ["key1","key2","key3"]}

RULES:
1) query_keys is a flat array of simple field names (lowercase snake_case). No objects/arrays.
2) domain is the main data category from this allow-list only.
3) If no time mentioned → time_frame = null.
4) time_frame MUST be a single ISO date (YYYY-MM-DD) or null.
5) If user gives a month or a relative period ("July 2025", "last week", "this month"), convert to one concrete start date (YYYY-MM-DD). For a month use day 1; for ranges use the start date.
6) If you cannot confidently produce a single date, set time_frame to null.
7) Use ONLY the allowed query keys; never output excluded ones.

ALLOWED query_keys: $allowed_query_keys
EXCLUDED query_keys: $excluded_query_keys

ALLOWED domains: $allowed_domains
EXCLUDED domains: $excluded_domains

EXAMPLES:
User: "Show me merchant transactions over 500 last week"
Output: {"time_frame": "2025-07-14", "domain": "transactions", "query_keys": ["merchant","amount"]}

User: "Find customers who bought electronics in January 2025"
Output: {"time_frame": "2025-01-01", "domain": "customers", "query_keys": ["category"]}

User: "List all product reviews with ratings"
Output: {"time_frame": null, "domain": "reviews", "query_keys": ["product_id","rating","review_text"]}

User: "Get bKash payments from this month"
Output: {"time_frame": "2025-10-01", "domain": "payments", "query_keys": ["bkash","mfs"]}

Return ONLY the JSON. No extra text."""
    },
    {
        "prompt_name": "trace_analysis_system",
        "agent_name": "analyze_agent",
        "prompt_type": "system",
        "variables": {},
        "prompt_content": "You are a senior banking systems analyst with expertise in transaction processing, log analysis, and dispute resolution. Analyze the provided log data thoroughly to understand exactly what happened during this transaction. Focus on technical details and evidence-based conclusions."
    },
    {
        "prompt_name": "trace_analysis_user",
        "agent_name": "analyze_agent",
        "prompt_type": "user",
        "variables": {"original_context": "str", "time_frame": "str", "query_keys": "list", "domain": "str", "trace_id": "str", "total_entries": "int", "source_files_count": "int", "timeline_count": "int", "sample_messages": "str", "timeline_steps": "str"},
        "prompt_content": """You are a senior banking systems analyst investigating a transaction dispute. Analyze this trace by examining the actual log content to understand what happened during this transaction request.

ORIGINAL DISPUTE: $original_context

SEARCH PARAMETERS:
- Time Frame: $time_frame
- Account Numbers: $query_keys
- Domain/System: $domain

TRACE ANALYSIS DATA:
- Trace ID: $trace_id
- Total Log Entries: $total_entries
- Source Log Files: $source_files_count
- Timeline Events: $timeline_count

ACTUAL LOG MESSAGES (Sample):
$sample_messages

CHRONOLOGICAL TIMELINE:
$timeline_steps

DEEP ANALYSIS REQUIRED:
Based on the actual log content above, analyze what really happened in this transaction request:

1. What was the transaction attempting to do?
2. Did it complete successfully or fail? At what stage?
3. What specific errors, warnings, or issues occurred?
4. What was the final outcome/status?
5. How does this relate to the customer's complaint?
6. What evidence supports or contradicts the customer's claim?

Provide detailed forensic analysis in JSON format:

{
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
}"""
    },
    {
        "prompt_name": "entries_analysis_system",
        "agent_name": "analyze_agent",
        "prompt_type": "system",
        "variables": {},
        "prompt_content": "You are a senior banking systems analyst. Provide thorough, evidence-based analysis."
    },
    {
        "prompt_name": "entries_analysis_user",
        "agent_name": "analyze_agent",
        "prompt_type": "user",
        "variables": {"dispute_text": "str", "trace_id": "str", "entry_count": "int", "sample_messages": "str"},
        "prompt_content": """You are a senior banking systems analyst investigating a customer dispute.

CUSTOMER DISPUTE: $dispute_text

TRACE DETAILS:
- Trace ID: $trace_id
- Total Log Entries: $entry_count

SAMPLE LOG MESSAGES:
$sample_messages

Analyze this trace and provide your expert assessment in JSON format:

{
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
}"""
    },
    {
        "prompt_name": "quality_assessment_system",
        "agent_name": "analyze_agent",
        "prompt_type": "system",
        "variables": {},
        "prompt_content": "Banking analyst. JSON only."
    },
    {
        "prompt_name": "quality_assessment_user",
        "agent_name": "analyze_agent",
        "prompt_type": "user",
        "variables": {"original_context": "str", "total_files": "int", "total_matches": "int", "trace_count": "int"},
        "prompt_content": """Rate overall log search quality for banking dispute. JSON only.

CONTEXT: $original_context
RESULTS: $total_files files, $total_matches matches, $trace_count traces

Rate 0-100 for:
- COMPLETENESS: Sufficient data to understand issue?
- RELEVANCE: Data relates to the dispute?
- COVERAGE: Transaction flow adequately covered?

JSON format:
{
    "completeness_score": <number>,
    "relevance_score": <number>,
    "coverage_score": <number>,
    "overall_confidence": <average>,
    "status": "<one line assessment>",
    "key_gaps": ["<gap1>", "<gap2>"]
}"""
    },
    {
        "prompt_name": "relevance_analysis_system",
        "agent_name": "verify_agent",
        "prompt_type": "system",
        "variables": {},
        "prompt_content": "You are an expert at analyzing system logs and determining relevance to user queries. Use provided context rules to make better relevance decisions. Be precise and thorough in your analysis."
    },
    {
        "prompt_name": "relevance_analysis_user",
        "agent_name": "verify_agent",
        "prompt_type": "user",
        "variables": {"original_text": "str", "domain": "str", "query_keys": "list", "time_frame": "str", "additional_params": "str", "rag_context": "str", "trace_id": "str", "timestamp": "str", "total_entries": "int", "service_names": "str", "operations": "str", "log_samples": "str", "timeline_summary": "str"},
        "prompt_content": """You are an expert system analyst determining if a request trace is relevant to a user's query.
You have access to context rules that help identify what's important vs what should be ignored.

ORIGINAL USER QUERY: $original_text

EXTRACTED PARAMETERS:
- Domain: $domain
- Query Keys: $query_keys
- Time Frame: $time_frame
- Additional Parameters: $additional_params

$rag_context

TRACE INFORMATION:
- Trace ID: $trace_id
- Timestamp: $timestamp
- Total Log Entries: $total_entries
- Services Involved: $service_names
- Key Operations: $operations

SAMPLE LOG MESSAGES:
$log_samples

TIMELINE SUMMARY:
$timeline_summary

ANALYSIS REQUIRED:
Determine if this trace is relevant to the user's query by analyzing:
1. Does the trace contain operations related to the query domain ($domain)?
2. Do the log messages contain the query keys ($query_keys)?
3. Does the timestamp match the requested time frame ($time_frame)?
4. Are there any operations or data that directly address the user's question?
5. Consider the IMPORTANT PATTERNS defined in the context rules
6. Even if not directly matching, could this trace provide useful context?

IMPORTANT: Use the context rules to boost relevance scores for traces containing important patterns
and to understand what activities are just maintenance/noise.

Provide analysis in JSON format:
{
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
}"""
    },
]


def seed_prompts():
    """Seed all prompts into the database."""
    print("Starting prompt seeding...")

    with get_db_session() as db:
        for prompt_data in PROMPTS_TO_SEED:
            prompt_name = prompt_data["prompt_name"]

            # Check if prompt already exists
            existing = db.query(PromptVersioned).filter(
                PromptVersioned.prompt_name == prompt_name,
                PromptVersioned.is_active == True
            ).first()

            if existing:
                print(f"  Skipping '{prompt_name}' - already exists (version {existing.version})")
                continue

            # Create new prompt
            new_prompt = PromptVersioned(
                prompt_name=prompt_name,
                version=1,
                prompt_content=prompt_data["prompt_content"],
                variables=prompt_data.get("variables", {}),
                agent_name=prompt_data.get("agent_name"),
                prompt_type=prompt_data.get("prompt_type"),
                is_active=True,
                created_by="seed_script"
            )
            db.add(new_prompt)
            db.flush()

            # Create history entry
            history = PromptHistory(
                prompt_id=new_prompt.id,
                action="created",
                old_content=None,
                new_content=new_prompt.prompt_content,
                changed_by="seed_script"
            )
            db.add(history)

            print(f"  Created '{prompt_name}' (agent: {prompt_data.get('agent_name')}, type: {prompt_data.get('prompt_type')})")

    print(f"\nSeeding complete! {len(PROMPTS_TO_SEED)} prompts processed.")


if __name__ == "__main__":
    seed_prompts()
