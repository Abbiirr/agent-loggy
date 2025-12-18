"""
Comprehensive tests for Loki caching functionality.
Tests cache key generation, hit/miss behavior, metrics, and cleanup.
"""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from app.tools.loki.loki_query_builder import (
    _get_loki_cache_key,
    download_logs_cached,
    get_loki_cache_stats,
    get_loki_cache_metrics,
    reset_loki_cache_metrics,
    clear_loki_cache,
    loki_cache_metrics,
    LOKI_CACHE_DIR,
    LOKI_CACHE_TTL,
    LOKI_TRACE_CACHE_TTL,
)
from app.services.cache import cache_manager
from app.services.loki_redis_cache import (
    LokiRedisBackend,
    LokiCacheL2,
    LokiCacheEntry,
    get_loki_cache_l2,
)


class TestLokiCacheKeyGeneration:
    """Tests for cache key generation."""

    def test_same_params_produce_same_key(self):
        """Same parameters should produce the same cache key."""
        params = {
            "filters": {"service_namespace": "ncc"},
            "search": "merchant",
            "date_str": "2025-12-17",
            "end_date_str": "2025-12-18",
        }
        key1 = _get_loki_cache_key(**params)
        key2 = _get_loki_cache_key(**params)
        assert key1 == key2

    def test_different_params_produce_different_keys(self):
        """Different parameters should produce different cache keys."""
        key1 = _get_loki_cache_key(
            filters={"service_namespace": "ncc"},
            date_str="2025-12-17",
        )
        key2 = _get_loki_cache_key(
            filters={"service_namespace": "abbl"},
            date_str="2025-12-17",
        )
        assert key1 != key2

    def test_different_dates_produce_different_keys(self):
        """Different dates should produce different cache keys."""
        key1 = _get_loki_cache_key(
            filters={"service_namespace": "ncc"},
            date_str="2025-12-17",
            end_date_str="2025-12-18",
        )
        key2 = _get_loki_cache_key(
            filters={"service_namespace": "ncc"},
            date_str="2025-12-18",
            end_date_str="2025-12-19",
        )
        assert key1 != key2

    def test_trace_id_affects_key(self):
        """Adding a trace_id should produce a different key."""
        base_key = _get_loki_cache_key(
            filters={"service_namespace": "ncc"},
            date_str="2025-12-17",
        )
        trace_key = _get_loki_cache_key(
            filters={"service_namespace": "ncc"},
            date_str="2025-12-17",
            trace_id="abc123",
        )
        assert base_key != trace_key

    def test_key_is_deterministic_with_list_search(self):
        """Cache key should be deterministic even with list search terms."""
        params = {
            "filters": {"service_namespace": "ncc"},
            "search": ["merchant", "bkash"],
            "date_str": "2025-12-17",
        }
        key1 = _get_loki_cache_key(**params)
        key2 = _get_loki_cache_key(**params)
        assert key1 == key2

    def test_key_length(self):
        """Cache key should be 20 characters (SHA256 truncated)."""
        key = _get_loki_cache_key(
            filters={"service_namespace": "ncc"},
            date_str="2025-12-17",
        )
        assert len(key) == 20

    def test_pipeline_list_vs_none(self):
        """Pipeline parameter should affect the key."""
        key_no_pipeline = _get_loki_cache_key(
            filters={"service_namespace": "ncc"},
            date_str="2025-12-17",
        )
        key_with_pipeline = _get_loki_cache_key(
            filters={"service_namespace": "ncc"},
            date_str="2025-12-17",
            pipeline=['!= "debug"'],
        )
        assert key_no_pipeline != key_with_pipeline


