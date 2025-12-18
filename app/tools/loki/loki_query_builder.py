import re
import subprocess
import hashlib
import json
import logging
import threading
from datetime import datetime, timedelta
from typing import Union, List, Dict, Optional
from pathlib import Path
import os

from app.services.cache import cache_manager

logger = logging.getLogger(__name__)

# Loki cache configuration
LOKI_CACHE_DIR = Path("app/loki_cache")
LOKI_CACHE_TTL = 14400  # 4 hours for general queries
LOKI_TRACE_CACHE_TTL = 21600  # 6 hours for individual trace logs


class LokiCacheMetrics:
    """Metrics for tracking Loki cache usage."""

    def __init__(self):
        self.hits: int = 0
        self.misses: int = 0
        self.downloads: int = 0
        self.errors: int = 0
        self.bytes_saved: int = 0
        self._lock = threading.Lock()

    def record_hit(self, file_size: int = 0) -> None:
        with self._lock:
            self.hits += 1
            self.bytes_saved += file_size

    def record_miss(self) -> None:
        with self._lock:
            self.misses += 1
            self.downloads += 1

    def record_error(self) -> None:
        with self._lock:
            self.errors += 1

    def hit_rate(self) -> float:
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    def to_dict(self) -> Dict[str, any]:
        with self._lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0.0
            return {
                "hits": self.hits,
                "misses": self.misses,
                "downloads": self.downloads,
                "errors": self.errors,
                "bytes_saved": self.bytes_saved,
                "hit_rate_percent": round(hit_rate, 2),
            }

    def reset(self) -> None:
        with self._lock:
            self.hits = 0
            self.misses = 0
            self.downloads = 0
            self.errors = 0
            self.bytes_saved = 0


# Global metrics instance
loki_cache_metrics = LokiCacheMetrics()

# Default Loki endpoint
BASE_URL = "https://loki-gateway.local.fintech23.xyz/loki/api/v1/query_range"


