# orchestrator.py
import asyncio
import logging
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

from starlette.concurrency import run_in_threadpool
from app.services.llm_providers import LLMProvider
from app.agents.parameter_agent import ParametersAgent
from app.agents.planning_agent import PlanningAgent
from app.agents.file_searcher import FileSearcher
from app.tools.log_searcher import LogSearcher
from app.tools.full_log_finder import FullLogFinder
from app.agents.analyze_agent import AnalyzeAgent
from app.agents.verify_agent import RelevanceAnalyzerAgent
from app.tools.loki.loki_trace_id_extractor import gather_logs_for_trace_ids, extract_trace_ids
from app.tools.loki.loki_query_builder import download_logs_cached
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from app.tools.loki.loki_log_report_generator import generate_comprehensive_report, parse_loki_json
import csv

from app.services.project_service import is_file_based, is_loki_based
from app.services.llm_gateway.gateway import CachePolicy

logger = logging.getLogger(__name__)

NEGATE_RULES_PATH = "app_settings/negate_keys.csv"


@dataclass
class PipelineContext:
    """Holds state passed between pipeline steps."""
    text: str
    project: str
    env: str
    domain: str
    negate_keys: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    log_files: List[Any] = field(default_factory=list)
    unique_filename: str = ""
    search_date: str = ""
    end_date_str: str = ""
    unique_ids: List[str] = field(default_factory=list)
    compiled: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    report_files: List[str] = field(default_factory=list)
    master_report: str = ""
    cache_policy: Optional[CachePolicy] = None
    cache_diagnostics: Dict[str, Any] = field(default_factory=dict)


