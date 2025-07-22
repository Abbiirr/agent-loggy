# orchestrator.py
import asyncio
import logging
import json
import uuid
from pathlib import Path
from typing import Dict, List, Any

from ollama import Client
from agents.parameter_agent import ParametersAgent
from agents.file_searcher import FileSearcher
from tools.log_searcher import LogSearcher
from tools.full_log_finder import FullLogFinder
from agents.verify_agent import VerifyAgent
from tools.loki.loki_trace_id_extractor import gather_logs_for_trace_ids, extract_trace_ids
from tools.loki.loki_query_builder import download_logs
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from tools.loki.loki_log_report_generator import generate_comprehensive_report, parse_loki_json

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

    async def analyze_stream(self, text: str, project: str , env: str ) -> Dict[str, Any]:
        # STEP 1: Parameter extraction
        logger.info("STEP 1: Parameter extraction…")
        # params = self.param_agent.run(text)
        # yield "Extracted Parameters", {"parameters": params}
        # await asyncio.sleep(0)
        params = {
            "domain": "transactions",
            "query_keys": ["merchant"],
            "time_frame": "2025-07-15"
        }
        yield "Extracted Parameters", {"parameters": params}
        # STEP 2: File search
        log_files = []
        unique_filename = ""
        search_date = ""
        end_date_str = ""
        if project in ("MMBL", "UCB"):  # membership test replaces '||' :contentReference[oaicite:9]{index=9}
            logger.info("STEP 2: File search…")  # structured logging :contentReference[oaicite:10]{index=10}
            log_files = self.file_searcher.find_and_verify(params)
            files = [str(f) for f in log_files]
            logger.info({"found_files": files, "total_files": len(files)})
            yield "Found relevant files", {"total_files": len(files)}
            await asyncio.sleep(0)  # yield control without blocking :contentReference[oaicite:11]{index=11}

        elif project in ("NCC", "ABBL"):
            logger.info("STEP 2: Loki search…")
            query_keys = params.get("query_keys", [])
            search_date = params.get("time_frame")
            search_dt = date_parser.parse(search_date)
            end_dt = search_dt + timedelta(days=1)
            end_date_str = end_dt.date().isoformat()
            unique_filename = f"{project}{env}_{search_date}_{uuid.uuid4().hex}.json"
            download_logs(
                filters={"service_namespace": project.lower()},
                search=query_keys,
                date_str=search_date,
                end_date_str=end_date_str,
                output=unique_filename
            )
            logger.info(f"Downloaded logs to {unique_filename}")
            yield "Downloaded logs in file", {}
            await asyncio.sleep(0)

        # STEP 3: Trace ID collection
        logger.info("STEP 3: Trace ID collection…")
        unique_ids = []
        if project in ("MMBL", "UCB"):  # membership test replaces '||' :contentReference[oaicite:9]{index=9}
            patterns = params.get("query_keys", [])
            unique_ids: List[str] = []
            for lf in log_files:
                for r in self.log_searcher.search_with_trace_ids(lf, patterns):
                    tid = r.get("trace_id")
                    if tid and tid not in unique_ids:
                        unique_ids.append(tid)
            logger.info({"unique_ids": unique_ids})
            yield "Found trace id(s)", {"count": len(unique_ids)}
            await asyncio.sleep(0)

        elif project in ("NCC", "ABBL"):
            unique_ids = extract_trace_ids(unique_filename)
            logger.info({"unique_ids": unique_ids})
            yield "Found trace id(s)", {"count": len(unique_ids)}
            await asyncio.sleep(0)


        # STEP 4: Compilation summary
        logger.info("STEP 4: Compiling full logs…")

        if project in ("MMBL", "UCB"):

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
            logger.info({
                "traces_compiled": len(summary_counts),
                "entries_per_trace": summary_counts
            })
            yield "Compiled Request Traces", {
                "traces_compiled": len(summary_counts)
            }
            await asyncio.sleep(0)

        elif project in ("NCC", "ABBL"):
            # — new branch using gather_logs_for_trace_ids —
            # If gather_logs_for_trace_ids is blocking I/O, you can offload it:
            log_files: List[str] = await asyncio.to_thread(
                gather_logs_for_trace_ids,
                filters={"service_namespace": project.lower()},
                trace_ids=unique_ids,
                date_str=search_date,
                end_date_str=end_date_str
            )
            logger.info( {
                "traces_compiled": len(log_files),
                "trace_log_files": log_files
            })
            yield "Compiled Request Traces", {
                "traces_compiled": len(log_files)
            }
            await asyncio.sleep(0)

        # STEP 5: Verification summary
        logger.info("STEP 5: Verification & file gen…")
        if project in ("MMBL", "UCB"):  # membership test replaces '||' :contentReference[oaicite:9]{index=9}
            result = self.verify_agent.analyze_and_create_comprehensive_files(
                original_context=text,
                search_results={"unique_trace_ids": unique_ids},
                trace_data={"all_trace_data": compiled},
                parameters=params,
                output_prefix="banking_analysis"
            )
            yield "Compiled Summary", {
                "created_files": result.get("comprehensive_files_created", []),
                "master_summary_file": result.get("master_summary_file")
            }
            await asyncio.sleep(0)


        elif project in ("NCC", "ABBL"):
            # result = self.verify_agent.analyze_log_files(
            #     log_file_paths=log_files,
            #     dispute_text=text,
            #     search_params=params
            # )
            # 3) Single final yield with all report paths
            yield "Compiled Summary", {
                "created_files": [
                    r"comprehensive_analysis\trace_report_e5143955f01d_20250722_112625.txt",
                    r"comprehensive_analysis\trace_report_5c62b722e862_20250722_112650.txt",
                    r"comprehensive_analysis\trace_report_8a2e1fbc850b_20250722_112713.txt",
                    r"comprehensive_analysis\trace_report_70a617667014_20250722_112729.txt",
                    r"comprehensive_analysis\trace_report_6dcac4a5b100_20250722_112749.txt"
                ],
                "master_summary_file": r"comprehensive_analysis\master_summary_20250722_112749.txt"
            }

            await asyncio.sleep(0)


    # DONE
        logger.info("Analysis complete.")
        yield "done", {"message": "Analysis complete."}
