# app/tests/test_cache.py
"""Tests for the TTLCache and CacheManager classes."""

import pytest
import time
from unittest.mock import patch

from app.services.cache import TTLCache, CacheManager, cached


class TestTTLCache:
    """Tests for TTLCache class."""

    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = TTLCache[str](default_ttl=60)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_nonexistent_key(self):
        """Test getting a key that doesn't exist."""
        cache = TTLCache[str](default_ttl=60)
        assert cache.get("nonexistent") is None

    def test_expiration(self):
        """Test that items expire after TTL."""
        cache = TTLCache[str](default_ttl=1)  # 1 second TTL
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_custom_ttl(self):
        """Test setting a custom TTL for a specific item."""
        cache = TTLCache[str](default_ttl=60)
        cache.set("key1", "value1", ttl=1)  # 1 second TTL

        assert cache.get("key1") == "value1"
        time.sleep(1.1)
        assert cache.get("key1") is None

    def test_delete(self):
        """Test deleting a key."""
        cache = TTLCache[str](default_ttl=60)
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None
        assert cache.delete("key1") is False  # Already deleted

    def test_clear(self):
        """Test clearing all entries."""
        cache = TTLCache[str](default_ttl=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.size() == 0

    def test_cleanup_expired(self):
        """Test cleanup of expired entries."""
        cache = TTLCache[str](default_ttl=1)
        cache.set("key1", "value1")
        cache.set("key2", "value2", ttl=60)  # This one won't expire

        time.sleep(1.1)
        removed = cache.cleanup_expired()
        assert removed == 1
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"

    def test_get_or_set(self):
        """Test get_or_set functionality."""
        cache = TTLCache[str](default_ttl=60)
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return "computed_value"

        # First call should compute
        result = cache.get_or_set("key1", factory)
        assert result == "computed_value"
        assert call_count == 1

        # Second call should use cache
        result = cache.get_or_set("key1", factory)
        assert result == "computed_value"
        assert call_count == 1  # Factory not called again

    def test_size(self):
        """Test size reporting."""
        cache = TTLCache[str](default_ttl=60)
        assert cache.size() == 0
        cache.set("key1", "value1")
        assert cache.size() == 1
        cache.set("key2", "value2")
        assert cache.size() == 2


class TestCacheManager:
    """Tests for CacheManager class."""

    def test_singleton(self):
        """Test that CacheManager is a singleton."""
        manager1 = CacheManager()
        manager2 = CacheManager()
        assert manager1 is manager2

    def test_get_cache(self):
        """Test getting named caches."""
        manager = CacheManager()
        cache1 = manager.get_cache("test_cache")
        cache2 = manager.get_cache("test_cache")
        assert cache1 is cache2

    def test_default_ttls(self):
        """Test that default TTLs are applied correctly."""
        manager = CacheManager()
        prompts_cache = manager.get_cache("prompts")
        assert prompts_cache.default_ttl == 300  # 5 minutes

        settings_cache = manager.get_cache("settings")
        assert settings_cache.default_ttl == 600  # 10 minutes

    def test_invalidate(self):
        """Test invalidating a specific cache."""
        manager = CacheManager()
        cache = manager.get_cache("test_invalidate")
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        manager.invalidate("test_invalidate")
        assert cache.get("key1") is None

    def test_invalidate_all(self):
        """Test invalidating all caches."""
        manager = CacheManager()
        cache1 = manager.get_cache("test_all_1")
        cache2 = manager.get_cache("test_all_2")
        cache1.set("key1", "value1")
        cache2.set("key2", "value2")

        manager.invalidate_all()
        assert cache1.get("key1") is None
        assert cache2.get("key2") is None

    def test_stats(self):
        """Test getting cache statistics."""
        manager = CacheManager()
        cache = manager.get_cache("test_stats")
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        stats = manager.stats()
        assert "test_stats" in stats
        assert stats["test_stats"] == 2


class TestCachedDecorator:
    """Tests for the @cached decorator."""

    def test_cached_decorator(self):
        """Test that the cached decorator works."""
        call_count = 0

        @cached("test_decorator", key_func=lambda x: f"key:{x}")
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return f"result:{x}"

        # First call should compute
        result = expensive_function("a")
        assert result == "result:a"
        assert call_count == 1

        # Second call should use cache
        result = expensive_function("a")
        assert result == "result:a"
        assert call_count == 1

        # Different argument should compute again
        result = expensive_function("b")
        assert result == "result:b"
        assert call_count == 2
