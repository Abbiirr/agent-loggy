# parameters_agent.py

from __future__ import annotations

import json
import logging
import regex as re
import time
from typing import Dict, List, Optional

import httpx
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from ollama import Client

from app.config import settings

logger = logging.getLogger(__name__)


# ---- CONFIGURATION (with ConfigService support) ----
def _get_config(category: str, key: str, default):
    """Get config from DB if enabled, otherwise return default."""
    if settings.USE_DB_SETTINGS:
        try:
            from app.services.config_service import get_setting
            return get_setting(category, key, default)
        except Exception as e:
            logger.warning(f"Failed to get config {category}.{key}: {e}")
    return default


# Default values (used when DB settings disabled or unavailable)
_DEFAULT_OLLAMA_HOST = "http://10.112.30.10:11434"
_DEFAULT_DOMAIN_KEYWORDS = ["NPSB", "BEFTN", "FUNDFTRANSFER", "PAYMENT", "BKASH", "QR", "MFS", "NAGAD", "UPAY", "ROCKET"]
_DEFAULT_ALLOWED_QUERY_KEYS = [
    "merchant", "amount", "transaction_id", "customer_id",
    "mfs", "bkash", "nagad", "upay", "rocket", "qr", "npsb", "beftn",
    "fund_transfer", "payment", "balance", "fee", "status",
    "product_id", "category", "rating", "review_text", "user_id"
]
_DEFAULT_EXCLUDED_QUERY_KEYS = [
    "password", "token", "secret", "api_key", "private_key",
    "internal_id", "system_log", "debug_info", "date"
]
_DEFAULT_ALLOWED_DOMAINS = [
    "transactions", "customers", "users", "products", "reviews",
    "payments", "merchants", "accounts", "orders", "analytics"
]
_DEFAULT_EXCLUDED_DOMAINS = [
    "system", "logs", "admin", "security", "internal",
    "debug", "config", "authentication"
]


def get_ollama_host() -> str:
    return _get_config("ollama", "host", _DEFAULT_OLLAMA_HOST)


def get_domain_keywords() -> List[str]:
    return _get_config("agent", "domain_keywords", _DEFAULT_DOMAIN_KEYWORDS)


def get_allowed_query_keys() -> List[str]:
    return _get_config("agent", "allowed_query_keys", _DEFAULT_ALLOWED_QUERY_KEYS)


def get_excluded_query_keys() -> List[str]:
    return _get_config("agent", "excluded_query_keys", _DEFAULT_EXCLUDED_QUERY_KEYS)


def get_allowed_domains() -> List[str]:
    return _get_config("agent", "allowed_domains", _DEFAULT_ALLOWED_DOMAINS)


# Keep module-level variables for backwards compatibility
OLLAMA_HOST = _DEFAULT_OLLAMA_HOST
DOMAIN_KEYWORDS = _DEFAULT_DOMAIN_KEYWORDS
allowed_query_keys: List[str] = _DEFAULT_ALLOWED_QUERY_KEYS
excluded_query_keys: List[str] = _DEFAULT_EXCLUDED_QUERY_KEYS
allowed_domains: List[str] = _DEFAULT_ALLOWED_DOMAINS
excluded_domains: List[str] = _DEFAULT_EXCLUDED_DOMAINS

# Month name map
_MONTHS = {
    'jan':1, 'january':1, 'feb':2, 'february':2, 'mar':3, 'march':3, 'apr':4, 'april':4,
    'may':5, 'jun':6, 'june':6, 'jul':7, 'july':7, 'aug':8, 'august':8,
    'sep':9, 'sept':9, 'september':9, 'oct':10, 'october':10, 'nov':11, 'november':11, 'dec':12, 'december':12
}

# Precompiled date patterns
_RE_ISO_YMD   = re.compile(r'\b(\d{4})[./-](\d{1,2})[./-](\d{1,2})\b')
_RE_D_MONTH_Y = re.compile(r'\b(\d{1,2})(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})\b', re.I)
_RE_MONTH_D_Y = re.compile(r'\b([A-Za-z]+)\s+(\d{1,2})(?:st|nd|rd|th)?,\s*(\d{4})\b', re.I)
_RE_DMY       = re.compile(r'\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\b')  # interpret day-first
_RE_YM        = re.compile(r'\b(\d{4})[./-](\d{1,2})\b')