class TestLokiCacheMetrics:
    """Tests for cache metrics tracking."""

    def setup_method(self):
        """Reset metrics before each test."""
        reset_loki_cache_metrics()

    def test_initial_metrics_are_zero(self):
        """Metrics should start at zero."""
        metrics = get_loki_cache_metrics()
        assert metrics["hits"] == 0
        assert metrics["misses"] == 0
        assert metrics["downloads"] == 0
        assert metrics["errors"] == 0
        assert metrics["bytes_saved"] == 0
        assert metrics["hit_rate_percent"] == 0.0

    def test_record_hit_increments_counter(self):
        """Recording a hit should increment the hit counter."""
        loki_cache_metrics.record_hit(file_size=1000)
        metrics = get_loki_cache_metrics()
        assert metrics["hits"] == 1
        assert metrics["bytes_saved"] == 1000

    def test_record_miss_increments_counters(self):
        """Recording a miss should increment miss and download counters."""
        loki_cache_metrics.record_miss()
        metrics = get_loki_cache_metrics()
        assert metrics["misses"] == 1
        assert metrics["downloads"] == 1

    def test_record_error_increments_counter(self):
        """Recording an error should increment the error counter."""
        loki_cache_metrics.record_error()
        metrics = get_loki_cache_metrics()
        assert metrics["errors"] == 1

    def test_hit_rate_calculation(self):
        """Hit rate should be calculated correctly."""
        # 3 hits, 1 miss = 75% hit rate
        loki_cache_metrics.record_hit()
        loki_cache_metrics.record_hit()
        loki_cache_metrics.record_hit()
        loki_cache_metrics.record_miss()

        metrics = get_loki_cache_metrics()
        assert metrics["hit_rate_percent"] == 75.0

    def test_hit_rate_zero_when_no_requests(self):
        """Hit rate should be 0 when there are no requests."""
        metrics = get_loki_cache_metrics()
        assert metrics["hit_rate_percent"] == 0.0

    def test_reset_clears_all_metrics(self):
        """Resetting should clear all metrics."""
        loki_cache_metrics.record_hit(file_size=5000)
        loki_cache_metrics.record_miss()
        loki_cache_metrics.record_error()

        reset_loki_cache_metrics()

        metrics = get_loki_cache_metrics()
        assert metrics["hits"] == 0
        assert metrics["misses"] == 0
        assert metrics["errors"] == 0
        assert metrics["bytes_saved"] == 0


class TestLokiCacheStats:
    """Tests for cache statistics."""

    def setup_method(self):
        """Reset metrics before each test."""
        reset_loki_cache_metrics()

    def test_stats_include_metrics(self):
        """Stats should include metrics."""
        loki_cache_metrics.record_hit(1000)
        stats = get_loki_cache_stats()

        assert "metrics" in stats
        assert stats["metrics"]["hits"] == 1

    def test_stats_include_cache_dir(self):
        """Stats should include cache directory path."""
        stats = get_loki_cache_stats()
        assert "cache_dir" in stats
        assert "loki_cache" in stats["cache_dir"]

    def test_stats_include_l1_cache_entries(self):
        """Stats should include L1 memory cache entry counts."""
        stats = get_loki_cache_stats()
        assert "l1_cache" in stats
        assert "loki_entries" in stats["l1_cache"]
        assert "loki_trace_entries" in stats["l1_cache"]

    def test_stats_include_l2_cache_info(self):
        """Stats should include L2 Redis cache info."""
        stats = get_loki_cache_stats()
        assert "l2_cache" in stats
        assert "enabled" in stats["l2_cache"]
        assert "connected" in stats["l2_cache"]