def _parse_single_datetime(date_str: str, time_str: Union[str, None] = None) -> datetime:
    """
    Parse date (YYYY-MM-DD or YYYY/MM/DD) with optional time (HH:MM or HH:MM:SS).
    """
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            dt = datetime.strptime(date_str, fmt)
            break
        except ValueError:
            continue
    else:
        raise ValueError(f"Invalid date: {date_str}")

    if time_str:
        m = re.match(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$", time_str)
        if not m:
            raise ValueError(f"Invalid time: {time_str}")
        h, mi, s = m.groups()
        return dt.replace(hour=int(h), minute=int(mi), second=int(s or '0'))

    return dt.replace(hour=0, minute=0, second=0)


def build_curl_args(
    filters: Union[Dict[str, str], None] = None,
    pipeline: Union[Dict[str, str], List[str], None] = None,
    search: Union[str, List[str], None] = None,
    trace_id: Optional[str] = None,             # ← new!
    date_str: Optional[str] = None,
    time_str: Optional[str] = None,
    end_date_str: Optional[str] = None,
    end_time_str: Optional[str] = None,
    output: Optional[str] = None,
    base_url: str = BASE_URL,
) -> List[str]:
    # 1) Build the selector as before
    sel = "{" + ",".join(f'{k}="{v}"' for k, v in (filters or {}).items()) + "}"

    # 2) Handle any existing pipeline entries
    stages: List[str] = []
    if pipeline:
        stages = list(pipeline.items() if isinstance(pipeline, dict) else pipeline)

    # 3) If user wants to filter by trace_id, ensure we parse JSON first
    if trace_id:
        # only add `json` once
        # if "json" not in stages:
        #     stages.insert(0, "json")
        # then add the trace_id filter
        stages.append(f'trace_id="{trace_id}"')

    # 4) Stitch stages into sel (prefixing non-negations with '|')
    for stage in stages:
        raw = stage if isinstance(stage, str) else stage[1]
        if raw.lstrip().startswith(("!=", "!~")):
            sel += f" {raw.strip()}"
        else:
            sel += f" | {raw.strip()}"

    # 5) Handle search terms (unchanged)
    if search:
        if isinstance(search, (list, tuple)):
            esc = [t.replace('"', '\\"') for t in search]
            joined = " or ".join(f'"{t}"' for t in esc)
            sel += f' |= {joined}'
        else:
            esc = search.replace('"', '\\"')
            sel += f' |= "{esc}"'

    # 6) Time‐range logic (unchanged) …
    if date_str:
        start_dt = _parse_single_datetime(date_str, time_str)
        if end_date_str:
            end_dt = _parse_single_datetime(end_date_str, end_time_str)
        else:
            delta = timedelta(hours=1) if time_str else timedelta(days=1)
            end_dt = start_dt + delta
    else:
        end_dt = datetime.utcnow()
        start_dt = end_dt - timedelta(days=1)

    start = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    end   = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    # 7) Build the curl invocation
    args = [
        "curl", "-G", base_url,
        "--data-urlencode", f"query={sel}",
        "--data-urlencode", f"start={start}",
        "--data-urlencode", f"end={end}",
    ]
    if output:
        args += ["-o", output]
    return args




def build_curl_command(
        *args,
        **kwargs
) -> str:
    """
    Return a properly formatted curl command string with each parameter on a new line.
    Format: curl -G "url" \
              --param 'value' \
              --param 'value' \
              -o output
    """
    arg_list = build_curl_args(*args, **kwargs)

    # Start with curl command and URL
    formatted_parts = [f'curl -G "{arg_list[2]}" \\']

    # Process remaining arguments in pairs (flag, value)
    i = 3
    while i < len(arg_list):
        if arg_list[i].startswith('--'):
            # Long option with value
            if i + 1 < len(arg_list) and not arg_list[i + 1].startswith('-'):
                flag = arg_list[i]
                value = arg_list[i + 1]
                formatted_parts.append(f"  {flag} '{value}' \\")
                i += 2
            else:
                # Flag without value
                formatted_parts.append(f"  {arg_list[i]} \\")
                i += 1
        elif arg_list[i].startswith('-'):
            # Short option with value
            if i + 1 < len(arg_list) and not arg_list[i + 1].startswith('-'):
                flag = arg_list[i]
                value = arg_list[i + 1]
                formatted_parts.append(f"  {flag} {value}")
                i += 2
            else:
                # Flag without value
                formatted_parts.append(f"  {arg_list[i]}")
                i += 1
        else:
            # Standalone argument
            formatted_parts.append(f"  {arg_list[i]}")
            i += 1

    # Remove trailing backslash from last line
    if formatted_parts[-1].endswith(' \\'):
        formatted_parts[-1] = formatted_parts[-1][:-2]

    return '\n'.join(formatted_parts)


def download_logs(
        *args,
        **kwargs,
) -> None:
    """
    Execute the curl via subprocess, avoiding shell parsing issues.
    """
    try:
        arg_list = build_curl_args(*args, **kwargs)
        # Ensure output directory exists
        output = kwargs.get('output')
        if output:
            os.makedirs(os.path.dirname(output), exist_ok=True)
        # Use build_curl_command to get the nicely formatted string
        curl_str = build_curl_command(*args, **kwargs)
        print("Running:")
        print(curl_str)
        subprocess.run(arg_list, check=True)
    except Exception as e:
        print(f"Error executing curl command: {e}")


def _get_loki_cache_key(
    filters: Optional[Dict[str, str]] = None,
    pipeline: Optional[Union[Dict[str, str], List[str]]] = None,
    search: Optional[Union[str, List[str]]] = None,
    trace_id: Optional[str] = None,
    date_str: Optional[str] = None,
    time_str: Optional[str] = None,
    end_date_str: Optional[str] = None,
    end_time_str: Optional[str] = None,
) -> str:
    """Generate a deterministic cache key from query parameters."""
    params = {
        "filters": filters,
        "pipeline": pipeline if isinstance(pipeline, list) else (list(pipeline.items()) if pipeline else None),
        "search": search,
        "trace_id": trace_id,
        "date_str": date_str,
        "time_str": time_str,
        "end_date_str": end_date_str,
        "end_time_str": end_time_str,
    }
    params_str = json.dumps(params, sort_keys=True)
    return hashlib.sha256(params_str.encode()).hexdigest()[:20]


def download_logs_cached(
    filters: Optional[Dict[str, str]] = None,
    pipeline: Optional[Union[Dict[str, str], List[str]]] = None,
    search: Optional[Union[str, List[str]]] = None,
    trace_id: Optional[str] = None,
    date_str: Optional[str] = None,
    time_str: Optional[str] = None,
    end_date_str: Optional[str] = None,
    end_time_str: Optional[str] = None,
    base_url: str = BASE_URL,
    force_refresh: bool = False,
) -> Optional[str]:
    """
    Cached version of download_logs. Returns the path to the cached/downloaded file.

    Args:
        filters: Loki label filters
        pipeline: Pipeline operations
        search: Search terms
        trace_id: Specific trace ID to filter
        date_str: Start date
        time_str: Start time
        end_date_str: End date
        end_time_str: End time
        base_url: Loki API endpoint
        force_refresh: If True, bypass cache and re-download

    Returns:
        Path to the log file (cached or freshly downloaded), or None on error
    """
    # Generate cache key
    cache_key = _get_loki_cache_key(
        filters=filters,
        pipeline=pipeline,
        search=search,
        trace_id=trace_id,
        date_str=date_str,
        time_str=time_str,
        end_date_str=end_date_str,
        end_time_str=end_time_str,
    )

    # Determine TTL based on whether this is a trace-specific query
    ttl = LOKI_TRACE_CACHE_TTL if trace_id else LOKI_CACHE_TTL
    cache_name = "loki_trace" if trace_id else "loki"

    # Check in-memory cache for file path
    loki_cache = cache_manager.get_cache(cache_name, ttl=ttl)

    if not force_refresh:
        cached_path = loki_cache.get(cache_key)
        if cached_path and Path(cached_path).exists():
            file_size = Path(cached_path).stat().st_size
            loki_cache_metrics.record_hit(file_size)
            logger.info(
                f"Loki cache HIT: key={cache_key[:12]}... file={Path(cached_path).name} "
                f"size={file_size} bytes (total hits: {loki_cache_metrics.hits}, "
                f"hit_rate: {loki_cache_metrics.hit_rate():.1f}%)"
            )
            return cached_path

    # Ensure cache directory exists
    LOKI_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Generate output filename
    output_path = LOKI_CACHE_DIR / f"loki_{cache_key}.json"

    # Download logs
    try:
        arg_list = build_curl_args(
            filters=filters,
            pipeline=pipeline,
            search=search,
            trace_id=trace_id,
            date_str=date_str,
            time_str=time_str,
            end_date_str=end_date_str,
            end_time_str=end_time_str,
            output=str(output_path),
            base_url=base_url,
        )

        curl_str = build_curl_command(
            filters=filters,
            pipeline=pipeline,
            search=search,
            trace_id=trace_id,
            date_str=date_str,
            time_str=time_str,
            end_date_str=end_date_str,
            end_time_str=end_time_str,
            output=str(output_path),
            base_url=base_url,
        )

        loki_cache_metrics.record_miss()
        logger.info(
            f"Loki cache MISS: key={cache_key[:12]}... downloading... "
            f"(total misses: {loki_cache_metrics.misses})"
        )
        logger.debug(f"Downloading Loki logs: {curl_str}")

        subprocess.run(arg_list, check=True)

        # Verify file was created and has content
        if output_path.exists() and output_path.stat().st_size > 0:
            file_size = output_path.stat().st_size
            # Cache the file path
            loki_cache.set(cache_key, str(output_path), ttl=ttl)
            logger.info(
                f"Loki cache STORED: key={cache_key[:12]}... file={output_path.name} "
                f"size={file_size} bytes TTL={ttl}s"
            )
            return str(output_path)
        else:
            logger.warning(f"Downloaded file is empty or missing: {output_path}")
            loki_cache_metrics.record_error()
            return None

    except subprocess.CalledProcessError as e:
        loki_cache_metrics.record_error()
        logger.error(f"Loki download ERROR: key={cache_key[:12]}... error={e}")
        return None
    except Exception as e:
        loki_cache_metrics.record_error()
        logger.error(f"Loki cache ERROR: key={cache_key[:12]}... error={e}")
        return None


def clear_loki_cache(older_than_hours: Optional[int] = None) -> int:
    """
    Clear Loki cache files.

    Args:
        older_than_hours: If provided, only clear files older than this many hours.
                         If None, clear all cache files.

    Returns:
        Number of files removed
    """
    if not LOKI_CACHE_DIR.exists():
        return 0

    removed_count = 0
    now = datetime.now()

    for cache_file in LOKI_CACHE_DIR.glob("loki_*.json"):
        try:
            if older_than_hours is not None:
                file_age = now - datetime.fromtimestamp(cache_file.stat().st_mtime)
                if file_age.total_seconds() < older_than_hours * 3600:
                    continue

            cache_file.unlink()
            removed_count += 1
            logger.debug(f"Removed cache file: {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to remove cache file {cache_file}: {e}")

    # Also invalidate in-memory caches
    cache_manager.invalidate("loki")
    cache_manager.invalidate("loki_trace")

    logger.info(f"Cleared {removed_count} Loki cache files")
    return removed_count


def get_loki_cache_stats() -> Dict[str, any]:
    """
    Get Loki cache statistics including metrics.

    Returns:
        Dict with cache statistics and metrics
    """
    stats = {
        "cache_dir": str(LOKI_CACHE_DIR),
        "file_count": 0,
        "total_size_mb": 0,
        "memory_cache_entries": {
            "loki": cache_manager.get_cache("loki").size(),
            "loki_trace": cache_manager.get_cache("loki_trace").size(),
        },
        "metrics": loki_cache_metrics.to_dict(),
    }

    if LOKI_CACHE_DIR.exists():
        cache_files = list(LOKI_CACHE_DIR.glob("loki_*.json"))
        stats["file_count"] = len(cache_files)
        stats["total_size_mb"] = round(
            sum(f.stat().st_size for f in cache_files) / (1024 * 1024), 2
        )

    return stats


def get_loki_cache_metrics() -> Dict[str, any]:
    """
    Get just the Loki cache metrics.

    Returns:
        Dict with cache hit/miss metrics
    """
    return loki_cache_metrics.to_dict()


def reset_loki_cache_metrics() -> None:
    """Reset all Loki cache metrics to zero."""
    loki_cache_metrics.reset()
    logger.info("Loki cache metrics reset")



# Example usage
if __name__ == '__main__':
    cmd_str = build_curl_command(
        filters={'service_namespace': 'ncc'},
        pipeline={'trace_id': '6dcac4a5b100123ae1793cb296f11ddf'},
        search='merchant',
        date_str='2025-07-14',
        end_date_str='2025-07-15',
        output='loki-ncc-merchant-14-15.json'
    )
    print(cmd_str)
    print()

    download_logs(
        filters={'service_namespace': 'ncc'},
        pipeline={'trace_id': '6dcac4a5b100123ae1793cb296f11ddf'},
        search='merchant',
        date_str='2025-07-15',
        end_date_str='2025-07-16',
        output='loki-ncc-merchant-15-16.json'
    )