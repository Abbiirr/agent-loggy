# orchestrator.py
import asyncio
import logging
import json
import uuid
from pathlib import Path
from typing import Dict, List, Any

from ollama import Client
from app.agents.parameter_agent import ParametersAgent
from app.agents.file_searcher import FileSearcher
from app.tools.log_searcher import LogSearcher
from app.tools.full_log_finder import FullLogFinder
from app.agents.analyze_agent import AnalyzeAgent
from app.agents.verify_agent import RelevanceAnalyzerAgent
from app.tools.loki.loki_trace_id_extractor import gather_logs_for_trace_ids, extract_trace_ids
from app.tools.loki.loki_query_builder import download_logs
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from app.tools.loki.loki_log_report_generator import generate_comprehensive_report, parse_loki_json
import csv

from app.services.project_service import is_file_based, is_loki_based

logger = logging.getLogger(__name__)

NEGATE_RULES_PATH = "app_settings/negate_keys.csv"


class Orchestrator:
    """
    Enhanced Orchestrator with streaming support for SSE.
    """

    def __init__(self, client: Client, model: str, log_base_dir: str = "./data"):
        self.param_agent = ParametersAgent(client, model)
        self.file_searcher = FileSearcher(Path(log_base_dir), client, model)
        self.log_searcher = LogSearcher(context=2)
        self.full_log_finder = FullLogFinder()
        self.analyze_agent = AnalyzeAgent(client, model, output_dir="app/comprehensive_analysis")
        self.verify_agent = RelevanceAnalyzerAgent(client, model, output_dir="app/verification_reports")

    async def analyze_stream(self, text: str, project: str, env: str, domain: str) -> Dict[str, Any]:
        # 1) Read negate keys from a CSV file (one key per row, no header)
        negate_keys = []
        try:
            with open(NEGATE_RULES_PATH, newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                # Skip the header row
                next(reader, None)
                for row in reader:
                    # Ensure we have at least 3 columns: label, operator, value
                    if len(row) >= 3:
                        term = row[2].strip()
                        if term:
                            negate_keys.append(term)
        except FileNotFoundError:
            logger.warning(f"Negation rules file not found at {NEGATE_RULES_PATH}")
        except Exception as e:
            logger.error(f"Error reading negate rules: {e}")

        # STEP 1: Parameter extraction
        logger.info("STEP 1: Parameter extraction…")
        params = self.param_agent.run(text)
        logger.info("Extracted parameters: %s", json.dumps(params, indent=2))
        yield "Extracted Parameters", {"parameters": params}
        await asyncio.sleep(0)
        # params = {
        #     "domain": "transactions",
        #     "query_keys": ["bkash"],
        #     "time_frame": "2025-07-24"
        # }
        # yield "Extracted Parameters", {"parameters": params}
        await asyncio.sleep(0)
        # STEP 2: File search
        log_files = []
        unique_filename = ""
        search_date = ""
        end_date_str = ""
        if is_file_based(project):
            logger.info("STEP 2: File search…")  # structured logging :contentReference[oaicite:10]{index=10}
            log_files = self.file_searcher.find_and_verify(params)
            files = [str(f) for f in log_files]
            logger.info({"found_files": files, "total_files": len(files)})
            yield "Found relevant files", {"total_files": len(files)}
            await asyncio.sleep(0)  # yield control without blocking :contentReference[oaicite:11]{index=11}

        elif is_loki_based(project):
            logger.info("STEP 2: Loki search…")
            query_keys = params.get("query_keys", [])
            search_date = params.get("time_frame")
            search_dt = date_parser.parse(search_date)
            end_dt = search_dt + timedelta(days=1)
            end_date_str = end_dt.date().isoformat()
            unique_filename = f"app/loki_logs/{project}{env}_{search_date}_{uuid.uuid4().hex}.json"
            pipeline = [f'!= "{term}"' for term in negate_keys]
            download_logs(
                filters={"service_namespace": project.lower()},
                search=query_keys,
                date_str=search_date,
                end_date_str=end_date_str,
                output=unique_filename,
                pipeline=pipeline
            )
            logger.info(f"Downloaded logs to {unique_filename}")
            yield "Downloaded logs in file", {}
            await asyncio.sleep(0)

        # STEP 3: Trace ID collection
        logger.info("STEP 3: Trace ID collection…")
        unique_ids = []
        if is_file_based(project):
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

        elif is_loki_based(project):
            unique_ids = extract_trace_ids(unique_filename)
            logger.info({"unique_ids": unique_ids})
            yield "Found trace id(s)", {"count": len(unique_ids)}
            await asyncio.sleep(0)

        # STEP 4: Compilation summary
        logger.info("STEP 4: Compiling full logs…")

        if is_file_based(project):

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

        elif is_loki_based(project):
            # — new branch using gather_logs_for_trace_ids —
            # If gather_logs_for_trace_ids is blocking I/O, you can offload it:
            log_files: List[str] = await asyncio.to_thread(
                gather_logs_for_trace_ids,
                filters={"service_namespace": project.lower()},
                trace_ids=unique_ids,
                date_str=search_date,
                end_date_str=end_date_str
            )
            logger.info({
                "traces_compiled": len(log_files),
                "trace_log_files": log_files
            })
            yield "Compiled Request Traces", {
                "traces_compiled": len(log_files)
            }
            await asyncio.sleep(0)

        # STEP 5: Verification summary
        logger.info("STEP 5: Verification & file gen…")
        report_files = []  # Initialize report_files
        master_report = ""  # Initialize master_report

        if is_file_based(project):
            result = self.analyze_agent.analyze_and_create_comprehensive_files(
                original_context=text,
                search_results={"unique_trace_ids": unique_ids},
                trace_data={"all_trace_data": compiled},
                parameters=params,
                output_prefix="banking_analysis"
            )
            report_files = result.get("comprehensive_files_created", [])
            master_report = result.get("master_summary_file", "")
            yield "Compiled Summary", {
                "created_files": report_files,
                "master_summary_file": master_report
            }
            await asyncio.sleep(0)

        elif is_loki_based(project):
            result = self.analyze_agent.analyze_log_files(
                log_file_paths=log_files,
                dispute_text=text,
                search_params=params
            )
            report_files = result["individual_reports"]
            master_report = result["master_report"]
            yield "Compiled Summary", {
                "created_files": report_files,
                "master_summary_file": master_report
            }
            await asyncio.sleep(0)

        # STEP 6: Run verify agents and write results to file
        logger.info("STEP 6: Running verify agents with parameters and original text…")

        # 1) Run the relevance analysis
        results = self.verify_agent.analyze_batch_relevance(
            original_text=text,
            parameters=params,
            trace_files=report_files
        )

        # 2) Export to disk, returning only the filename/path
        output_file = self.verify_agent.export_results_to_file(results)

        # 3) Generate the complete summary string and yield it
        summary_string = self.verify_agent.get_verification_summary_string(output_file)
        yield "Verification Results", summary_string

        # output_file = "app\\verification_reports\\relevance_analysis_20250724_121257.json"

        # 3) Generate the complete summary string and yield it
        # summary_string = self.verify_agent.get_verification_summary_string(output_file)
        # yield "Verification Results", summary_string
        await asyncio.sleep(0)


        # DONE
        logger.info("Analysis complete.")
        yield "done", {"message": "Analysis complete."}