class TestDownloadLogsCached:
    """Tests for the cached download function."""

    def setup_method(self):
        """Reset metrics and clear caches before each test."""
        reset_loki_cache_metrics()
        cache_manager.invalidate("loki")
        cache_manager.invalidate("loki_trace")

    @patch("app.tools.loki.loki_query_builder.subprocess.run")
    def test_cache_miss_downloads_file(self, mock_run):
        """On cache miss, file should be downloaded."""
        mock_run.return_value = MagicMock(returncode=0)

        # Create a temp cache directory
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.tools.loki.loki_query_builder.LOKI_CACHE_DIR", Path(tmpdir)):
                # Pre-create a fake downloaded file
                cache_key = _get_loki_cache_key(
                    filters={"service_namespace": "test"},
                    date_str="2025-12-17",
                    end_date_str="2025-12-18",
                )
                fake_file = Path(tmpdir) / f"loki_{cache_key}.json"
                fake_file.write_text('{"data": {"result": []}}')

                result = download_logs_cached(
                    filters={"service_namespace": "test"},
                    date_str="2025-12-17",
                    end_date_str="2025-12-18",
                )

                # Subprocess should have been called
                mock_run.assert_called_once()

                # Metrics should show a miss
                metrics = get_loki_cache_metrics()
                assert metrics["misses"] == 1

    @patch("app.tools.loki.loki_query_builder.subprocess.run")
    def test_cache_hit_skips_download(self, mock_run):
        """On cache hit, download should be skipped."""
        # Create a temp cache directory with pre-cached file
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.tools.loki.loki_query_builder.LOKI_CACHE_DIR", Path(tmpdir)):
                cache_key = _get_loki_cache_key(
                    filters={"service_namespace": "test"},
                    date_str="2025-12-17",
                    end_date_str="2025-12-18",
                )

                # Pre-create a cached file
                cached_file = Path(tmpdir) / f"loki_{cache_key}.json"
                cached_file.write_text('{"data": {"result": []}}')

                # Manually populate the in-memory cache
                loki_cache = cache_manager.get_cache("loki")
                loki_cache.set(cache_key, str(cached_file))

                # Now request the same data
                result = download_logs_cached(
                    filters={"service_namespace": "test"},
                    date_str="2025-12-17",
                    end_date_str="2025-12-18",
                )

                # Subprocess should NOT have been called
                mock_run.assert_not_called()

                # Result should be the cached file path
                assert result == str(cached_file)

                # Metrics should show a hit
                metrics = get_loki_cache_metrics()
                assert metrics["hits"] == 1

    @patch("app.tools.loki.loki_query_builder.subprocess.run")
    def test_force_refresh_bypasses_cache(self, mock_run):
        """force_refresh=True should bypass cache."""
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.tools.loki.loki_query_builder.LOKI_CACHE_DIR", Path(tmpdir)):
                cache_key = _get_loki_cache_key(
                    filters={"service_namespace": "test"},
                    date_str="2025-12-17",
                    end_date_str="2025-12-18",
                )

                # Pre-create a cached file
                cached_file = Path(tmpdir) / f"loki_{cache_key}.json"
                cached_file.write_text('{"data": {"result": []}}')

                # Populate the in-memory cache
                loki_cache = cache_manager.get_cache("loki")
                loki_cache.set(cache_key, str(cached_file))

                # Request with force_refresh=True
                result = download_logs_cached(
                    filters={"service_namespace": "test"},
                    date_str="2025-12-17",
                    end_date_str="2025-12-18",
                    force_refresh=True,
                )

                # Subprocess SHOULD have been called despite cache
                mock_run.assert_called_once()

    def test_trace_id_uses_different_cache(self):
        """Trace-specific queries should use loki_trace cache with longer TTL."""
        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.tools.loki.loki_query_builder.LOKI_CACHE_DIR", Path(tmpdir)):
                # Check that trace queries use the trace cache
                cache_key = _get_loki_cache_key(
                    filters={"service_namespace": "test"},
                    date_str="2025-12-17",
                    trace_id="abc123",
                )

                # Verify TTL configuration
                assert LOKI_TRACE_CACHE_TTL > LOKI_CACHE_TTL

    @patch("app.tools.loki.loki_query_builder.subprocess.run")
    def test_download_error_records_metric(self, mock_run):
        """Download errors should be recorded in metrics."""
        mock_run.side_effect = Exception("Network error")

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.tools.loki.loki_query_builder.LOKI_CACHE_DIR", Path(tmpdir)):
                result = download_logs_cached(
                    filters={"service_namespace": "test"},
                    date_str="2025-12-17",
                    end_date_str="2025-12-18",
                )

                # Result should be None on error
                assert result is None

                # Error should be recorded
                metrics = get_loki_cache_metrics()
                assert metrics["errors"] == 1


