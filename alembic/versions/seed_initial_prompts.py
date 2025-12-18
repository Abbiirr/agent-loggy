"""Seed initial prompts into prompts_versioned table

Revision ID: seed_initial_prompts
Revises: add_eval_tables
Create Date: 2025-12-18

This migration seeds all the initial system and user prompts that were previously
hardcoded in the agent files. Prompts are now always loaded from the database.

System Prompts seeded:
- parameter_extraction_system (ParametersAgent)
- trace_analysis_system (AnalyzeAgent)
- entries_analysis_system (AnalyzeAgent)
- quality_assessment_system (AnalyzeAgent)
- relevance_analysis_system (RelevanceAnalyzerAgent)

User Prompts seeded:
- trace_analysis_user (AnalyzeAgent)
- entries_analysis_user (AnalyzeAgent)
- quality_assessment_user (AnalyzeAgent)
- relevance_analysis_user (RelevanceAnalyzerAgent)
"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

# revision identifiers, used by Alembic.
revision = 'seed_initial_prompts'
down_revision = 'add_eval_tables'
branch_labels = None
depends_on = None


def get_schema():
    try:
        from app.config import settings
        return settings.DATABASE_SCHEMA
    except:
        return "public"


SCHEMA = get_schema()

# ============================================================================
# PROMPT DEFINITIONS
# ============================================================================

PARAMETER_EXTRACTION_SYSTEM = """You are a parameter extractor for a log search system. Your ONLY job is to extract structured parameters from user queries.

CRITICAL INSTRUCTIONS:
- Output ONLY valid JSON. No explanations, no thinking, no <think> tags.
- Do NOT research, analyze, or try to understand what user keywords mean.
- User keywords like names ("frodo", "john") are search terms for log queries, NOT topics to research.
- Extract parameters mechanically. Do not hallucinate or add information.

OUTPUT SCHEMA (strict):
{"time_frame": "YYYY-MM-DD or null", "domain": "domain_name", "query_keys": ["key1","key2"]}

RULES:
1) query_keys: flat array of lowercase snake_case field names from ALLOWED list only.
2) domain: category from ALLOWED domains list only.
3) time_frame: single ISO date (YYYY-MM-DD) or null if no date mentioned.
4) For relative dates ("last week", "this month"), use the start date.
5) For month names ("July 2025", "december 17 2025"), convert to YYYY-MM-DD.

ALLOWED query_keys: $allowed_query_keys
EXCLUDED query_keys: $excluded_query_keys
ALLOWED domains: $allowed_domains
EXCLUDED domains: $excluded_domains

EXAMPLES:
User: "Show me merchant transactions over 500 last week"
{"time_frame": "2025-07-14", "domain": "transactions", "query_keys": ["merchant","amount"]}

User: "Find customers who bought electronics in January 2025"
{"time_frame": "2025-01-01", "domain": "customers", "query_keys": ["category"]}

User: "List all product reviews with ratings"
{"time_frame": null, "domain": "reviews", "query_keys": ["product_id","rating","review_text"]}

User: "Get bKash payments from this month"
{"time_frame": "2025-10-01", "domain": "payments", "query_keys": ["bkash","mfs"]}

User: "find what happened user frodo december 17 2025"
{"time_frame": "2025-12-17", "domain": "users", "query_keys": ["user_id"]}

User: "check transactions for customer john on 2025-12-15"
{"time_frame": "2025-12-15", "domain": "transactions", "query_keys": ["customer_id"]}

RESPOND WITH ONLY THE JSON OBJECT. NO OTHER TEXT."""

PARAMETER_EXTRACTION_VARIABLES = {
    "allowed_query_keys": "Template variable: comma-separated list of allowed query keys",
    "excluded_query_keys": "Template variable: comma-separated list of excluded query keys",
    "allowed_domains": "Template variable: comma-separated list of allowed domains",
    "excluded_domains": "Template variable: comma-separated list of excluded domains"
}

TRACE_ANALYSIS_SYSTEM = """You are a senior banking systems analyst with expertise in transaction processing, log analysis, and dispute resolution. Analyze the provided log data thoroughly to understand exactly what happened during this transaction. Focus on technical details and evidence-based conclusions.

Your responsibilities:
1. Examine log entries chronologically to reconstruct the transaction flow
2. Identify any errors, failures, or anomalies in the processing
3. Determine the root cause of any issues found
4. Assess whether the evidence supports or contradicts customer claims
5. Provide specific, actionable recommendations

Always base your conclusions on actual evidence from the logs. If evidence is insufficient, clearly state what additional information would be needed."""

ENTRIES_ANALYSIS_SYSTEM = """You are a senior banking systems analyst. Provide thorough, evidence-based analysis of transaction logs.

When analyzing log entries:
1. Focus on the chronological sequence of events
2. Identify key operations and their outcomes
3. Note any errors, warnings, or unusual patterns
4. Correlate related entries to understand the full transaction flow
5. Provide clear, actionable insights

