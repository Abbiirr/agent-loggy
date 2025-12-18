# app/services/cache.py
"""
TTL-based caching infrastructure with thread-safe in-memory caching.
Supports hot-reload via cache invalidation.
"""

import threading
import time
from typing import Any, Callable, Optional, TypeVar, Generic
from dataclasses import dataclass, field
from functools import wraps

T = TypeVar("T")


@dataclass
class CacheEntry(Generic[T]):
    """A single cache entry with value and expiration time."""
    value: T
    expires_at: float

    def is_expired(self) -> bool:
        return time.time() > self.expires_at


class TTLCache(Generic[T]):
    """
    Thread-safe TTL (Time-To-Live) cache implementation.

    Usage:
        cache = TTLCache[str](default_ttl=300)  # 5 minutes
        cache.set("key", "value")
        value = cache.get("key")
    """

    def __init__(self, default_ttl: int = 300):
        """
        Initialize TTLCache.

        Args:
            default_ttl: Default time-to-live in seconds (default: 300 = 5 minutes)
        """
        self._cache: dict[str, CacheEntry[T]] = {}
        self._lock = threading.RLock()
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[T]:
        """
        Get value from cache if it exists and is not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry.is_expired():
                del self._cache[key]
                return None
            return entry.value

    def set(self, key: str, value: T, ttl: Optional[int] = None) -> None:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + ttl
        with self._lock:
            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)

    def delete(self, key: str) -> bool:
        """
        Delete a specific key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if key was deleted, False if key didn't exist
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all entries from cache."""
        with self._lock:
            self._cache.clear()

    def cleanup_expired(self) -> int:
        """
        Remove all expired entries from cache.

        Returns:
            Number of entries removed
        """
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    def get_or_set(self, key: str, factory: Callable[[], T], ttl: Optional[int] = None) -> T:
        """
        Get value from cache or compute and store it if not present.

        Args:
            key: Cache key
            factory: Function to compute value if not in cache
            ttl: Time-to-live in seconds

        Returns:
            Cached or computed value
        """
        value = self.get(key)
        if value is not None:
            return value

        # Compute value outside lock to avoid blocking
        computed_value = factory()
        self.set(key, computed_value, ttl)
        return computed_value

    def size(self) -> int:
        """Return number of entries in cache (including expired)."""
        with self._lock:
            return len(self._cache)


class CacheManager:
    """
    Centralized cache management for different cache types.
    Provides named caches with configurable TTLs.

    Default TTLs:
        - prompts: 5 minutes (300s)
        - settings: 10 minutes (600s)
        - projects: 10 minutes (600s)
        - context_rules: 15 minutes (900s)
    """

    # Default TTLs in seconds
    DEFAULT_TTLS = {
        "prompts": 300,                    # 5 minutes
        "settings": 600,                   # 10 minutes
        "projects": 600,                   # 10 minutes
        "context_rules": 900,              # 15 minutes
        # Loki/HTTP request caching
        "loki": 14400,                     # 4 hours - log queries don't change often
        "loki_trace": 21600,               # 6 hours - individual trace logs
        # LLM response caching (extended TTLs)
        "llm_parameter_extraction": 7200,  # 2 hours - same query = same params
        "llm_trace_analysis": 14400,       # 4 hours - same logs = same analysis
        "llm_trace_entries_analysis": 14400,  # 4 hours
        "llm_quality_assessment": 7200,    # 2 hours
        "llm_relevance_analysis": 14400,   # 4 hours
    }

    _instance: Optional["CacheManager"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "CacheManager":
        """Singleton pattern for global cache management."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._caches: dict[str, TTLCache] = {}
        self._cache_lock = threading.RLock()
        self._initialized = True

    def get_cache(self, name: str, ttl: Optional[int] = None) -> TTLCache:
        """
        Get or create a named cache.

        Args:
            name: Cache name (e.g., 'prompts', 'settings')
            ttl: TTL in seconds (uses default for known names, 300 otherwise)

        Returns:
            TTLCache instance
        """
        with self._cache_lock:
            if name not in self._caches:
                default_ttl = ttl or self.DEFAULT_TTLS.get(name, 300)
                self._caches[name] = TTLCache(default_ttl=default_ttl)
            return self._caches[name]

    def invalidate(self, name: str) -> bool:
        """
        Invalidate (clear) a specific cache.

        Args:
            name: Cache name to invalidate

        Returns:
            True if cache was invalidated, False if cache didn't exist
        """
        with self._cache_lock:
            if name in self._caches:
                self._caches[name].clear()
                return True
            return False

    def invalidate_all(self) -> None:
        """Invalidate all caches (hot-reload trigger)."""
        with self._cache_lock:
            for cache in self._caches.values():
                cache.clear()

    def cleanup_all(self) -> dict[str, int]:
        """
        Cleanup expired entries from all caches.

        Returns:
            Dict mapping cache name to number of entries cleaned
        """
        results = {}
        with self._cache_lock:
            for name, cache in self._caches.items():
                results[name] = cache.cleanup_expired()
        return results

    def stats(self) -> dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dict mapping cache name to entry count
        """
        with self._cache_lock:
            return {name: cache.size() for name, cache in self._caches.items()}


def cached(cache_name: str, key_func: Optional[Callable[..., str]] = None, ttl: Optional[int] = None):
    """
    Decorator for caching function results.

    Usage:
        @cached("prompts", key_func=lambda name: f"prompt:{name}")
        def get_prompt(name: str) -> str:
            ...

    Args:
        cache_name: Name of the cache to use
        key_func: Function to generate cache key from arguments
        ttl: TTL override in seconds
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            cache = CacheManager().get_cache(cache_name)

            # Generate cache key
            if key_func:
                key = key_func(*args, **kwargs)
            else:
                # Default key from function name and args
                key = f"{func.__name__}:{args}:{kwargs}"

            # Try to get from cache
            cached_value = cache.get(key)
            if cached_value is not None:
                return cached_value

            # Compute and cache
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)
            return result

        return wrapper
    return decorator


# Global cache manager instance
cache_manager = CacheManager()
