"""
Redis-backed L2 cache for Loki queries.

This module provides persistent caching for Loki query results across server restarts.
Uses the same pattern as the LLM gateway's Redis backend.

Architecture:
- L1: In-memory TTL cache (existing via cache_manager)
- L2: Redis backend (this module) for persistence

Cache entries store: cache_key -> file_path mapping
The actual log files are stored on disk in app/loki_cache/
"""

from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from app.config import settings

logger = logging.getLogger(__name__)


def _now_s() -> float:
    return time.time()


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class LokiCacheEntry:
    """Represents a cached Loki query result."""
    file_path: str
    created_at: float
    result_count: int
    file_size: int


class LokiRedisBackend:
    """Redis backend for Loki cache persistence."""

    def __init__(
        self,
        redis_url: str,
        *,
        key_prefix: str = "loki:",
        socket_connect_timeout_s: float = 1.0,
        socket_timeout_s: float = 1.0,
    ):
        try:
            import redis  # type: ignore
        except ImportError as e:
            raise RuntimeError("redis package not installed - run: uv add redis") from e

        self._redis = redis.Redis.from_url(
            redis_url,
            decode_responses=True,  # We store JSON strings
            socket_connect_timeout=float(socket_connect_timeout_s),
            socket_timeout=float(socket_timeout_s),
        )
        self._key_prefix = key_prefix
        self._lock = threading.Lock()

        # Metrics
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.deletes = 0
        self.errors = 0

    def _make_key(self, cache_key: str) -> str:
        """Create Redis key with prefix."""
        return f"{self._key_prefix}{cache_key}"

    def ping(self) -> bool:
        """Check if Redis is reachable."""
        try:
            return bool(self._redis.ping())
        except Exception as e:
            logger.warning(f"Redis ping failed: {e}")
            return False

    def get(self, cache_key: str) -> Optional[LokiCacheEntry]:
        """
        Get cached entry from Redis.

        Returns:
            LokiCacheEntry if found and valid, None otherwise
        """
        try:
            redis_key = self._make_key(cache_key)
            raw = self._redis.get(redis_key)

            if raw is None:
                with self._lock:
                    self.misses += 1
                return None

            data = json.loads(raw)
            entry = LokiCacheEntry(
                file_path=data["file_path"],
                created_at=data["created_at"],
                result_count=data.get("result_count", 0),
                file_size=data.get("file_size", 0),
            )

            # Verify the cached file still exists on disk
            if not Path(entry.file_path).exists():
                logger.info(
                    f"Redis cache entry file missing, removing: key={cache_key[:12]}... "
                    f"file={entry.file_path}"
                )
                self.delete(cache_key)
                with self._lock:
                    self.misses += 1
                return None

            with self._lock:
                self.hits += 1

            logger.debug(
                f"Redis L2 cache HIT: key={cache_key[:12]}... file={Path(entry.file_path).name}"
            )
            return entry

        except Exception as e:
            with self._lock:
                self.errors += 1
            logger.warning(f"Redis get error for key={cache_key[:12]}...: {e}")
            return None

    def set(
        self,
        cache_key: str,
        file_path: str,
        *,
        result_count: int = 0,
        file_size: int = 0,
        ttl_seconds: int,
    ) -> bool:
        """
        Store cache entry in Redis.

        Args:
            cache_key: The cache key
            file_path: Path to the cached log file
            result_count: Number of results in the Loki response
            file_size: Size of the cached file in bytes
            ttl_seconds: TTL for the Redis entry

        Returns:
            True if stored successfully, False otherwise
        """
        try:
            redis_key = self._make_key(cache_key)
            data = {
                "file_path": file_path,
                "created_at": _now_s(),
                "result_count": result_count,
                "file_size": file_size,
            }

            self._redis.set(redis_key, json.dumps(data), ex=int(ttl_seconds))

            with self._lock:
                self.sets += 1

            logger.debug(
                f"Redis L2 cache SET: key={cache_key[:12]}... file={Path(file_path).name} "
                f"ttl={ttl_seconds}s"
            )
            return True

        except Exception as e:
            with self._lock:
                self.errors += 1
            logger.warning(f"Redis set error for key={cache_key[:12]}...: {e}")
            return False

    def delete(self, cache_key: str) -> bool:
        """Delete a cache entry from Redis."""
        try:
            redis_key = self._make_key(cache_key)
            deleted = self._redis.delete(redis_key)
            with self._lock:
                self.deletes += 1
            return bool(deleted)
        except Exception as e:
            with self._lock:
                self.errors += 1
            logger.warning(f"Redis delete error for key={cache_key[:12]}...: {e}")
            return False

    def clear(self, pattern: str = "*") -> int:
        """
        Clear cache entries matching pattern.

        Args:
            pattern: Redis key pattern to match (default: all loki keys)

        Returns:
            Number of keys deleted
        """
        try:
            full_pattern = f"{self._key_prefix}{pattern}"
            keys = list(self._redis.scan_iter(match=full_pattern, count=100))
            if keys:
                deleted = self._redis.delete(*keys)
                logger.info(f"Redis cache cleared: {deleted} keys matching {full_pattern}")
                return int(deleted)
            return 0
        except Exception as e:
            with self._lock:
                self.errors += 1
            logger.warning(f"Redis clear error: {e}")
            return 0

    def stats(self) -> Dict[str, Any]:
        """Get Redis backend statistics."""
        with self._lock:
            total = self.hits + self.misses
            hit_rate = (self.hits / total * 100) if total > 0 else 0.0
            return {
                "hits": self.hits,
                "misses": self.misses,
                "sets": self.sets,
                "deletes": self.deletes,
                "errors": self.errors,
                "hit_rate_percent": round(hit_rate, 2),
            }


