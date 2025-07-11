import logging
import re
from pathlib import Path
from typing import Optional, List, Dict

from ollama import Client

logger = logging.getLogger(__name__)


class FileSearcher:
    """
    Locates and verifies the appropriate log file based on extracted parameters.

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

    def find_and_verify(self, params: Dict[str, any]) -> Optional[Path]:
        """
        Find the best file and verify via regex + LLM.
        params should contain 'time_frame', 'domain', 'query_keys'.
        Returns Path if verified, else None.
        """
        # First, list all available files for debugging
        self._list_all_files()

        tf = params.get("time_frame")
        date_part = self._parse_time_frame(tf)

        logger.info(f"Searching for logs with date: {date_part}")
        logger.info(f"Parameters: {params}")

        for prefix in self.PREFIX_ORDER:
            logger.info(f"Searching for {prefix} logs...")
            candidates = self._find_files_by_prefix_and_date(prefix, date_part, params)

            if candidates:
                logger.info(f"Found {len(candidates)} candidate {prefix} files: {[f.name for f in candidates]}")

                # Try each candidate file
                for path in candidates:
                    logger.info(f"Checking candidate file: {path}")

                    # Regex check
                    if self._regex_verify(path, params):
                        logger.info(f"Regex verification passed for {path}")
                        # LLM verify
                        if self._llm_verify(path, params):
                            logger.info(f"LLM verification passed for {path}")
                            return path
                        else:
                            logger.debug(f"LLM verification failed for {path}")
                    else:
                        logger.debug(f"Regex verification failed for {path}")
            else:
                logger.info(f"No {prefix} files found for date {date_part}")

        logger.warning(f"No verified log file found for {tf}")
        return None

    def _list_all_files(self):
        """List all files in the base directory for debugging"""
        try:
            logger.info(f"Searching in directory: {self.base_dir}")
            logger.info(f"Directory exists: {self.base_dir.exists()}")
            logger.info(f"Directory is directory: {self.base_dir.is_dir()}")

            if not self.base_dir.exists():
                logger.error(f"Base directory does not exist: {self.base_dir}")
                return

            # List all files first
            all_files = list(self.base_dir.iterdir())
            logger.info(f"All files and directories in base directory ({len(all_files)}):")
            for item in sorted(all_files):
                if item.is_file():
                    logger.info(f"  FILE: {item.name}")
                elif item.is_dir():
                    logger.info(f"  DIR:  {item.name}")

            # List .xz files specifically
            xz_files = list(self.base_dir.glob("*.xz"))
            logger.info(f"All .xz files in directory ({len(xz_files)}):")
            for file in sorted(xz_files):
                logger.info(f"  - {file.name}")

            # List .gz files
            gz_files = list(self.base_dir.glob("*.gz"))
            logger.info(f"All .gz files in directory ({len(gz_files)}):")
            for file in sorted(gz_files):
                logger.info(f"  - {file.name}")

            # List .log files
            log_files = list(self.base_dir.glob("*.log"))
            logger.info(f"All .log files in directory ({len(log_files)}):")
            for file in sorted(log_files):
                logger.info(f"  - {file.name}")

            # List files with 'log' in name
            log_pattern_files = list(self.base_dir.glob("*log*"))
            logger.info(f"All files with 'log' in name ({len(log_pattern_files)}):")
            for file in sorted(log_pattern_files):
                logger.info(f"  - {file.name}")

        except Exception as e:
            logger.error(f"Error listing files: {e}")

    def _find_files_by_prefix_and_date(self, prefix: str, date_part: str, params: Dict[str, any]) -> List[Path]:
        """
        Find all files matching the prefix and date pattern.
        Handles different patterns for different log types.
        """
        candidates = []

        # Try multiple file extensions
        extensions = ['.xz', '.gz', '.log', '']

        for ext in extensions:
            # Pattern 1: prefix.log.YYYY-MM-DD.ext
            pattern1 = f"{prefix}.log.{date_part}{ext}"
            matches1 = list(self.base_dir.glob(pattern1))
            candidates.extend(matches1)

            # Pattern 2: prefix.log.YYYY-MM-DD.*.ext (with hour)
            pattern2 = f"{prefix}.log.{date_part}.*{ext}"
            matches2 = list(self.base_dir.glob(pattern2))
            # Filter out duplicates
            for match in matches2:
                if match not in candidates:
                    candidates.append(match)

            # Pattern 3: Just prefix with date somewhere in name
            pattern3 = f"*{prefix}*{date_part}*{ext}"
            matches3 = list(self.base_dir.glob(pattern3))
            for match in matches3:
                if match not in candidates:
                    candidates.append(match)

        # Also try without the date format conversion (in case files use different date format)
        original_date_formats = [
            params.get("time_frame", "").replace("/", "-"),  # 06.11.2024 -> 06.11.2024
            params.get("time_frame", "").replace(".", "-"),  # 06.11.2024 -> 06-11-2024
        ]

        for orig_date in original_date_formats:
            if orig_date:
                for ext in extensions:
                    pattern4 = f"*{prefix}*{orig_date}*{ext}"
                    matches4 = list(self.base_dir.glob(pattern4))
                    for match in matches4:
                        if match not in candidates:
                            candidates.append(match)

        logger.debug(f"All patterns tried for {prefix}: ")
        logger.debug(f"  - {prefix}.log.{date_part}.*")
        logger.debug(f"  - *{prefix}*{date_part}*")
        logger.debug(f"Found files: {[f.name for f in candidates]}")

        return sorted(candidates)

    def _regex_verify(self, path: Path, params: Dict[str, any]) -> bool:
        """
        Quick check: filename or first lines contain domain or query_keys
        """
        name = path.name.upper()
        domain = params.get("domain", "")
        query_keys = params.get("query_keys", [])

        logger.debug(f"Regex verification for {path.name}")
        logger.debug(f"Domain: {domain}, Query keys: {query_keys}")

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

        # Check a sample of file content (first 100 lines)
        try:
            import gzip
            import lzma

            # Handle compressed files
            if path.suffix == '.xz':
                with lzma.open(path, 'rt', errors='ignore') as f:
                    content_check = self._check_content(f, query_keys, 100)
            elif path.suffix == '.gz':
                with gzip.open(path, 'rt', errors='ignore') as f:
                    content_check = self._check_content(f, query_keys, 100)
            else:
                with path.open("r", errors="ignore") as f:
                    content_check = self._check_content(f, query_keys, 100)

            if content_check:
                logger.debug(f"Found query keys in file content")
                return True

        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")

        # If no specific matches found, return True for broader verification by LLM
        # This allows the LLM to make the final decision
        logger.debug(f"No specific matches found in regex check, allowing LLM verification")
        return True

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

    def _llm_verify(self, path: Path, params: Dict[str, any]) -> bool:
        """
        Use LLM to confirm if the file likely contains relevant logs.
        """
        # Read a small snippet
        snippet = ""
        try:
            import lzma
            import gzip

            # Handle compressed files
            if path.suffix == '.xz':
                with lzma.open(path, 'rt', errors='ignore') as f:
                    snippet = "".join([f.readline() for _ in range(20)])
            elif path.suffix == '.gz':
                with gzip.open(path, 'rt', errors='ignore') as f:
                    snippet = "".join([f.readline() for _ in range(20)])
            else:
                with path.open("r", errors="ignore") as f:
                    snippet = "".join([f.readline() for _ in range(20)])
        except Exception as e:
            logger.error(f"Error reading file for LLM verification: {e}")
            snippet = ""

        if not snippet.strip():
            logger.warning(f"No content found in {path.name} for LLM verification")
            return False

        prompt = (
            f"We are searching for logs with these parameters:\n"
            f"- Time frame: {params.get('time_frame')}\n"
            f"- Domain: {params.get('domain')}\n"
            f"- Query keys: {params.get('query_keys')}\n\n"
            f"Here is a snippet from the file {path.name}:\n"
            f"---\n{snippet}\n---\n\n"
            f"Question: Based on the search parameters and this file snippet, "
            f"does this file likely contain the logs we need?\n"
            f"Reply with YES or NO only."
        )

        try:
            resp = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
            )
            content = resp["message"]["content"].strip().upper()
            logger.debug(f"LLM response for {path.name}: {content}")
            return content.startswith("YES")
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