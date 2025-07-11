import logging
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
import gzip
import lzma

from ollama import Client

logger = logging.getLogger(__name__)


class FileSearcher:
    """
    Locates and verifies appropriate log files based on extracted parameters.

    Search order:
      1. error logs
      2. trace logs
      3. integration logs
      4. application logs

    Verification:
      - Initial regex check on filename and sample content
      - LLM confirmation for final decision
    """
    PREFIX_ORDER = ["error", "trace", "integration", "application"]
    DOMAIN_KEYWORDS = ["NPSB", "BEFTN"]

    def __init__(self, base_dir: Path, llm_client: Client, model: str):
        """
        Args:
            base_dir: Path to directory containing log files
            llm_client: Ollama Client instance
            model: name of the LLM model to use for verification
        """
        self.base_dir = base_dir
        self.client = llm_client
        self.model = model

    def find_and_verify(self, params: Dict[str, Any]) -> List[Path]:
        """
        Find all verified files matching the search criteria.
        params should contain 'time_frame', 'domain', 'query_keys'.
        Returns List of Path objects for all verified files.
        """
        # First, list all available files for debugging
        self._list_all_files()

        tf = params.get("time_frame")
        if not tf:
            logger.error("No time_frame provided in parameters")
            return []

        try:
            date_part = self._parse_time_frame(tf)
        except Exception as e:
            logger.error(f"Failed to parse time_frame '{tf}': {e}")
            return []

        logger.info(f"Searching for logs with date: {date_part}")
        logger.info(f"Parameters: {params}")

        verified_files = []

        for prefix in self.PREFIX_ORDER:
            logger.info(f"--- Searching for {prefix} logs ---")
            candidates = self._find_files_by_prefix_and_date(prefix, date_part, params)

            if candidates:
                logger.info(f"Found {len(candidates)} candidate {prefix} files: {[f.name for f in candidates]}")

                # Check each candidate file
                for path in candidates:
                    logger.info(f"Checking candidate file: {path}")

                    # Regex check
                    if self._regex_verify(path, params):
                        logger.info(f"✓ Regex verification passed for {path}")

                        # LLM verify
                        if self._llm_verify(path, params):
                            logger.info(f"✓ LLM verification passed for {path}")
                            verified_files.append(path)
                        else:
                            logger.debug(f"✗ LLM verification failed for {path}")
                    else:
                        logger.debug(f"✗ Regex verification failed for {path}")
            else:
                logger.info(f"No {prefix} files found for date {date_part}")

        if verified_files:
            logger.info(f"Total verified log files found: {len(verified_files)}")
            for vf in verified_files:
                logger.info(f"  ✓ {vf}")
        else:
            logger.warning(f"No verified log files found for {tf}")

        return verified_files

    def _list_all_files(self):
        """List all files in the base directory and subdirectories for debugging"""
        try:
            logger.info(f"Searching in directory: {self.base_dir}")
            logger.info(f"Directory exists: {self.base_dir.exists()}")
            logger.info(f"Directory is directory: {self.base_dir.is_dir()}")

            if not self.base_dir.exists():
                logger.error(f"Base directory does not exist: {self.base_dir}")
                return

            # List all files in base directory
            all_files = list(self.base_dir.iterdir())
            logger.info(f"All files and directories in base directory ({len(all_files)}):")
            for item in sorted(all_files):
                if item.is_file():
                    logger.info(f"  FILE: {item.name}")
                elif item.is_dir():
                    logger.info(f"  DIR:  {item.name}")

            # List .xz files in base directory and subdirectories
            xz_files = list(self.base_dir.rglob("*.xz"))
            logger.info(f"All .xz files in directory and subdirectories ({len(xz_files)}):")
            for file in sorted(xz_files):
                logger.info(f"  - {file.relative_to(self.base_dir)}")

        except Exception as e:
            logger.error(f"Error listing files: {e}")

    def _find_files_by_prefix_and_date(self, prefix: str, date_part: str, params: Dict[str, Any]) -> List[Path]:
        """
        Find all files matching the prefix and date pattern in base directory and subdirectories.
        """
        candidates = []

        # Try multiple file extensions
        extensions = ['.xz', '.gz', '.log', '']

        for ext in extensions:
            # Pattern 1: prefix.log.YYYY-MM-DD.ext
            pattern1 = f"{prefix}.log.{date_part}{ext}"
            matches1 = list(self.base_dir.rglob(pattern1))
            candidates.extend(matches1)

            # Pattern 2: prefix.log.YYYY-MM-DD.*.ext (with hour)
            pattern2 = f"{prefix}.log.{date_part}.*{ext}"
            matches2 = list(self.base_dir.rglob(pattern2))
            # Filter out duplicates
            for match in matches2:
                if match not in candidates:
                    candidates.append(match)

        logger.debug(
            f"Found {len(candidates)} candidates for {prefix}: {[f.relative_to(self.base_dir) if f.is_relative_to(self.base_dir) else f.name for f in candidates]}")
        return sorted(candidates)

    def _regex_verify(self, path: Path, params: Dict[str, Any]) -> bool:
        """
        Quick check: filename or first lines contain domain or query_keys
        """
        name = path.name.upper()
        domain = params.get("domain", "")
        query_keys = params.get("query_keys", [])

        logger.debug(f"Regex verification for {path.name}")

        # Check domain keywords in filename
        if domain:
            for dk in domain.split(","):
                dk = dk.strip().upper()
                if dk and dk in name:
                    logger.debug(f"Found domain keyword '{dk}' in filename")
                    return True

        # Check query_keys in filename
        for key in query_keys:
            if str(key) in name:
                logger.debug(f"Found query key '{key}' in filename")
                return True

        # Check file content
        try:
            content_check = self._check_file_content(path, query_keys, 100)
            if content_check:
                logger.debug(f"Found query keys in file content")
                return True
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")

        # Allow LLM to make final decision even if regex doesn't find specific matches
        logger.debug(f"No specific matches found in regex check, allowing LLM verification")
        return True

    def _check_file_content(self, path: Path, query_keys: List, max_lines: int = 100) -> bool:
        """Check if any query keys are present in the file content"""
        try:
            # Handle compressed files
            if path.suffix == '.xz':
                with lzma.open(path, 'rt', errors='ignore') as f:
                    return self._check_content(f, query_keys, max_lines)
            elif path.suffix == '.gz':
                with gzip.open(path, 'rt', errors='ignore') as f:
                    return self._check_content(f, query_keys, max_lines)
            else:
                with path.open("r", errors="ignore") as f:
                    return self._check_content(f, query_keys, max_lines)
        except Exception as e:
            logger.error(f"Error reading file content: {e}")
            return False

    def _check_content(self, file_handle, query_keys: List, max_lines: int = 100) -> bool:
        """Check if any query keys are present in the file content"""
        try:
            for i, line in enumerate(file_handle):
                if i >= max_lines:
                    break
                for key in query_keys:
                    if str(key) in line:
                        return True
        except Exception as e:
            logger.error(f"Error checking content: {e}")
        return False

    def _llm_verify(self, path: Path, params: Dict[str, Any]) -> bool:
        """
        Use LLM to confirm if the file likely contains relevant logs based on filename only.
        """
        logger.info(f"Starting LLM verification for {path.name}")

        # Simple prompt based only on filename with clear date format explanation
        prompt = (
            f"We are searching for logs with these parameters:\n"
            f"- Time frame: {params.get('time_frame')} (DD.MM.YYYY format)\n"
            f"- Domain: {params.get('domain')}\n"
            f"- Query keys: {params.get('query_keys')}\n\n"
            f"Filename: {path.name}\n\n"
            f"Note: In the filename, the date appears as YYYY-MM-DD format.\n"
            f"Example: '11.07.2025' in DD.MM.YYYY format corresponds to '2025-07-11' in the filename.\n\n"
            f"Question: Based ONLY on the filename, does this file likely contain logs for the specified time frame?\n"
            f"Reply with YES or NO only."
        )

        try:
            resp = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            content = resp["message"]["content"].strip().upper()

            # Debug the actual content character by character
            logger.info(f"LLM raw response: '{resp['message']['content']}'")
            logger.info(f"After strip & upper: '{content}'")
            logger.info(f"Last 5 chars: '{content[-5:]}'")
            logger.info(f"Contains 'YES': {'YES' in content}")

            # Fix: Use 'in' operator instead of startswith
            result = 'YES' in content
            if result:
                logger.info(f"✓ LLM verification PASSED for {path.name}")
            else:
                logger.info(f"✗ LLM verification FAILED for {path.name}")

            return result
        except Exception as e:
            logger.error(f"Error during LLM verification: {e}")
            return False

    def _parse_time_frame(self, time_frame: str) -> str:
        """
        Parse time frame like '06.11.2024' or '06.11.2024/12' into YYYY-MM-DD format
        """
        try:
            # Split by '/' if hour is specified
            parts = time_frame.split("/")
            date_part = parts[0]

            # Parse date part (DD.MM.YYYY)
            d, m, y = date_part.split('.')
            formatted_date = f"{y}-{m.zfill(2)}-{d.zfill(2)}"

            logger.debug(f"Parsed time frame '{time_frame}' to '{formatted_date}'")
            return formatted_date
        except Exception as e:
            logger.error(f"Error parsing time frame '{time_frame}': {e}")
            return time_frame