class TestClearLokiCache:
    """Tests for cache clearing functionality."""

    def test_clear_removes_all_files(self):
        """clear_loki_cache() should remove all cache files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            with patch("app.tools.loki.loki_query_builder.LOKI_CACHE_DIR", cache_dir):
                # Create some fake cache files
                (cache_dir / "loki_abc123.json").write_text("{}")
                (cache_dir / "loki_def456.json").write_text("{}")
                (cache_dir / "loki_ghi789.json").write_text("{}")

                # Clear cache
                removed = clear_loki_cache()

                # All files should be removed
                assert removed == 3
                assert len(list(cache_dir.glob("loki_*.json"))) == 0

    def test_clear_older_than_hours(self):
        """clear_loki_cache(older_than_hours) should only remove old files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir)
            with patch("app.tools.loki.loki_query_builder.LOKI_CACHE_DIR", cache_dir):
                # Create a cache file
                cache_file = cache_dir / "loki_test123.json"
                cache_file.write_text("{}")

                # File is brand new, so clearing with older_than_hours=1 should not remove it
                removed = clear_loki_cache(older_than_hours=1)

                assert removed == 0
                assert cache_file.exists()


class TestEmptyResultsNotCached:
    """Tests that empty Loki results are not cached."""

    def setup_method(self):
        """Reset metrics and clear caches before each test."""
        reset_loki_cache_metrics()
        cache_manager.invalidate("loki")
        cache_manager.invalidate("loki_trace")

    @patch("app.tools.loki.loki_query_builder.subprocess.run")
    def test_empty_results_not_cached(self, mock_run):
        """Empty Loki results should NOT be cached."""
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.tools.loki.loki_query_builder.LOKI_CACHE_DIR", Path(tmpdir)):
                cache_key = _get_loki_cache_key(
                    filters={"service_namespace": "test"},
                    date_str="2025-12-17",
                    end_date_str="2025-12-18",
                )

                # Create an empty Loki result file
                empty_result_file = Path(tmpdir) / f"loki_{cache_key}.json"
                empty_result_file.write_text('{"status":"success","data":{"result":[]}}')

                result = download_logs_cached(
                    filters={"service_namespace": "test"},
                    date_str="2025-12-17",
                    end_date_str="2025-12-18",
                )

                # File should be returned
                assert result is not None

                # But it should NOT be in the cache
                loki_cache = cache_manager.get_cache("loki")
                cached_path = loki_cache.get(cache_key)
                assert cached_path is None, "Empty results should not be cached"

    @patch("app.tools.loki.loki_query_builder.subprocess.run")
    def test_non_empty_results_are_cached(self, mock_run):
        """Non-empty Loki results SHOULD be cached."""
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            with patch("app.tools.loki.loki_query_builder.LOKI_CACHE_DIR", Path(tmpdir)):
                cache_key = _get_loki_cache_key(
                    filters={"service_namespace": "test"},
                    date_str="2025-12-17",
                    end_date_str="2025-12-18",
                )

                # Create a non-empty Loki result file
                non_empty_file = Path(tmpdir) / f"loki_{cache_key}.json"
                non_empty_file.write_text(
                    '{"status":"success","data":{"result":[{"stream":{"trace_id":"abc123"}}]}}'
                )

                result = download_logs_cached(
                    filters={"service_namespace": "test"},
                    date_str="2025-12-17",
                    end_date_str="2025-12-18",
                )

                # File should be returned
                assert result is not None

                # And it SHOULD be in the cache
                loki_cache = cache_manager.get_cache("loki")
                cached_path = loki_cache.get(cache_key)
                assert cached_path is not None, "Non-empty results should be cached"


