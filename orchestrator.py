import logging
from ollama import Client
from agents.parameter_agent import ParametersAgent

logger = logging.getLogger(__name__)

class Orchestrator:
    """Runs only the ParametersAgent for now."""
    def __init__(self, client: Client, model: str):
        self.param_agent = ParametersAgent(client, model)

    def analyze(self, text: str):
        logger.info("Extracting parameters...")
        params = self.param_agent.run(text)
        logger.info("Extracted parameters: %s", params)
        return params