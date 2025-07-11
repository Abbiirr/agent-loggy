#!/usr/bin/env python3
"""
parameters_agent.py

Improved version with better prompt engineering and robust parsing
"""

import json
import logging
import sys
import re

import httpx
from ollama import Client

# ---- CONFIGURATION ----
OLLAMA_HOST = "http://localhost:11434"

# ---- LOGGING SETUP ----
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---- HEALTH CHECK ----
def is_ollama_running(host: str = OLLAMA_HOST) -> bool:
    """Return True if Ollama daemon responds on the root endpoint."""
    try:
        resp = httpx.get(f"{host}/", timeout=2.0)
        return resp.status_code == 200 and "Ollama is running" in resp.text
    except httpx.RequestError:
        return False


# ---- AGENT BASE ----
class Agent:
    """Base class for all agents."""

    def __init__(self, client: Client, name: str):
        self.client = client
        self.name = name

    def run(self, **kwargs):
        raise NotImplementedError


# ---- PARAMETERS AGENT ----
class ParametersAgent(Agent):
    """
    Extracts search parameters from text with improved parsing
    """

    def __init__(self, client: Client, model: str = None):
        super().__init__(client, name="ParametersAgent")
        self.model = model or self._pick_default_model()
        logger.info("Using Ollama model: %s", self.model)

    def _pick_default_model(self) -> str:
        """Return the first installed model, or exit if none."""
        models = self.client.list()
        if not models or not models.get('models'):
            logger.critical("No Ollama models installed. Pull one with `ollama pull <model>`. ")
            sys.exit(1)
        return models['models'][0]['model']

    def run(self, text: str) -> dict:
        # More detailed and clearer prompt
        system_msg = """You are a log analysis parameter extractor. 
Your job is to extract key information from user text for searching logs.

Extract these specific parameters:
1. time_frame: Any dates, times, or time ranges mentioned (e.g., "06.11.2024", "last hour", "yesterday")
2. domain: Business domains or systems mentioned (e.g., "NPSB", "BEFTN", "fundtransfer", "payment", "bkash", "qr")
3. query_keys: Important search terms like account numbers, transaction IDs, amounts, error codes, user names

Return your answer in this exact format:
TIME_FRAME: [extracted time information]
DOMAIN: [extracted domains, comma-separated]
QUERY_KEYS: [important search terms, comma-separated]

Be specific and extract actual values from the text."""

        user_msg = f"Extract parameters from this text:\n\n{text}"

        logger.info("Requesting parameters extraction...")
        resp = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
        )

        raw = resp["message"]["content"].strip()
        logger.info("LLM raw output: %s", raw)

        # Parse the structured response
        return self._parse_structured_response(raw)

    def _parse_structured_response(self, response: str) -> dict:
        """Parse the structured response format"""
        result = {
            "time_frame": "",
            "domain": "",
            "query_keys": []
        }

        lines = response.split('\n')
        for line in lines:
            line = line.strip()

            if line.startswith("TIME_FRAME:"):
                result["time_frame"] = line.replace("TIME_FRAME:", "").strip()
            elif line.startswith("DOMAIN:"):
                domain_text = line.replace("DOMAIN:", "").strip()
                result["domain"] = domain_text
            elif line.startswith("QUERY_KEYS:"):
                keys_text = line.replace("QUERY_KEYS:", "").strip()
                if keys_text:
                    result["query_keys"] = [key.strip() for key in keys_text.split(',') if key.strip()]

        # Fallback: try to extract from free-form text if structured parsing fails
        if not any([result["time_frame"], result["domain"], result["query_keys"]]):
            logger.warning("Structured parsing failed, trying fallback extraction")
            return self._fallback_extraction(response)

        return result

    def _fallback_extraction(self, text: str) -> dict:
        """Fallback extraction using regex patterns"""
        result = {
            "time_frame": "",
            "domain": "",
            "query_keys": []
        }

        # Extract dates (DD.MM.YYYY format)
        date_pattern = r'\b\d{1,2}\.\d{1,2}\.\d{4}\b'
        dates = re.findall(date_pattern, text)
        if dates:
            result["time_frame"] = dates[0]

        # Extract domains (known business domains)
        domain_keywords = ["NPSB", "BEFTN", "fundtransfer", "payment", "bkash", "qr", "fund transfer"]
        found_domains = []
        text_upper = text.upper()
        for domain in domain_keywords:
            if domain.upper() in text_upper:
                found_domains.append(domain)
        if found_domains:
            result["domain"] = ", ".join(found_domains)

        # Extract account numbers (pattern: digits)
        account_pattern = r'\b\d{10,}\b'
        accounts = re.findall(account_pattern, text)

        # Extract amounts
        amount_pattern = r'\b\d{1,3}(?:,\d{3})*(?:\.\d{2})?\b'
        amounts = re.findall(amount_pattern, text)

        query_keys = []
        query_keys.extend(accounts)
        query_keys.extend(amounts)

        # Add some context keywords
        context_keywords = ["failed", "debited", "transaction", "discrepancy"]
        for keyword in context_keywords:
            if keyword.lower() in text.lower():
                query_keys.append(keyword)

        result["query_keys"] = list(set(query_keys))  # Remove duplicates

        return result


# ---- MAIN SCRIPT ----
if __name__ == "__main__":
    # 1) Health check
    if not is_ollama_running():
        logger.critical("Ollama server is not running! Start it with `ollama serve`. ")
        sys.exit(1)
    logger.info("Ollama is running and reachable.")

    # 2) Instantiate client and agent
    client = Client(host=OLLAMA_HOST)
    pa = ParametersAgent(client, model="deepseek-r1:8b")

    # 3) Example input text
    user_text = (
        "Please be informed that Mr. Md. Mahadi Hasan holds two accounts with Modhumoti Bank PLC "
        "(Account No. 112013800000010 and Account No. 114412200000042). "
        "On 06.11.2024, he executed two transactions via the GO SMART app—an NPSB transaction of 50,000 "
        "and a BEFTN transaction of 50,000. Both were marked as failed in the GO SMART admin panel logs, "
        "but amounts were debited according to the Bank Ultimas report. Investigate and explain the discrepancy."
    )

    # 4) Run agent and print results
    extracted = pa.run(user_text)
    print("\nExtracted parameters:")
    print(f"  time_frame : '{extracted['time_frame']}'")
    print(f"  domain     : '{extracted['domain']}'")
    print(f"  query_keys : {extracted['query_keys']}")