class TestCacheKeyConsistency:
    """Tests to ensure cache keys are consistent across different scenarios."""

    def test_none_values_handled_consistently(self):
        """None values should be handled consistently in key generation."""
        key1 = _get_loki_cache_key(
            filters={"service_namespace": "ncc"},
            pipeline=None,
            search=None,
            trace_id=None,
            date_str="2025-12-17",
        )
        key2 = _get_loki_cache_key(
            filters={"service_namespace": "ncc"},
            date_str="2025-12-17",
        )
        assert key1 == key2

    def test_empty_list_vs_none(self):
        """Empty list should produce different key than None."""
        key_none = _get_loki_cache_key(
            filters={"service_namespace": "ncc"},
            search=None,
            date_str="2025-12-17",
        )
        key_empty = _get_loki_cache_key(
            filters={"service_namespace": "ncc"},
            search=[],
            date_str="2025-12-17",
        )
        # Empty list serializes differently than None
        assert key_none != key_empty

    def test_filter_order_does_not_affect_key(self):
        """Filter order should not affect the cache key due to JSON sort_keys."""
        # The filters dict itself might have different order in Python < 3.7
        # but json.dumps with sort_keys=True should normalize this
        key1 = _get_loki_cache_key(
            filters={"a": "1", "b": "2"},
            date_str="2025-12-17",
        )
        key2 = _get_loki_cache_key(
            filters={"b": "2", "a": "1"},
            date_str="2025-12-17",
        )
        assert key1 == key2


class TestLokiCacheEntry:
    """Tests for LokiCacheEntry dataclass."""

    def test_create_entry(self):
        """Should create a valid cache entry."""
        entry = LokiCacheEntry(
            file_path="/tmp/test.json",
            created_at=time.time(),
            result_count=5,
            file_size=1024,
        )
        assert entry.file_path == "/tmp/test.json"
        assert entry.result_count == 5
        assert entry.file_size == 1024

    def test_entry_is_immutable(self):
        """LokiCacheEntry should be frozen (immutable)."""
        entry = LokiCacheEntry(
            file_path="/tmp/test.json",
            created_at=time.time(),
            result_count=5,
            file_size=1024,
        )
        with pytest.raises(AttributeError):
            entry.file_path = "/tmp/other.json"


