import json
import logging
import re
import sys

import httpx
from ollama import Client

logger = logging.getLogger(__name__)

# ---- CONFIGURATION ----
OLLAMA_HOST = "http://localhost:11434"
DOMAIN_KEYWORDS = ["NPSB", "BEFTN", "FUNDFTRANSFER", "PAYMENT", "BKASH", "QR"]

# ---- HEALTH CHECK ----
def is_ollama_running(host: str = OLLAMA_HOST) -> bool:
    """Return True if Ollama daemon responds on the root endpoint."""
    try:
        resp = httpx.get(f"{host}/", timeout=2.0)
        return resp.status_code == 200 and "Ollama is running" in resp.text
    except Exception:
        return False

class ParametersAgent:
    """Extracts `time_frame`, `domain`, and `query_keys` from text."""
    def __init__(self, client: Client, model: str):
        self.client = client
        self.model = model
        logger.info("ParametersAgent using model: %s", model)

    def run(self, text: str) -> dict:
        if not is_ollama_running():
            logger.critical("Ollama server is not running. Start it with 'ollama serve'.")
            sys.exit(1)

        prompt = (
            "You are a parameter extractor. Output valid JSON with keys: time_frame, domain, query_keys."
            f"\nUser text: {text}"
        )
        resp = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
            ],
        )
        raw = resp["message"]["content"].strip()
        logger.debug("Raw parameters output: %s", raw)
        try:
            params = json.loads(raw)
        except json.JSONDecodeError:
            logger.error("JSON parse error, falling back to regex extraction.")
            params = self._fallback(text)

        # Enforce DOMAIN_KEYWORDS
        text_upper = text.upper()
        forced = [kw for kw in DOMAIN_KEYWORDS if kw in text_upper]
        if forced:
            existing = [d.strip() for d in params.get("domain", "").split(",") if d.strip()]
            params["domain"] = ", ".join(dict.fromkeys(forced + existing))
        print(params)
        return params

    def _fallback(self, text: str) -> dict:
        # Simple regex-based fallback extraction
        result = {"time_frame": "", "domain": "", "query_keys": []}
        date_match = re.search(r"\b\d{1,2}\.\d{1,2}\.\d{4}\b", text)
        if date_match:
            result["time_frame"] = date_match.group(0)
        # domain keywords
        found = [kw for kw in DOMAIN_KEYWORDS if kw in text.upper()]
        if found:
            result["domain"] = ", ".join(found)
        # account numbers
        accounts = re.findall(r"\b\d{10,}\b", text)
        result["query_keys"] = accounts
        return result