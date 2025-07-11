import logging
from pathlib import Path
from ollama import Client
from agents.parameter_agent import ParametersAgent
from agents.file_searcher import FileSearcher

logger = logging.getLogger(__name__)


class Orchestrator:
    """Runs ParametersAgent and FileSearcher to find relevant log files."""

    def __init__(self, client: Client, model: str, log_base_dir: str = "./data"):
        self.param_agent = ParametersAgent(client, model)
        self.file_searcher = FileSearcher(Path(log_base_dir), client, model)

    def analyze(self, text: str):
        # Hardcode parameters for testing FileSearcher
        params = {
            'time_frame': '06.11.2024',
            'domain': 'NPSB, BEFTN',
            'query_keys': ['112013800000010', '114412200000042']
        }

        logger.info("Using hardcoded parameters: %s", params)

        # Hardcode log file search
        logger.info("Searching for log file...")
        log_file = self.file_searcher.find_and_verify(params)

        if log_file:
            logger.info("Found log file: %s", log_file)
            return {
                'parameters': params,
                'log_file': str(log_file)
            }
        else:
            logger.warning("No suitable log file found")
            return {
                'parameters': params,
                'log_file': None
            }