class Orchestrator:
    """
    Enhanced Orchestrator with streaming support for SSE.
    Refactored for clarity with each step as a separate method.
    """

    def __init__(self, llm_provider: LLMProvider, model: str, log_base_dir: str = "./data"):
        self.param_agent = ParametersAgent(llm_provider, model)
        self.planning_agent = PlanningAgent(llm_provider, model)
        self.file_searcher = FileSearcher(Path(log_base_dir), llm_provider, model)
        self.log_searcher = LogSearcher(context=2)
        self.full_log_finder = FullLogFinder()
        self.analyze_agent = AnalyzeAgent(llm_provider, model, output_dir="app/comprehensive_analysis")
        self.verify_agent = RelevanceAnalyzerAgent(llm_provider, model, output_dir="app/verification_reports")

    # ==================== MAIN PIPELINE ====================

    async def analyze_stream(
        self,
        text: str,
        project: str,
        env: str,
        domain: str,
        cache_policy: Optional[CachePolicy] = None,
    ) -> Dict[str, Any]:
        """Main analysis pipeline - orchestrates all steps."""
        ctx = PipelineContext(text=text, project=project, env=env, domain=domain, cache_policy=cache_policy)

        # Load configuration (run in threadpool to avoid blocking event loop)
        ctx.negate_keys = await run_in_threadpool(self._load_negate_keys)

        # STEP 1: Parameter extraction
        ctx.params, diag = await run_in_threadpool(self._step1_extract_parameters, ctx.text, ctx.cache_policy)
        ctx.cache_diagnostics["parameter_extraction"] = diag.__dict__
        logger.info(f"Parameter extraction cache: {diag.status} (key: {diag.key_prefix[:12] if diag.key_prefix else 'N/A'}...)")
        yield "Extracted Parameters", {"parameters": ctx.params, "cache": ctx.cache_diagnostics["parameter_extraction"]}

        # STEP 1b: Plan the pipeline steps (internal use only)
        plan = await run_in_threadpool(
            self.planning_agent.run,
            text=ctx.text,
            project=ctx.project,
            env=ctx.env,
            domain=ctx.domain,
            extracted_params=ctx.params,
            cache_policy=ctx.cache_policy,
        )
        logger.debug("Generated plan: %s", json.dumps(plan, indent=2))

        if isinstance(plan, dict) and plan.get("can_proceed") is False:
            yield "Need Clarification", {"questions": plan.get("blocking_questions", [])}
            yield "done", {"status": "needs_input"}
            return

        # STEP 2: Log search (file-based or Loki)
        step2_result = await run_in_threadpool(self._step2_search_logs, ctx)
        if step2_result.get("error"):
            yield "Error", {"error": step2_result["error"]}
            return
        yield step2_result["event"], step2_result["data"]

        # STEP 3: Trace ID collection
        step3_result = await run_in_threadpool(self._step3_collect_trace_ids, ctx)
        yield step3_result["event"], step3_result["data"]

        # STEP 4: Compile logs
        step4_result = await self._step4_compile_logs(ctx)
        yield step4_result["event"], step4_result["data"]

        # STEP 5: Analysis & report generation
        step5_result = await run_in_threadpool(self._step5_analyze_and_generate_reports, ctx)
        yield step5_result["event"], step5_result["data"]

        # STEP 6: Verification
        step6_result = await run_in_threadpool(self._step6_verify, ctx)
        yield step6_result["event"], step6_result["data"]

        # Done
        logger.info("Analysis complete.")
        yield "done", {"message": "Analysis complete."}

    # ==================== STEP METHODS ====================

    def _load_negate_keys(self) -> List[str]:
        """Load negation keys from CSV configuration file."""
        negate_keys = []
        try:
            with open(NEGATE_RULES_PATH, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader, None)  # Skip header
                for row in reader:
                    if len(row) >= 3:
                        term = row[2].strip()
                        if term:
                            negate_keys.append(term)
        except FileNotFoundError:
            logger.warning(f"Negation rules file not found at {NEGATE_RULES_PATH}")
        except Exception as e:
            logger.error(f"Error reading negate rules: {e}")
        return negate_keys

    def _step1_extract_parameters(
        self, text: str, cache_policy: Optional[CachePolicy] = None
    ) -> tuple[Dict[str, Any], Any]:
        """STEP 1: Extract parameters from user query using LLM."""
        logger.info("STEP 1: Parameter extraction…")
        params, diag = self.param_agent.run(text, cache_policy=cache_policy)
        logger.info("Extracted parameters: %s", json.dumps(params, indent=2))
        return params, diag

    def _step2_search_logs(self, ctx: PipelineContext) -> Dict[str, Any]:
        """STEP 2: Search logs - dispatches to file-based or Loki-based search."""
        if is_file_based(ctx.project):
            return self._step2_search_logs_file_based(ctx)
        elif is_loki_based(ctx.project):
            return self._step2_search_logs_loki(ctx)
        else:
            logger.warning(f"Unknown project type: {ctx.project}")
            return {"event": "Warning", "data": {"warning": f"Unknown project type: {ctx.project}"}}

    def _step2_search_logs_file_based(self, ctx: PipelineContext) -> Dict[str, Any]:
        """STEP 2 (file-based): Search local log files."""
        logger.info("STEP 2: File search…")
        ctx.log_files = self.file_searcher.find_and_verify(ctx.params)
        files = [str(f) for f in ctx.log_files]
        logger.info({"found_files": files, "total_files": len(files)})
        return {"event": "Found relevant files", "data": {"total_files": len(files)}}

    def _step2_search_logs_loki(self, ctx: PipelineContext) -> Dict[str, Any]:
        """STEP 2 (Loki): Download logs from Loki."""
        logger.info("STEP 2: Loki search…")
        query_keys = ctx.params.get("query_keys", [])
        ctx.search_date = ctx.params.get("time_frame")
        logger.debug("Loki search: query_keys=%s, search_date=%s", query_keys, ctx.search_date)

        # Validate time_frame
        if not ctx.search_date:
            logger.error("time_frame is None or empty - cannot proceed with Loki search without a date")
            return {"error": "Missing time_frame parameter. Please specify a date for the search."}

        try:
            search_dt = date_parser.parse(ctx.search_date)
        except Exception as e:
            logger.error("Failed to parse time_frame '%s': %s", ctx.search_date, e)
            return {"error": f"Invalid time_frame format: {ctx.search_date}"}

        end_dt = search_dt + timedelta(days=1)
        ctx.end_date_str = end_dt.date().isoformat()
        logger.debug("Loki search date range: %s to %s", ctx.search_date, ctx.end_date_str)

        # Ensure loki_logs directory exists
        loki_logs_dir = Path("app/loki_logs")
        loki_logs_dir.mkdir(parents=True, exist_ok=True)

        pipeline = [f'!= "{term}"' for term in ctx.negate_keys]

        ctx.unique_filename = download_logs_cached(
            filters={"service_namespace": ctx.project.lower()},
            search=query_keys,
            date_str=ctx.search_date,
            end_date_str=ctx.end_date_str,
            pipeline=pipeline
        )

        if not ctx.unique_filename:
            logger.error("Failed to download logs from Loki")
            return {"error": "Failed to download logs from Loki"}

        logger.info(f"Downloaded logs to {ctx.unique_filename}")
        return {"event": "Downloaded logs in file", "data": {}}

    def _step3_collect_trace_ids(self, ctx: PipelineContext) -> Dict[str, Any]:
        """STEP 3: Collect trace IDs - dispatches to file-based or Loki-based."""
        logger.info("STEP 3: Trace ID collection…")
        if is_file_based(ctx.project):
            return self._step3_collect_trace_ids_file_based(ctx)
        elif is_loki_based(ctx.project):
            return self._step3_collect_trace_ids_loki(ctx)
        return {"event": "Found trace id(s)", "data": {"count": 0}}

    def _step3_collect_trace_ids_file_based(self, ctx: PipelineContext) -> Dict[str, Any]:
        """STEP 3 (file-based): Extract trace IDs from local log files."""
        patterns = ctx.params.get("query_keys", [])
        ctx.unique_ids = []
        for lf in ctx.log_files:
            for r in self.log_searcher.search_with_trace_ids(lf, patterns):
                tid = r.get("trace_id")
                if tid and tid not in ctx.unique_ids:
                    ctx.unique_ids.append(tid)
        logger.info({"unique_ids": ctx.unique_ids})
        return {"event": "Found trace id(s)", "data": {"count": len(ctx.unique_ids)}}

    def _step3_collect_trace_ids_loki(self, ctx: PipelineContext) -> Dict[str, Any]:
        """STEP 3 (Loki): Extract trace IDs from downloaded Loki logs."""
        ctx.unique_ids = extract_trace_ids(ctx.unique_filename)
        logger.info({"unique_ids": ctx.unique_ids})
        return {"event": "Found trace id(s)", "data": {"count": len(ctx.unique_ids)}}

    async def _step4_compile_logs(self, ctx: PipelineContext) -> Dict[str, Any]:
        """STEP 4: Compile full logs - dispatches to file-based or Loki-based."""
        logger.info("STEP 4: Compiling full logs…")
        if is_file_based(ctx.project):
            return await run_in_threadpool(self._step4_compile_logs_file_based, ctx)
        elif is_loki_based(ctx.project):
            return await self._step4_compile_logs_loki(ctx)
        return {"event": "Compiled Request Traces", "data": {"traces_compiled": 0}}

    def _step4_compile_logs_file_based(self, ctx: PipelineContext) -> Dict[str, Any]:
        """STEP 4 (file-based): Compile logs for each trace ID from local files."""
        ctx.compiled = {}
        summary_counts: Dict[str, int] = {}

        for trace_id in ctx.unique_ids:
            entries: List[Dict[str, Any]] = []
            timeline: List[Dict[str, Any]] = []
            source_files: List[str] = []

            for lf in ctx.log_files:
                result = self.full_log_finder.find_all_logs_for_trace(lf, trace_id)
                if result.get("total_entries", 0) > 0:
                    source_files.append(str(lf))
                    entries.extend(result.get("log_entries", []))
                    timeline.extend(result.get("timeline", []))

            ctx.compiled[trace_id] = {
                "log_entries": entries,
                "timeline": timeline,
                "source_files": source_files,
                "total_entries": len(entries),
            }
            summary_counts[trace_id] = len(entries)

        logger.info({"traces_compiled": len(summary_counts), "entries_per_trace": summary_counts})
        return {"event": "Compiled Request Traces", "data": {"traces_compiled": len(summary_counts)}}

    async def _step4_compile_logs_loki(self, ctx: PipelineContext) -> Dict[str, Any]:
        """STEP 4 (Loki): Gather logs for each trace ID from Loki."""
        ctx.log_files = await run_in_threadpool(
            gather_logs_for_trace_ids,
            filters={"service_namespace": ctx.project.lower()},
            trace_ids=ctx.unique_ids,
            date_str=ctx.search_date,
            end_date_str=ctx.end_date_str
        )
        logger.info({"traces_compiled": len(ctx.log_files), "trace_log_files": ctx.log_files})
        return {"event": "Compiled Request Traces", "data": {"traces_compiled": len(ctx.log_files)}}

    def _step5_analyze_and_generate_reports(self, ctx: PipelineContext) -> Dict[str, Any]:
        """STEP 5: Analyze and generate reports - dispatches to file-based or Loki-based."""
        logger.info("STEP 5: Verification & file gen…")
        if is_file_based(ctx.project):
            return self._step5_analyze_file_based(ctx)
        elif is_loki_based(ctx.project):
            return self._step5_analyze_loki(ctx)
        return {"event": "Compiled Summary", "data": {"created_files": [], "master_summary_file": ""}}

    def _step5_analyze_file_based(self, ctx: PipelineContext) -> Dict[str, Any]:
        """STEP 5 (file-based): Generate comprehensive analysis files."""
        result = self.analyze_agent.analyze_and_create_comprehensive_files(
            original_context=ctx.text,
            search_results={"unique_trace_ids": ctx.unique_ids},
            trace_data={"all_trace_data": ctx.compiled},
            parameters=ctx.params,
            output_prefix="banking_analysis",
            cache_policy=ctx.cache_policy,
        )
        ctx.report_files = result.get("comprehensive_files_created", [])
        ctx.master_report = result.get("master_summary_file", "")
        return {
            "event": "Compiled Summary",
            "data": {"created_files": ctx.report_files, "master_summary_file": ctx.master_report}
        }

    def _step5_analyze_loki(self, ctx: PipelineContext) -> Dict[str, Any]:
        """STEP 5 (Loki): Analyze downloaded log files."""
        result = self.analyze_agent.analyze_log_files(
            log_file_paths=ctx.log_files,
            dispute_text=ctx.text,
            search_params=ctx.params,
            cache_policy=ctx.cache_policy,
        )
        ctx.report_files = result["individual_reports"]
        ctx.master_report = result["master_report"]
        return {
            "event": "Compiled Summary",
            "data": {"created_files": ctx.report_files, "master_summary_file": ctx.master_report}
        }

    def _step6_verify(self, ctx: PipelineContext) -> Dict[str, Any]:
        """STEP 6: Run verification agents and generate final report."""
        logger.info("STEP 6: Running verify agents with parameters and original text…")

        results = self.verify_agent.analyze_batch_relevance(
            original_text=ctx.text,
            parameters=ctx.params,
            trace_files=ctx.report_files,
            cache_policy=ctx.cache_policy,
        )

        output_file = self.verify_agent.export_results_to_file(results)
        summary_string = self.verify_agent.get_verification_summary_string(output_file)

        return {"event": "Verification Results", "data": summary_string}
