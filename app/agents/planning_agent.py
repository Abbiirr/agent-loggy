from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

import regex as re

from app.services.project_service import is_file_based, is_loki_based
from app.services.llm_providers import LLMProvider
from app.services.llm_gateway.gateway import CachePolicy, CacheableValue, get_llm_cache_gateway



logger = logging.getLogger(__name__)

_RE_FENCED_JSON = re.compile(r"```json\\s*(\\{.*?\\})\\s*```", re.DOTALL | re.IGNORECASE)
_RE_BALANCED_OBJ = re.compile(r"(\\{(?:[^{}]|(?1))*\\})", re.DOTALL)  # requires 'regex' module
_RE_THINK_BLOCK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_RE_THINK_UNCLOSED = re.compile(r"<think>.*", re.DOTALL | re.IGNORECASE)


class PlanningAgent:
    """
    Produces a structured execution plan for the log analysis pipeline.

    This agent is intentionally scoped: it plans *how* agent-loggy will analyze logs
    (parameter extraction, search, trace correlation, analysis, verification),
    similar to how tool-based coding agents produce a step-by-step plan before acting.
    """

    def __init__(self, client: Optional[LLMProvider], model: str):
        self.client = client
        self.model = model

    def run(
        self,
        text: str,
        project: str,
        env: str,
        domain: str,
        extracted_params: Optional[Dict[str, Any]] = None,
        cache_policy: Optional[CachePolicy] = None,
    ) -> Dict[str, Any]:
        extracted_params = extracted_params or {}

        if not self.client or not self.client.is_available():
            return self._fallback(text, project, env, domain, extracted_params)

        try:
            messages = [
                {"role": "system", "content": self._system_prompt()},
                {"role": "user", "content": self._user_payload(text, project, env, domain, extracted_params)},
            ]
            gateway = get_llm_cache_gateway()

            def compute() -> CacheableValue:
                resp = self.client.chat(model=self.model, messages=messages, options={"timeout": 30})
                raw = (resp.get("message") or {}).get("content") or ""
                plan = self._safe_parse_json(raw)
                plan = self._normalize_plan(plan, text, project, env, domain, extracted_params)
                return CacheableValue(value=plan, cacheable=True)

            plan, diag = gateway.cached(
                cache_type="planning",
                model=self.model,
                messages=messages,
                options={"timeout": 30},
                default_ttl_seconds=600,
                policy=cache_policy,
                compute=compute,
            )
            logger.info(f"Planning agent cache: {diag.status} (key: {diag.key_prefix[:12] if diag.key_prefix else 'N/A'}...)")
            return plan
        except Exception as e:
            logger.warning("PlanningAgent failed; using fallback: %s", e)
            return self._fallback(text, project, env, domain, extracted_params)

    def _system_prompt(self) -> str:
        return (
            "You are a planning agent for a log analysis backend. "
            "Your job is to turn the user's request into an execution plan for THIS system.\n\n"
            "CRITICAL INSTRUCTIONS:\n"
            "- Output ONLY valid JSON. No markdown, no explanations, no <think> tags.\n"
            "- Do not invent data. If information is missing (especially date/time_frame), ask a question.\n"
            "- Steps must match the system capabilities described in the input payload.\n\n"
            "OUTPUT SCHEMA (strict):\n"
            "{\n"
            '  "plan_version": 1,\n'
            '  "goal": "string",\n'
            '  "can_proceed": true,\n'
            '  "blocking_questions": ["string"],\n'
            '  "assumptions": ["string"],\n'
            '  "steps": [\n'
            "    {\n"
            '      "id": "string",\n'
            '      "title": "string",\n'
            '      "agent_or_tool": "string",\n'
            '      "inputs": ["string"],\n'
            '      "outputs": ["string"],\n'
            '      "notes": ["string"]\n'
            "    }\n"
            "  ],\n"
            '  "expected_artifacts": ["string"],\n'
            '  "replan_triggers": ["string"],\n'
            '  "warnings": ["string"]\n'
            "}\n"
        )

    def _user_payload(
        self,
        text: str,
        project: str,
        env: str,
        domain: str,
        extracted_params: Dict[str, Any],
    ) -> str:
        capability = "unknown"
        if is_file_based(project):
            capability = "file"
        elif is_loki_based(project):
            capability = "loki"

        payload = {
            "request": {
                "prompt": text,
                "project": project,
                "env": env,
                "domain": domain,
                "project_log_source_type": capability,
                "extracted_params": extracted_params,
            },
            "pipeline_capabilities": [
                "extract_parameters(time_frame, domain, query_keys)",
                "search_logs(file_based_or_loki)",
                "extract_trace_ids",
                "compile_full_logs_per_trace",
                "analyze_traces_and_write_reports",
                "verify_relevance_and_summarize",
            ],
            "constraints": {
                "date_required_for_search": True,
                "loki_requires_date": True,
                "file_search_prefers_date": True,
            },
        }
        return json.dumps(payload, ensure_ascii=False)

    def _safe_parse_json(self, raw: str) -> Dict[str, Any]:
        text = (raw or "").strip()
        text = _RE_THINK_BLOCK.sub("", text)
        text = _RE_THINK_UNCLOSED.sub("", text).strip()

        fenced = _RE_FENCED_JSON.search(text)
        if fenced:
            text = fenced.group(1).strip()
        else:
            obj = _RE_BALANCED_OBJ.search(text)
            if obj:
                text = obj.group(1).strip()

        return json.loads(text)

    def _normalize_plan(
        self,
        plan: Dict[str, Any],
        text: str,
        project: str,
        env: str,
        domain: str,
        extracted_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not isinstance(plan, dict):
            return self._fallback(text, project, env, domain, extracted_params)

        required_keys = {"goal", "can_proceed", "blocking_questions", "assumptions", "steps", "expected_artifacts", "warnings"}
        if not required_keys.issubset(plan.keys()):
            return self._fallback(text, project, env, domain, extracted_params)

        if not isinstance(plan.get("steps"), list):
            return self._fallback(text, project, env, domain, extracted_params)

        plan.setdefault("plan_version", 1)
        if "replan_triggers" not in plan or not isinstance(plan.get("replan_triggers"), list):
            plan["replan_triggers"] = [
                "No log files found for the requested date/time_frame",
                "No trace IDs found after searching matching logs",
                "Too many trace IDs found (consider narrowing query_keys or time window)",
            ]

        time_frame = extracted_params.get("time_frame")
        query_keys = extracted_params.get("query_keys") or []

        bq = plan.get("blocking_questions") or []
        if not isinstance(bq, list):
            bq = []

        # Block if time_frame is missing
        if not time_frame:
            plan["can_proceed"] = False
            if not any("date" in str(x).lower() or "time" in str(x).lower() for x in bq):
                bq.append("What date (YYYY-MM-DD) should I search?")

        # Block if query_keys is empty
        if not query_keys:
            plan["can_proceed"] = False
            if not any("identifier" in str(x).lower() or "keyword" in str(x).lower() or "filter" in str(x).lower() for x in bq):
                bq.append("What identifiers or keywords should I search for (e.g., transaction_id, merchant, bkash, nagad)?")

        plan["blocking_questions"] = bq

        if is_loki_based(project) and not time_frame:
            warnings = plan.get("warnings") or []
            if isinstance(warnings, list):
                warnings.append("Loki projects require `time_frame`; the pipeline will stop with an error if missing.")
            plan["warnings"] = warnings

        return plan

    def _fallback(
        self,
        text: str,
        project: str,
        env: str,
        domain: str,
        extracted_params: Dict[str, Any],
    ) -> Dict[str, Any]:
        time_frame = extracted_params.get("time_frame")
        query_keys = extracted_params.get("query_keys") or []

        blocking_questions: List[str] = []
        warnings: List[str] = []

        if not time_frame:
            blocking_questions.append("What date (YYYY-MM-DD) should I search?")
            warnings.append("Without `time_frame`, file search returns no files and Loki search errors.")

        if not query_keys:
            blocking_questions.append("What identifiers should I filter on (e.g., transaction_id, customer_id, amount, merchant, bkash/nagad)?")

        log_source = "unknown"
        if is_file_based(project):
            log_source = "file"
        elif is_loki_based(project):
            log_source = "loki"

        steps = [
            {
                "id": "1",
                "title": "Extract search parameters",
                "agent_or_tool": "ParametersAgent",
                "inputs": ["user prompt"],
                "outputs": ["time_frame", "domain", "query_keys"],
                "notes": ["Produces normalized ISO date when possible."],
            },
            {
                "id": "2",
                "title": "Search logs",
                "agent_or_tool": "FileSearcher" if log_source == "file" else "Loki download_logs",
                "inputs": ["time_frame", "query_keys", "project", "env"],
                "outputs": ["matching log files or downloaded Loki JSON"],
                "notes": [f"Project log source: {log_source}."],
            },
            {
                "id": "3",
                "title": "Extract trace IDs from matches",
                "agent_or_tool": "LogSearcher + trace_id extractor" if log_source == "file" else "extract_trace_ids",
                "inputs": ["log files", "query_keys"],
                "outputs": ["unique trace IDs"],
                "notes": ["Deduplicates trace IDs across files."],
            },
            {
                "id": "4",
                "title": "Compile full logs per trace",
                "agent_or_tool": "FullLogFinder" if log_source == "file" else "gather_logs_for_trace_ids",
                "inputs": ["trace IDs", "log files/date range"],
                "outputs": ["all log entries grouped by trace"],
                "notes": ["Builds a timeline and sources list per trace."],
            },
            {
                "id": "5",
                "title": "Analyze traces and generate reports",
                "agent_or_tool": "AnalyzeAgent",
                "inputs": ["compiled trace logs", "original prompt", "parameters"],
                "outputs": ["per-trace report files", "master summary file"],
                "notes": ["Writes to `app/comprehensive_analysis/`."],
            },
            {
                "id": "6",
                "title": "Verify relevance and summarize results",
                "agent_or_tool": "RelevanceAnalyzerAgent",
                "inputs": ["report files", "original prompt", "parameters"],
                "outputs": ["verification report file", "summary string"],
                "notes": ["Writes to `app/verification_reports/`."],
            },
        ]

        can_proceed = bool(time_frame) and bool(query_keys)
        if is_loki_based(project) and not time_frame:
            warnings.append("Loki projects hard-require `time_frame` (the pipeline returns an error if missing).")

        return {
            "plan_version": 1,
            "goal": f"Analyze logs to answer: {text.strip()}" if text else "Analyze logs to answer the user's question",
            "can_proceed": can_proceed,
            "blocking_questions": blocking_questions,
            "assumptions": [
                f"Project is `{project}` and log source is `{log_source}`.",
                f"Environment is `{env}` and domain context is `{domain}`.",
            ],
            "steps": steps,
            "expected_artifacts": [
                "Per-trace report file(s) under app/comprehensive_analysis/",
                "Master summary report under app/comprehensive_analysis/",
                "Verification report under app/verification_reports/",
            ],
            "replan_triggers": [
                "No log files found for the requested date/time_frame",
                "No trace IDs found after searching matching logs",
                "Too many trace IDs found (consider narrowing query_keys or time window)",
            ],
            "warnings": warnings,
        }
