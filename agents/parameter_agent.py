import json
import logging
import regex as re
import sys

import httpx
from dateutil import parser as date_parser
from ollama import Client

logger = logging.getLogger(__name__)

# ---- CONFIGURATION ----
OLLAMA_HOST = "http://localhost:11434"
DOMAIN_KEYWORDS = ["NPSB", "BEFTN", "FUNDFTRANSFER", "PAYMENT", "BKASH", "QR"]
allowed_query_keys = [
    "merchant", "amount", "transaction_id", "customer_id",
    "mfs", "bkash", "nagad", "upay", "rocket", "qr", "npsb", "beftn",
    "fund_transfer", "payment", "balance", "fee", "status",
    "product_id", "category", "rating", "review_text", "user_id"
]

excluded_query_keys = [
    "password", "token", "secret", "api_key", "private_key",
    "internal_id", "system_log", "debug_info", "date", "amount"
]

allowed_domains = [
    "transactions", "customers", "users", "products", "reviews",
    "payments", "merchants", "accounts", "orders", "analytics"
]

excluded_domains = [
    "system", "logs", "admin", "security", "internal",
    "debug", "config", "authentication"
]


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
            f"""You are a parameter extractor. Extract parameters and output ONLY valid JSON in this exact format:
{{"time_frame": "YYYY-MM-DD or null", "domain": "domain_name", "query_keys": ["key1", "key2", "key3"]}}

RULES:
1. query_keys must be a flat array of strings - NO nested objects or arrays
2. Each query_key should be a simple field name
3. Domain should be the main data category
4. If no time mentioned, set time_frame to null

ALLOWED query_keys: {", ".join(allowed_query_keys)}
EXCLUDED query_keys: {", ".join(excluded_query_keys)}

ALLOWED domains: {", ".join(allowed_domains)}
EXCLUDED domains: {", ".join(excluded_domains)}

EXAMPLES:
User: "Show me merchant transactions over $500 last week"
Output: {{"time_frame": "2025-07-14", "domain": "transactions", "query_keys": ["merchant"]}}

User: "Find customers who bought electronics in January"
Output: {{"time_frame": "2025-01-01", "domain": "customers", "query_keys": ["customer_id", "category"]}}

User: "List all product reviews with ratings"
Output: {{"time_frame": null, "domain": "reviews", "query_keys": ["product_id", "rating", "review_text"]}}

User: "Get bKash payments from this month"
Output: {{"time_frame": "2025-07-01", "domain": "payments", "query_keys": ["bkash", "mfs", "processpayment"]}}

User text: {text}

Output only the JSON, no explanations:"""
        )
        resp = self.client.chat(
            model=self.model,
            messages=[{"role": "system", "content": prompt}],
        )
        raw = resp["message"]["content"]
        logger.debug("Raw parameters output: %s", raw)

        # 1. Pull out the JSON blob, wherever it is

        try:
            json_blob = self._extract_json_block(raw)
            params = json.loads(json_blob)
        except json.JSONDecodeError:
            logger.error("JSON parse error, falling back to regex extraction.")
            params = self._fallback(text)

        # 2. Normalize the date field
        if "time_frame" in params and isinstance(params["time_frame"], str):
            params["time_frame"] = self._normalize_date(params["time_frame"])

        # 3. Enforce DOMAIN_KEYWORDS as before
        text_upper = text.upper()
        forced = [kw for kw in DOMAIN_KEYWORDS if kw in text_upper]
        if forced:
            existing = [d.strip() for d in params.get("domain", "").split(",") if d.strip()]
            params["domain"] = ", ".join(dict.fromkeys(forced + existing))

        return params

    def _extract_json_block(self, raw: str) -> str:
        """
        Finds the first JSON object in the raw string, whether it's
        inside ```json``` fences or between the first { … }.
        """
        # 1) Try finding a fenced JSON block
        fenced = re.search(r"```json\s*(\{.*?\})\s*```", raw, flags=re.DOTALL)
        if fenced:
            return fenced.group(1)

        # 2) Otherwise, grab the first {...}
        simple = re.search(r"(\{(?:[^{}]|(?1))*\})", raw, flags=re.DOTALL)
        if simple:
            return simple.group(1)

        # 3) Give up — return whole text (likely to fail JSON parse)
        return raw.strip()

    def _normalize_date(self, date_str: str) -> str:
        """
        Turn any human‑readable date into YYYY‑MM‑DD.
        If parsing fails, returns the original string.
        """
        try:
            dt = date_parser.parse(date_str, dayfirst=True, fuzzy=True)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError) as e:
            logger.warning("Could not parse date '%s': %s", date_str, e)
            return date_str

    def _fallback(self, text: str) -> dict:
        # Simple regex-based fallback extraction, as before
        result = {"time_frame": "", "domain": "", "query_keys": []}
        date_match = re.search(r"\b\d{1,2}\.\d{1,2}\.\d{4}\b", text)
        if date_match:
            result["time_frame"] = date_match.group(0)
        found = [kw for kw in DOMAIN_KEYWORDS if kw in text.upper()]
        if found:
            result["domain"] = ", ".join(found)
        accounts = re.findall(r"\b\d{10,}\b", text)
        result["query_keys"] = accounts
        return result
