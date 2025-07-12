import logging
from pathlib import Path
from ollama import Client
from agents.verify_agent import VerifyAgent

logger = logging.getLogger(__name__)

class Orchestrator:
    def __init__(self, client: Client, model: str, log_base_dir: str = "./data"):
        self.verify_agent = VerifyAgent(client, model)

    def analyze(self, text: str):
        # --- HARDCODED DATA FOR STEPS 1-4 ---
        params = {
            'time_frame': '06.11.2024',
            'domain': 'NPSB, BEFTN',
            'query_keys': ['112013800000010', '114412200000042']
        }
        log_files = [
            'data/NPSB_Dispute_06_11_24/NPSB_Dispute_06_11_24/trace.log.2024-11-06.11',
            'data/NPSB_Dispute_06_11_24/NPSB_Dispute_06_11_24/trace.log.2024-11-06.12.xz'
        ]
        search_results = {
            'files_searched': log_files,
            'patterns': params['query_keys'],
            'matches': ['<log-row>...</log-row>'],  # Example match
            'total_matches': 1,
            'trace_ids': [{'match': '<log-row>...</log-row>', 'trace_id': 'e9706b05-7e8e-4025-b70c-a3028532daa9'}],
            'unique_trace_ids': ['e9706b05-7e8e-4025-b70c-a3028532daa9'],
            'total_files': len(log_files)
        }
        file_creation_result = {
            'unique_trace_ids': ['e9706b05-7e8e-4025-b70c-a3028532daa9'],
            'total_unique_traces': 1,
            'files_created': ['trace_outputs/comprehensive_trace_e9706b05-7e8e-4025-b70c-a3028532daa9.txt'],
            'output_directory': "trace_outputs",
            'comprehensive_search': True,
            'files_searched_per_trace': len(log_files),
            'all_trace_data': {
                'e9706b05-7e8e-4025-b70c-a3028532daa9': {
                    'trace_id': 'e9706b05-7e8e-4025-b70c-a3028532daa9',
                    'total_entries': 3,
                    'log_entries': [],
                    'timeline': [],
                    'source_files': log_files,
                    'files_searched': len(log_files),
                    'files_with_entries': 2
                }
            }
        }
        trace_analysis = file_creation_result['all_trace_data']['e9706b05-7e8e-4025-b70c-a3028532daa9']

        # --- ONLY TEST STEP 5 ---
        logger.info("Step 5: Running Verify Agent...")

        verification_results = self.verify_agent.analyze_and_verify_concise(
            original_context=text,
            search_results=search_results,
            trace_data={'all_trace_data': file_creation_result['all_trace_data']},
            parameters=params
        )

        logger.info(f"Verification complete. Confidence: {verification_results['confidence_score']}/100")
        logger.info(f"Further search needed: {verification_results['further_search_needed']['decision']}")

        return {
            'parameters': params,
            'log_files': log_files,
            'total_files': len(log_files),
            'search_results': search_results,
            'file_creation_result': file_creation_result,
            'trace_analysis': trace_analysis,
            'verification_results': verification_results
        }