Your analysis should be factual and based solely on the log evidence provided. Clearly distinguish between confirmed findings and inferences."""

QUALITY_ASSESSMENT_SYSTEM = """You are a banking log analysis quality assessor. Evaluate the completeness and relevance of log data for dispute resolution.

Assessment criteria:
1. COMPLETENESS: Is there sufficient data to understand what happened?
2. RELEVANCE: Does the data directly relate to the dispute/query?
3. COVERAGE: Are all stages of the transaction flow represented?

Provide scores (0-100) for each criterion and identify specific gaps that may impact analysis quality. Output JSON format only."""

RELEVANCE_ANALYSIS_SYSTEM = """You are an expert at analyzing system logs and determining relevance to user queries. Use provided context rules to make better relevance decisions. Be precise and thorough in your analysis.

When determining relevance:
1. Match log content against the user's search parameters (domain, query keys, time frame)
2. Consider both direct matches and contextually related information
3. Apply provided RAG context rules to identify important vs. ignorable patterns
4. Score relevance objectively based on evidence strength

Important patterns from context rules should increase relevance scores. Maintenance/scheduled activities should typically be filtered out unless directly relevant to the query.

Provide detailed reasoning for your relevance determination."""


# ============================================================================
# USER PROMPT DEFINITIONS (Templates with variables)
# ============================================================================

TRACE_ANALYSIS_USER = """You are a senior banking systems analyst investigating a transaction dispute. Analyze this trace by examining the actual log content to understand what happened during this transaction request.

ORIGINAL DISPUTE: $original_context

SEARCH PARAMETERS:
- Time Frame: $time_frame
- Account Numbers: $query_keys
- Domain/System: $domain

TRACE ANALYSIS DATA:
- Trace ID: $trace_id
- Total Log Entries: $total_entries
- Source Log Files: $source_files_count
- Timeline Events: $timeline_events_count

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

TRACE_ANALYSIS_USER_VARIABLES = {
    "original_context": "The original user dispute/query text (truncated to 300 chars)",
    "time_frame": "Search time frame parameter",
    "query_keys": "List of query keys/account numbers",
    "domain": "Domain/system being searched",
    "trace_id": "The trace ID being analyzed",
    "total_entries": "Total number of log entries",
    "source_files_count": "Number of source log files",
    "timeline_events_count": "Number of timeline events",
    "sample_messages": "Sample log messages (bullet list)",
    "timeline_steps": "Chronological timeline steps"
}

ENTRIES_ANALYSIS_USER = """You are a senior banking systems analyst investigating a customer dispute.

CUSTOMER DISPUTE: $dispute_text

TRACE DETAILS:
- Trace ID: $trace_id
- Total Log Entries: $total_entries

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

ENTRIES_ANALYSIS_USER_VARIABLES = {
    "dispute_text": "The customer dispute text (truncated to 300 chars)",
    "trace_id": "The trace ID being analyzed",
    "total_entries": "Total number of log entries",
    "sample_messages": "Sample log messages (bullet list)"
}

QUALITY_ASSESSMENT_USER = """Rate overall log search quality for banking dispute. JSON only.

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

QUALITY_ASSESSMENT_USER_VARIABLES = {
    "original_context": "Original context/dispute text (truncated to 150 chars)",
    "total_files": "Number of files searched",
    "total_matches": "Number of matches found",
    "trace_count": "Number of traces found"
}