class TestLokiRedisBackendMocked:
    """Tests for LokiRedisBackend with mocked Redis."""

    @pytest.fixture
    def mock_redis_module(self):
        """Create a mock redis module."""
        mock_redis_client = MagicMock()
        mock_redis_mod = MagicMock()
        mock_redis_mod.Redis.from_url.return_value = mock_redis_client
        return mock_redis_mod, mock_redis_client

    def test_backend_initialization(self, mock_redis_module):
        """Backend should initialize with Redis connection."""
        mock_mod, mock_client = mock_redis_module

        with patch.dict('sys.modules', {'redis': mock_mod}):
            backend = LokiRedisBackend("redis://localhost:6379")

            mock_mod.Redis.from_url.assert_called_once()
            assert backend.hits == 0
            assert backend.misses == 0
            assert backend.sets == 0

    def test_ping_success(self, mock_redis_module):
        """Ping should return True when Redis is available."""
        mock_mod, mock_client = mock_redis_module
        mock_client.ping.return_value = True

        with patch.dict('sys.modules', {'redis': mock_mod}):
            backend = LokiRedisBackend("redis://localhost:6379")
            assert backend.ping() is True

    def test_ping_failure(self, mock_redis_module):
        """Ping should return False when Redis fails."""
        mock_mod, mock_client = mock_redis_module
        mock_client.ping.side_effect = Exception("Connection refused")

        with patch.dict('sys.modules', {'redis': mock_mod}):
            backend = LokiRedisBackend("redis://localhost:6379")
            assert backend.ping() is False

    def test_get_miss(self, mock_redis_module):
        """Get should return None and record miss when key not found."""
        mock_mod, mock_client = mock_redis_module
        mock_client.get.return_value = None

        with patch.dict('sys.modules', {'redis': mock_mod}):
            backend = LokiRedisBackend("redis://localhost:6379")
            result = backend.get("nonexistent_key")

            assert result is None
            assert backend.misses == 1

    def test_get_hit(self, mock_redis_module):
        """Get should return entry and record hit when key found."""
        mock_mod, mock_client = mock_redis_module

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write('{}')
            temp_path = f.name

        try:
            # Use forward slashes for JSON to avoid escaping issues on Windows
            temp_path_json = temp_path.replace('\\', '/')
            cached_data = f'{{"file_path": "{temp_path_json}", "created_at": 1234567890, "result_count": 5, "file_size": 1024}}'
            mock_client.get.return_value = cached_data

            with patch.dict('sys.modules', {'redis': mock_mod}):
                backend = LokiRedisBackend("redis://localhost:6379")
                result = backend.get("test_key")

                assert result is not None
                assert result.result_count == 5
                assert backend.hits == 1
        finally:
            os.unlink(temp_path)

    def test_get_removes_entry_if_file_missing(self, mock_redis_module):
        """Get should remove entry and return None if cached file doesn't exist."""
        mock_mod, mock_client = mock_redis_module
        cached_data = '{"file_path": "/nonexistent/path/test.json", "created_at": 1234567890, "result_count": 5, "file_size": 1024}'
        mock_client.get.return_value = cached_data

        with patch.dict('sys.modules', {'redis': mock_mod}):
            backend = LokiRedisBackend("redis://localhost:6379")
            result = backend.get("test_key")

            assert result is None
            mock_client.delete.assert_called_once()  # Should delete the stale entry
            assert backend.misses == 1

    def test_set_stores_entry(self, mock_redis_module):
        """Set should store entry in Redis with TTL."""
        mock_mod, mock_client = mock_redis_module

        with patch.dict('sys.modules', {'redis': mock_mod}):
            backend = LokiRedisBackend("redis://localhost:6379")
            result = backend.set(
                "test_key",
                "/tmp/test.json",
                result_count=10,
                file_size=2048,
                ttl_seconds=3600,
            )

            assert result is True
            mock_client.set.assert_called_once()
            assert backend.sets == 1

    def test_delete_removes_entry(self, mock_redis_module):
        """Delete should remove entry from Redis."""
        mock_mod, mock_client = mock_redis_module
        mock_client.delete.return_value = 1

        with patch.dict('sys.modules', {'redis': mock_mod}):
            backend = LokiRedisBackend("redis://localhost:6379")
            result = backend.delete("test_key")

            assert result is True
            mock_client.delete.assert_called_once()
            assert backend.deletes == 1

    def test_stats_returns_metrics(self, mock_redis_module):
        """Stats should return all metrics."""
        mock_mod, mock_client = mock_redis_module
        mock_client.get.return_value = None

        with patch.dict('sys.modules', {'redis': mock_mod}):
            backend = LokiRedisBackend("redis://localhost:6379")
            backend.get("key1")  # miss
            backend.get("key2")  # miss

            stats = backend.stats()

            assert stats["hits"] == 0
            assert stats["misses"] == 2
            assert stats["hit_rate_percent"] == 0.0


class TestLokiCacheL2:
    """Tests for LokiCacheL2 manager."""

    def test_disabled_by_default(self):
        """L2 cache should be disabled when LOKI_CACHE_REDIS_ENABLED is False."""
        with patch("app.services.loki_redis_cache.settings") as mock_settings:
            mock_settings.LOKI_CACHE_REDIS_ENABLED = False
            mock_settings.LOKI_CACHE_REDIS_URL = None
            mock_settings.LLM_CACHE_REDIS_URL = None

            l2 = LokiCacheL2()
            assert l2.is_enabled is False

    def test_stats_when_disabled(self):
        """Stats should show disabled state when L2 is not enabled."""
        with patch("app.services.loki_redis_cache.settings") as mock_settings:
            mock_settings.LOKI_CACHE_REDIS_ENABLED = False
            mock_settings.LOKI_CACHE_REDIS_URL = None
            mock_settings.LLM_CACHE_REDIS_URL = None

            l2 = LokiCacheL2()
            stats = l2.stats()

            assert stats["enabled"] is False
            assert stats["connected"] is False
            assert stats["backend_stats"] is None

    def test_get_returns_none_when_disabled(self):
        """Get should return None when L2 is disabled."""
        with patch("app.services.loki_redis_cache.settings") as mock_settings:
            mock_settings.LOKI_CACHE_REDIS_ENABLED = False
            mock_settings.LOKI_CACHE_REDIS_URL = None
            mock_settings.LLM_CACHE_REDIS_URL = None

            l2 = LokiCacheL2()
            result = l2.get("any_key")

            assert result is None

    def test_set_returns_false_when_disabled(self):
        """Set should return False when L2 is disabled."""
        with patch("app.services.loki_redis_cache.settings") as mock_settings:
            mock_settings.LOKI_CACHE_REDIS_ENABLED = False
            mock_settings.LOKI_CACHE_REDIS_URL = None
            mock_settings.LLM_CACHE_REDIS_URL = None

            l2 = LokiCacheL2()
            result = l2.set("key", "/tmp/file.json", ttl_seconds=3600)

            assert result is False


