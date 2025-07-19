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
        # STEP 1: Parameter extraction
        logger.info("STEP 1: Parameter extraction…")
        params = self.param_agent.run(text)
        yield "params", {"parameters": params}
        await asyncio.sleep(0)

        # STEP 2: File search
        logger.info("STEP 2: File search…")
        log_files = self.file_searcher.find_and_verify(params)
        files = [str(f) for f in log_files]
        yield "files", {"found_files": files, "total_files": len(files)}
        await asyncio.sleep(0)

        # STEP 3: Trace ID collection
        logger.info("STEP 3: Trace ID collection…")
        patterns = params.get("query_keys", [])
        unique_ids: List[str] = []
        for lf in log_files:
            for r in self.log_searcher.search_with_trace_ids(lf, patterns):
                tid = r.get("trace_id")
                if tid and tid not in unique_ids:
                    unique_ids.append(tid)
        yield "trace_ids", {"found_trace_ids": unique_ids, "count": len(unique_ids)}
        await asyncio.sleep(0)

        # STEP 4: Compilation summary
        logger.info("STEP 4: Compiling full logs…")
        compiled: Dict[str, Dict[str, Any]] = {}
        summary_counts: Dict[str, int] = {}

        for trace_id in unique_ids:
            entries: List[Dict[str, Any]] = []
            timeline: List[Dict[str, Any]] = []
            source_files: List[str] = []

            # Gather from each file
            for lf in log_files:
                result = self.full_log_finder.find_all_logs_for_trace(lf, trace_id)
                if result.get("total_entries", 0) > 0:
                    source_files.append(str(lf))
                    entries.extend(result.get("log_entries", []))
                    timeline.extend(result.get("timeline", []))

            compiled[trace_id] = {
                "log_entries": entries,
                "timeline": timeline,
                "source_files": source_files,
                "total_entries": len(entries),
            }
            summary_counts[trace_id] = len(entries)

        yield "compiled_summary", {
            "traces_compiled": len(summary_counts),
            "entries_per_trace": summary_counts
        }
        await asyncio.sleep(0)

        # STEP 5: Verification summary
        # logger.info("STEP 5: Verification & file gen…")
        # result = self.verify_agent.analyze_and_create_comprehensive_files(
        #     original_context=text,
        #     search_results={"unique_trace_ids": unique_ids},
        #     trace_data={"all_trace_data": compiled},
        #     parameters=params,
        #     output_prefix="banking_analysis"
        # )
        # yield "verification_summary", {
        #     "created_files": result.get("comprehensive_files_created", []),
        #     "master_summary_file": result.get("master_summary_file")
        # }
        # await asyncio.sleep(0)

        # DONE
        yield "done", {"message": "Analysis complete."}