RELEVANCE_ANALYSIS_USER = """You are an expert system analyst determining if a request trace is relevant to a user's query.
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

RELEVANCE_ANALYSIS_USER_VARIABLES = {
    "original_text": "Original user query text",
    "domain": "Domain parameter",
    "query_keys": "Query keys list",
    "time_frame": "Time frame parameter",
    "additional_params": "Additional parameters JSON",
    "rag_context": "RAG context rules section",
    "trace_id": "Trace ID",
    "timestamp": "Trace timestamp",
    "total_entries": "Total log entries",
    "service_names": "Comma-separated service names",
    "operations": "Comma-separated operations",
    "log_samples": "Sample log messages (bullet list)",
    "timeline_summary": "Timeline summary text"
}


# ============================================================================
# MIGRATION FUNCTIONS
# ============================================================================

def upgrade() -> None:
    """Seed all initial prompts into the prompts_versioned table."""

    # Define all prompts to insert (system + user prompts)
    prompts = [
        # ===== SYSTEM PROMPTS =====
        {
            "prompt_name": "parameter_extraction_system",
            "prompt_content": PARAMETER_EXTRACTION_SYSTEM,
            "variables": PARAMETER_EXTRACTION_VARIABLES,
            "agent_name": "parameter_agent",
            "prompt_type": "system",
            "created_by": "migration:seed_initial_prompts"
        },
        {
            "prompt_name": "trace_analysis_system",
            "prompt_content": TRACE_ANALYSIS_SYSTEM,
            "variables": {},
            "agent_name": "analyze_agent",
            "prompt_type": "system",
            "created_by": "migration:seed_initial_prompts"
        },
        {
            "prompt_name": "entries_analysis_system",
            "prompt_content": ENTRIES_ANALYSIS_SYSTEM,
            "variables": {},
            "agent_name": "analyze_agent",
            "prompt_type": "system",
            "created_by": "migration:seed_initial_prompts"
        },
        {
            "prompt_name": "quality_assessment_system",
            "prompt_content": QUALITY_ASSESSMENT_SYSTEM,
            "variables": {},
            "agent_name": "analyze_agent",
            "prompt_type": "system",
            "created_by": "migration:seed_initial_prompts"
        },
        {
            "prompt_name": "relevance_analysis_system",
            "prompt_content": RELEVANCE_ANALYSIS_SYSTEM,
            "variables": {},
            "agent_name": "verify_agent",
            "prompt_type": "system",
            "created_by": "migration:seed_initial_prompts"
        },
        # ===== USER PROMPTS =====
        {
            "prompt_name": "trace_analysis_user",
            "prompt_content": TRACE_ANALYSIS_USER,
            "variables": TRACE_ANALYSIS_USER_VARIABLES,
            "agent_name": "analyze_agent",
            "prompt_type": "user",
            "created_by": "migration:seed_initial_prompts"
        },
        {
            "prompt_name": "entries_analysis_user",
            "prompt_content": ENTRIES_ANALYSIS_USER,
            "variables": ENTRIES_ANALYSIS_USER_VARIABLES,
            "agent_name": "analyze_agent",
            "prompt_type": "user",
            "created_by": "migration:seed_initial_prompts"
        },
        {
            "prompt_name": "quality_assessment_user",
            "prompt_content": QUALITY_ASSESSMENT_USER,
            "variables": QUALITY_ASSESSMENT_USER_VARIABLES,
            "agent_name": "analyze_agent",
            "prompt_type": "user",
            "created_by": "migration:seed_initial_prompts"
        },
        {
            "prompt_name": "relevance_analysis_user",
            "prompt_content": RELEVANCE_ANALYSIS_USER,
            "variables": RELEVANCE_ANALYSIS_USER_VARIABLES,
            "agent_name": "verify_agent",
            "prompt_type": "user",
            "created_by": "migration:seed_initial_prompts"
        },
    ]

    # Insert each prompt
    for prompt in prompts:
        # Use dollar-quoted strings to safely handle special characters in prompt content
        variables_json = str(prompt["variables"]).replace("'", '"')

        op.execute(f"""
            INSERT INTO {SCHEMA}.prompts_versioned
            (prompt_name, version, prompt_content, variables, agent_name, prompt_type, is_active, created_by, created_at)
            VALUES (
                '{prompt["prompt_name"]}',
                1,
                $prompt${prompt["prompt_content"]}$prompt$,
                '{variables_json}'::jsonb,
                '{prompt["agent_name"]}',
                '{prompt["prompt_type"]}',
                true,
                '{prompt["created_by"]}',
                CURRENT_TIMESTAMP
            )
            ON CONFLICT (prompt_name, version) DO UPDATE SET
                prompt_content = EXCLUDED.prompt_content,
                variables = EXCLUDED.variables,
                agent_name = EXCLUDED.agent_name,
                prompt_type = EXCLUDED.prompt_type,
                is_active = EXCLUDED.is_active;
        """)

        # Also insert history record for audit trail
        op.execute(f"""
            INSERT INTO {SCHEMA}.prompt_history
            (prompt_id, action, new_content, changed_by, changed_at)
            SELECT id, 'created', prompt_content, 'migration:seed_initial_prompts', CURRENT_TIMESTAMP
            FROM {SCHEMA}.prompts_versioned
            WHERE prompt_name = '{prompt["prompt_name"]}' AND version = 1;
        """)


def downgrade() -> None:
    """Remove all seeded prompts."""

    prompt_names = [
        # System prompts
        'parameter_extraction_system',
        'trace_analysis_system',
        'entries_analysis_system',
        'quality_assessment_system',
        'relevance_analysis_system',
        # User prompts
        'trace_analysis_user',
        'entries_analysis_user',
        'quality_assessment_user',
        'relevance_analysis_user',
    ]

    for prompt_name in prompt_names:
        # Delete history first (foreign key constraint)
        op.execute(f"""
            DELETE FROM {SCHEMA}.prompt_history
            WHERE prompt_id IN (
                SELECT id FROM {SCHEMA}.prompts_versioned
                WHERE prompt_name = '{prompt_name}'
            );
        """)

        # Delete the prompt
        op.execute(f"""
            DELETE FROM {SCHEMA}.prompts_versioned
            WHERE prompt_name = '{prompt_name}';
        """)