class LokiCacheL2:
    """
    L2 cache manager for Loki queries using Redis.

    Handles automatic connection to Redis based on settings,
    with graceful fallback if Redis is unavailable.
    """

    def __init__(self):
        self._backend: Optional[LokiRedisBackend] = None
        self._lock = threading.Lock()
        self._last_error: Optional[str] = None
        self._last_checked_s: Optional[float] = None
        self._enabled = bool(getattr(settings, "LOKI_CACHE_REDIS_ENABLED", False))

    def _get_redis_url(self) -> Optional[str]:
        """Get Redis URL from settings with fallback."""
        url = getattr(settings, "LOKI_CACHE_REDIS_URL", None)
        if not url:
            # Fall back to LLM cache Redis URL
            url = getattr(settings, "LLM_CACHE_REDIS_URL", None)
        return url

    def _ensure_backend(self) -> Optional[LokiRedisBackend]:
        """Lazily initialize Redis backend."""
        if not self._enabled:
            return None

        redis_url = self._get_redis_url()
        if not redis_url:
            return None

        if self._backend is not None:
            return self._backend

        with self._lock:
            if self._backend is not None:
                return self._backend

            self._last_checked_s = _now_s()
            try:
                backend = LokiRedisBackend(
                    redis_url,
                    key_prefix="loki:",
                    socket_connect_timeout_s=0.5,
                    socket_timeout_s=0.5,
                )
                if not backend.ping():
                    self._last_error = "Redis ping failed"
                    logger.warning("Loki Redis L2 cache: ping failed, running without L2")
                    return None

                self._backend = backend
                self._last_error = None
                logger.info("Loki Redis L2 cache: connected successfully")
                return self._backend

            except Exception as e:
                self._last_error = str(e)
                logger.warning(f"Loki Redis L2 cache: connection failed: {e}")
                return None

    @property
    def is_enabled(self) -> bool:
        """Check if L2 cache is enabled and available."""
        return self._ensure_backend() is not None

    def get(self, cache_key: str) -> Optional[LokiCacheEntry]:
        """Get entry from L2 cache."""
        backend = self._ensure_backend()
        if backend is None:
            return None
        return backend.get(cache_key)

    def set(
        self,
        cache_key: str,
        file_path: str,
        *,
        result_count: int = 0,
        file_size: int = 0,
        ttl_seconds: int,
    ) -> bool:
        """Store entry in L2 cache."""
        backend = self._ensure_backend()
        if backend is None:
            return False
        return backend.set(
            cache_key,
            file_path,
            result_count=result_count,
            file_size=file_size,
            ttl_seconds=ttl_seconds,
        )

    def delete(self, cache_key: str) -> bool:
        """Delete entry from L2 cache."""
        backend = self._ensure_backend()
        if backend is None:
            return False
        return backend.delete(cache_key)

    def clear(self, pattern: str = "*") -> int:
        """Clear L2 cache entries matching pattern."""
        backend = self._ensure_backend()
        if backend is None:
            return 0
        return backend.clear(pattern)

    def stats(self) -> Dict[str, Any]:
        """Get L2 cache statistics."""
        backend = self._ensure_backend()
        return {
            "enabled": self._enabled,
            "connected": backend is not None,
            "redis_url_configured": bool(self._get_redis_url()),
            "last_error": self._last_error,
            "last_checked_s": self._last_checked_s,
            "backend_stats": backend.stats() if backend else None,
        }


# Singleton instance
_loki_cache_l2: Optional[LokiCacheL2] = None
_loki_cache_l2_lock = threading.Lock()


def get_loki_cache_l2() -> LokiCacheL2:
    """Get the global Loki L2 cache instance."""
    global _loki_cache_l2
    if _loki_cache_l2 is None:
        with _loki_cache_l2_lock:
            if _loki_cache_l2 is None:
                _loki_cache_l2 = LokiCacheL2()
    return _loki_cache_l2
