# orchestrator.py
import asyncio
import logging
import json
from pathlib import Path
from typing import Dict, List, Any

from ollama import Client
from agents.parameter_agent import ParametersAgent
from agents.file_searcher import FileSearcher
from tools.log_searcher import LogSearcher
from tools.full_log_finder import FullLogFinder
from agents.verify_agent import VerifyAgent

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Enhanced Orchestrator with streaming support for SSE.
    """

    def __init__(self, client: Client, model: str, log_base_dir: str = "./data"):
        self.param_agent = ParametersAgent(client, model)
        self.file_searcher = FileSearcher(Path(log_base_dir), client, model)
        self.log_searcher = LogSearcher(context=2)
        self.full_log_finder = FullLogFinder()
        self.verify_agent = VerifyAgent(client, model, output_dir="comprehensive_analysis")

    async def analyze_stream(self, text: str):
        # # STEP 1: Parameter extraction
        # logger.info("STEP 1: Parameter extraction…")
        # params = self.param_agent.run(text)
        # yield "Extracted Parameters", {"parameters": params}
        # await asyncio.sleep(0)
        #
        # # STEP 2: File search
        # logger.info("STEP 2: File search…")
        # log_files = self.file_searcher.find_and_verify(params)
        # files = [str(f) for f in log_files]
        # yield "Found relevant files", {"found_files": files, "total_files": len(files)}
        # await asyncio.sleep(0)
        #
        # # STEP 3: Trace ID collection
        # logger.info("STEP 3: Trace ID collection…")
        # patterns = params.get("query_keys", [])
        # unique_ids: List[str] = []
        # for lf in log_files:
        #     for r in self.log_searcher.search_with_trace_ids(lf, patterns):
        #         tid = r.get("trace_id")
        #         if tid and tid not in unique_ids:
        #             unique_ids.append(tid)
        # yield "Found trace id(s)", {"found_trace_ids": unique_ids, "count": len(unique_ids)}
        # await asyncio.sleep(0)
        #
        # # STEP 4: Compilation summary
        # logger.info("STEP 4: Compiling full logs…")
        # compiled: Dict[str, Dict[str, Any]] = {}
        # summary_counts: Dict[str, int] = {}
        #
        # for trace_id in unique_ids:
        #     entries: List[Dict[str, Any]] = []
        #     timeline: List[Dict[str, Any]] = []
        #     source_files: List[str] = []
        #
        #     # Gather from each file
        #     for lf in log_files:
        #         result = self.full_log_finder.find_all_logs_for_trace(lf, trace_id)
        #         if result.get("total_entries", 0) > 0:
        #             source_files.append(str(lf))
        #             entries.extend(result.get("log_entries", []))
        #             timeline.extend(result.get("timeline", []))
        #
        #     compiled[trace_id] = {
        #         "log_entries": entries,
        #         "timeline": timeline,
        #         "source_files": source_files,
        #         "total_entries": len(entries),
        #     }
        #     summary_counts[trace_id] = len(entries)
        #
        # yield "Compiled Request Traces", {
        #     "traces_compiled": len(summary_counts),
        #     "entries_per_trace": summary_counts
        # }
        # await asyncio.sleep(0)

        # STEP 5: Verification summary
        logger.info("STEP 5: Verification & file gen…")
        # result = self.verify_agent.analyze_and_create_comprehensive_files(
        #     original_context=text,
        #     search_results={"unique_trace_ids": unique_ids},
        #     trace_data={"all_trace_data": compiled},
        #     parameters=params,
        #     output_prefix="banking_analysis"
        # )
        yield "Compiled Summary", {
            "created_files": [
                "K:\\projects\\ai\\agent-loggy\\comprehensive_analysis\\banking_analysis_trace_e9706b05-7e8e-4025-b70c-a3028532daa9_20250719_170418.txt",
                "K:\\projects\\ai\\agent-loggy\\comprehensive_analysis\\banking_analysis_trace_593a8560-91e7-4305-aff8-8b7b4f2fbe6d_20250719_170443.txt",
                "K:\\projects\\ai\\agent-loggy\\comprehensive_analysis\\banking_analysis_trace_68184aaf-819a-466b-8450-b64dda7301cc_20250719_170505.txt",
                "K:\\projects\\ai\\agent-loggy\\comprehensive_analysis\\banking_analysis_trace_04f67a7f-6c20-4849-b24e-735b1d30b91f_20250719_170536.txt",
                "K:\\projects\\ai\\agent-loggy\\comprehensive_analysis\\banking_analysis_trace_8a9f15fd-2447-4faf-81d5-3295f6081f84_20250719_170603.txt",
                "K:\\projects\\ai\\agent-loggy\\comprehensive_analysis\\banking_analysis_trace_92e1f051-f275-4133-ad29-61289b0b264a_20250719_170626.txt",
                "K:\\projects\\ai\\agent-loggy\\comprehensive_analysis\\banking_analysis_trace_23a7a0f8-ff3a-45bb-ab99-0c168abd5c33_20250719_170647.txt",
                "K:\\projects\\ai\\agent-loggy\\comprehensive_analysis\\banking_analysis_trace_b4ac2069-bfd5-47cf-9e87-8e97518b9242_20250719_170720.txt"
            ],
            "master_summary_file": "K:\\projects\\ai\\agent-loggy\\comprehensive_analysis\\banking_analysis_trace_b4ac2069-bfd5-47cf-9e87-8e97518b9242_20250719_170720.txt"
        }
        await asyncio.sleep(0)

        # DONE
        yield "done", {"message": "Analysis complete."}