# JSON extraction patterns (supports fenced blocks and balanced braces via recursion)
_RE_FENCED = re.compile(r"```json\s*(\{.*?\})\s*```", re.DOTALL)
_RE_OBJ    = re.compile(r"(\{(?:[^{}]|(?1))*\})", re.DOTALL)  # requires 'regex' module


# ---- HEALTH CHECK WITH RETRY ----
def is_ollama_running(host: str = None, max_retries: int = None) -> bool:
    """Return True if Ollama daemon responds on the root endpoint."""
    if host is None:
        host = get_ollama_host()
    if max_retries is None:
        max_retries = _get_config("ollama", "max_retries", 3)

    for attempt in range(max_retries):
        try:
            resp = httpx.get(f"{host}/", timeout=10.0)
            if resp.status_code == 200:
                return True
        except Exception as e:
            logger.debug(f"Ollama health check attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(0.5 * (2 ** attempt))  # Exponential backoff
    return False


class OllamaUnavailableError(Exception):
    """Raised when Ollama service is unavailable"""
    pass


class ParametersAgent:
    """
    Extracts {time_frame, domain, query_keys} from free text using an LLM
    and then applies strict validation + deterministic date normalization.
    """

    def __init__(self, client: Client, model: str):
        self.client = client
        self.model = model
        logger.info("ParametersAgent using model: %s", model)

    # ---------------------- Public API ----------------------

    def run(self, text: str) -> Dict:
        # Check Ollama availability but don't crash the app
        if not is_ollama_running():
            logger.error("Ollama server is not available. Using fallback extraction.")
            # Return fallback instead of crashing
            return self._fallback(text)

        try:
            system_prompt = self._build_system_prompt()
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text.strip()},
            ]

            # Add timeout to prevent hanging
            timeout = _get_config("ollama", "timeout", 30)
            resp = self.client.chat(
                model=self.model,
                messages=messages,
                options={"timeout": timeout}
            )
            raw = resp["message"]["content"]
            logger.debug("Raw parameters output: %s", raw)

            # 1) Extract JSON
            try:
                json_blob = self._extract_json_block(raw)
                params = json.loads(json_blob)
            except Exception as e:
                logger.error("LLM JSON parse error (%s). Falling back to regex-only extraction.", e)
                params = self._fallback(text)

        except Exception as e:
            logger.error(f"Ollama API call failed: {e}. Using fallback extraction.")
            return self._fallback(text)

        # 2) Normalize time_frame → ISO YYYY-MM-DD or None
        tf = params.get("time_frame", None)
        if isinstance(tf, str):
            normalized = self._normalize_date(tf)
            params["time_frame"] = normalized if normalized is not None else None
        elif tf is None:
            params["time_frame"] = None
        else:
            params["time_frame"] = None

        # 3) Domain: enforce allow-list / infer if missing or invalid
        domain = (params.get("domain") or "").strip().lower()
        current_allowed_domains = get_allowed_domains()
        if not domain or domain not in current_allowed_domains or domain in excluded_domains:
            inferred = self._infer_domain(text)
            params["domain"] = inferred
        else:
            params["domain"] = domain

        # 4) query_keys: normalize, dedupe, enforce allow/exclude
        qk = params.get("query_keys", [])
        if not isinstance(qk, list):
            qk = []
        params["query_keys"] = self._sanitize_query_keys(qk, text)

        return {
            "time_frame": params["time_frame"],
            "domain": params["domain"],
            "query_keys": params["query_keys"],
        }

    # ---------------------- Prompt ----------------------

    def _build_system_prompt(self) -> str:
        """Build the system prompt, optionally from database if feature flag enabled."""
        # Get current config values
        current_allowed_keys = get_allowed_query_keys()
        current_excluded_keys = get_excluded_query_keys()
        current_allowed_domains = get_allowed_domains()

        # Try to get prompt from database if feature flag is enabled
        if settings.USE_DB_PROMPTS:
            try:
                from app.services.prompt_service import get_prompt_service
                prompt_service = get_prompt_service()
                db_prompt = prompt_service.render_prompt(
                    "parameter_extraction_system",
                    {
                        "allowed_query_keys": ', '.join(current_allowed_keys),
                        "excluded_query_keys": ', '.join(current_excluded_keys),
                        "allowed_domains": ', '.join(current_allowed_domains),
                        "excluded_domains": ', '.join(excluded_domains),
                    }
                )
                if db_prompt:
                    logger.debug("Using database prompt for parameter_extraction_system")
                    return db_prompt
                logger.warning("Database prompt not found, falling back to hardcoded prompt")
            except Exception as e:
                logger.warning(f"Failed to get prompt from database: {e}, using hardcoded prompt")

        # Fallback to hardcoded prompt
        return (
            "You are a strict parameter extractor.\n"
            "Return ONLY valid JSON with this exact schema:\n"
            '{"time_frame": "YYYY-MM-DD or null", "domain": "domain_name", "query_keys": ["key1","key2","key3"]}\n\n'
            "RULES:\n"
            "1) query_keys is a flat array of simple field names (lowercase snake_case). No objects/arrays.\n"
            "2) domain is the main data category from this allow-list only.\n"
            "3) If no time mentioned → time_frame = null.\n"
            "4) time_frame MUST be a single ISO date (YYYY-MM-DD) or null.\n"
            '5) If user gives a month or a relative period ("July 2025", "last week", "this month"), convert to one concrete start date (YYYY-MM-DD). For a month use day 1; for ranges use the start date.\n'
            "6) If you cannot confidently produce a single date, set time_frame to null.\n"
            "7) Use ONLY the allowed query keys; never output excluded ones.\n\n"
            f"ALLOWED query_keys: {', '.join(current_allowed_keys)}\n"
            f"EXCLUDED query_keys: {', '.join(current_excluded_keys)}\n\n"
            f"ALLOWED domains: {', '.join(current_allowed_domains)}\n"
            f"EXCLUDED domains: {', '.join(excluded_domains)}\n\n"
            "EXAMPLES:\n"
            'User: "Show me merchant transactions over 500 last week"\n'
            'Output: {"time_frame": "2025-07-14", "domain": "transactions", "query_keys": ["merchant","amount"]}\n\n'
            'User: "Find customers who bought electronics in January 2025"\n'
            'Output: {"time_frame": "2025-01-01", "domain": "customers", "query_keys": ["category"]}\n\n'
            'User: "List all product reviews with ratings"\n'
            'Output: {"time_frame": null, "domain": "reviews", "query_keys": ["product_id","rating","review_text"]}\n\n'
            'User: "Get bKash payments from this month"\n'
            'Output: {"time_frame": "2025-10-01", "domain": "payments", "query_keys": ["bkash","mfs"]}\n\n'
            "Return ONLY the JSON. No extra text."
        )

    # ---------------------- Helpers ----------------------

    def _extract_json_block(self, raw: str) -> str:
        """Find the first JSON object, fenced or plain; prefer fenced ```json blocks."""
        m = _RE_FENCED.search(raw)
        if m:
            return m.group(1)
        m = _RE_OBJ.search(raw)
        if m:
            return m.group(1)
        return raw.strip()

    def _month_index(self, mstr: str) -> Optional[int]:
        return _MONTHS.get(mstr.strip().lower())

    def _safe_iso(self, y: int, m: int, d: int) -> Optional[str]:
        try:
            return datetime(y, m, d).strftime('%Y-%m-%d')
        except ValueError:
            return None

    def _start_of_week(self, d: date) -> date:
        # Monday as start of week
        return d - timedelta(days=d.weekday())

    def _normalize_date(self, date_str: str) -> Optional[str]:
        """
        Deterministic conversion of various human forms to YYYY-MM-DD.
        Returns None if not confidently parseable as a single calendar day.
        """
        s = (date_str or "").strip()

        # 1) Strict ISO (YYYY-MM-DD or YYYY/MM/DD or YYYY.MM.DD)
        m = _RE_ISO_YMD.search(s)
        if m:
            y, mo, da = map(int, m.groups())
            out = self._safe_iso(y, mo, da)
            if out: return out

        # 2) "DD Month YYYY"
        m = _RE_D_MONTH_Y.search(s)
        if m:
            d, mon, y = m.groups()
            mi = self._month_index(mon)
            if mi:
                out = self._safe_iso(int(y), mi, int(d))
                if out: return out

        # 3) "Month DD, YYYY"
        m = _RE_MONTH_D_Y.search(s)
        if m:
            mon, d, y = m.groups()
            mi = self._month_index(mon)
            if mi:
                out = self._safe_iso(int(y), mi, int(d))
                if out: return out

        # 4) Numeric D-M-Y (explicit day-first policy)
        m = _RE_DMY.search(s)
        if m:
            d, mo, y = m.groups()
            y = int(y)
            if y < 100:
                y += 2000 if y < 50 else 1900
            out = self._safe_iso(y, int(mo), int(d))
            if out: return out

        # 5) Year-Month -> first of the month
        m = _RE_YM.search(s)
        if m:
            y, mo = map(int, m.groups())
            out = self._safe_iso(y, mo, 1)
            if out: return out

        # 6) Relative phrases → choose a concrete start date
        low = s.lower()
        today = date.today()

        if 'today' in low:
            return today.strftime('%Y-%m-%d')
        if 'yesterday' in low:
            return (today - timedelta(days=1)).strftime('%Y-%m-%d')
        if 'tomorrow' in low:
            return (today + timedelta(days=1)).strftime('%Y-%m-%d')

        if 'this week' in low:
            return self._start_of_week(today).strftime('%Y-%m-%d')
        if 'last week' in low:
            return self._start_of_week(today - timedelta(days=7)).strftime('%Y-%m-%d')
        if 'next week' in low:
            return self._start_of_week(today + timedelta(days=7)).strftime('%Y-%m-%d')

        if 'this month' in low:
            return today.replace(day=1).strftime('%Y-%m-%d')
        if 'last month' in low:
            first = today.replace(day=1) - timedelta(days=1)
            return first.replace(day=1).strftime('%Y-%m-%d')
        if 'next month' in low:
            first_next = (today.replace(day=1) + relativedelta(months=1))
            return first_next.strftime('%Y-%m-%d')

        # 7) Not confident
        return None

    def _infer_domain(self, text: str) -> str:
        """
        If LLM domain is missing/invalid, infer from text.
        Payment/MFS cues -> 'payments', otherwise default 'transactions'.
        """
        t = text.upper()
        domain_keywords = get_domain_keywords()
        current_allowed_domains = get_allowed_domains()

        if any(k in t for k in domain_keywords) or any(k in t for k in ["FUND TRANSFER"]):
            return "payments" if "payments" in current_allowed_domains else "transactions"
        return "transactions"

    def _sanitize_query_keys(self, keys: List[str], text: str) -> List[str]:
        """
        - Lowercase & snake_case
        - Drop excluded
        - Restrict to allow-list
        - Auto-add obvious keys present in text (e.g., bkash, nagad, qr, mfs)
        """
        def norm(k: str) -> str:
            k = (k or "").strip().lower()
            k = k.replace("-", "_").replace(" ", "_")
            return k

        allowed_set = set(get_allowed_query_keys())
        excluded_set = set(get_excluded_query_keys())

        out: List[str] = []
        for k in keys:
            nk = norm(k)
            if nk and nk not in excluded_set and nk in allowed_set:
                if nk not in out:
                    out.append(nk)

        # Heuristic: scan text to add known provider/network keys
        t = text.lower()
        auto_candidates = ["bkash", "nagad", "upay", "rocket", "qr", "mfs", "npsb", "beftn", "fund_transfer", "payment", "merchant", "amount", "status"]
        for cand in auto_candidates:
            # handle "fund transfer" as well
            if cand == "fund_transfer":
                if "fund transfer" in t or "fundtransfer" in t:
                    if cand not in out and cand in allowed_set:
                        out.append(cand)
                continue
            if cand in t and cand in allowed_set and cand not in excluded_set and cand not in out:
                out.append(cand)

        return out

    def _fallback(self, text: str) -> Dict:
        """
        Conservative extraction when the LLM output is unusable.
        - No guessing complex dates
        - Domain inferred heuristically
        - query_keys from allow-list tokens found in text
        """
        tf = self._normalize_date(text)  # may be None
        domain = self._infer_domain(text)
        qk = self._sanitize_query_keys([], text)
        return {"time_frame": tf, "domain": domain, "query_keys": qk}