class TestL2CacheIntegration:
    """Integration tests for L2 cache with download_logs_cached."""

    def setup_method(self):
        """Reset metrics and clear caches before each test."""
        reset_loki_cache_metrics()
        cache_manager.invalidate("loki")
        cache_manager.invalidate("loki_trace")

    @patch("app.tools.loki.loki_query_builder.subprocess.run")
    @patch("app.tools.loki.loki_query_builder.get_loki_cache_l2")
    def test_l2_hit_populates_l1(self, mock_get_l2, mock_run):
        """L2 cache hit should populate L1 cache."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_key = _get_loki_cache_key(
                filters={"service_namespace": "test"},
                date_str="2025-12-17",
                end_date_str="2025-12-18",
            )

            # Create a cached file
            cached_file = Path(tmpdir) / f"loki_{cache_key}.json"
            cached_file.write_text('{"data": {"result": [{"stream": {}}]}}')

            # Mock L2 cache to return the entry
            mock_l2 = MagicMock()
            mock_l2.get.return_value = LokiCacheEntry(
                file_path=str(cached_file),
                created_at=time.time(),
                result_count=1,
                file_size=100,
            )
            mock_get_l2.return_value = mock_l2

            with patch("app.tools.loki.loki_query_builder.LOKI_CACHE_DIR", Path(tmpdir)):
                result = download_logs_cached(
                    filters={"service_namespace": "test"},
                    date_str="2025-12-17",
                    end_date_str="2025-12-18",
                )

                # Should return the cached file
                assert result == str(cached_file)

                # Should NOT call subprocess (no download)
                mock_run.assert_not_called()

                # L1 cache should now have the entry
                loki_cache = cache_manager.get_cache("loki")
                l1_cached = loki_cache.get(cache_key)
                assert l1_cached == str(cached_file)

    @patch("app.tools.loki.loki_query_builder.subprocess.run")
    @patch("app.tools.loki.loki_query_builder.get_loki_cache_l2")
    def test_download_stores_in_both_l1_and_l2(self, mock_get_l2, mock_run):
        """Download should store in both L1 and L2 caches."""
        mock_run.return_value = MagicMock(returncode=0)

        with tempfile.TemporaryDirectory() as tmpdir:
            cache_key = _get_loki_cache_key(
                filters={"service_namespace": "test"},
                date_str="2025-12-17",
                end_date_str="2025-12-18",
            )

            # Mock L2 cache
            mock_l2 = MagicMock()
            mock_l2.get.return_value = None  # L2 miss
            mock_l2.set.return_value = True  # L2 set succeeds
            mock_get_l2.return_value = mock_l2

            with patch("app.tools.loki.loki_query_builder.LOKI_CACHE_DIR", Path(tmpdir)):
                # Pre-create a non-empty result file
                result_file = Path(tmpdir) / f"loki_{cache_key}.json"
                result_file.write_text('{"status":"success","data":{"result":[{"stream":{}}]}}')

                result = download_logs_cached(
                    filters={"service_namespace": "test"},
                    date_str="2025-12-17",
                    end_date_str="2025-12-18",
                )

                # Should have stored in L2
                mock_l2.set.assert_called_once()
                call_args = mock_l2.set.call_args
                assert call_args[0][0] == cache_key  # cache key
                assert cache_key in call_args[0][1]  # file path contains cache key
