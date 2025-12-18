import threading
import time

from app.services.llm_gateway.gateway import CachePolicy, CacheableValue, LLMCacheGateway, make_cache_key


def test_make_cache_key_relevance_ignores_generated_timestamp():
    key1 = make_cache_key(
        cache_type="relevance_analysis",
        namespace="default",
        model="m",
        messages=[{"role": "user", "content": "Generated: 2025-01-01 00:00:00\nHello"}],
        options=None,
        gateway_version="v1",
        prompt_version="v1",
    )
    key2 = make_cache_key(
        cache_type="relevance_analysis",
        namespace="default",
        model="m",
        messages=[{"role": "user", "content": "Generated: 2025-12-31 23:59:59\nHello"}],
        options=None,
        gateway_version="v1",
        prompt_version="v1",
    )
    assert key1 == key2


def test_l1_hit_and_ttl_expiry():
    gw = LLMCacheGateway(
        enabled=True,
        gateway_version="v1",
        prompt_version="v1",
        namespace="default",
        l1_max_entries=100,
        l1_ttl_seconds=1,
        redis_url=None,
        l2_enabled=False,
    )

    calls = {"n": 0}

    def compute():
        calls["n"] += 1
        return CacheableValue(value={"ok": True}, cacheable=True)

    v1, d1 = gw.cached(
        cache_type="quality_assessment",
        model="m",
        messages=[{"role": "user", "content": "x"}],
        options=None,
        default_ttl_seconds=1,
        policy=CachePolicy(),
        compute=compute,
    )
    assert v1 == {"ok": True}
    assert calls["n"] == 1
    assert d1.status == "MISS"

    v2, d2 = gw.cached(
        cache_type="quality_assessment",
        model="m",
        messages=[{"role": "user", "content": "x"}],
        options=None,
        default_ttl_seconds=1,
        policy=CachePolicy(),
        compute=compute,
    )
    assert v2 == {"ok": True}
    assert calls["n"] == 1
    assert d2.status == "HIT_L1"

    time.sleep(1.05)
    v3, d3 = gw.cached(
        cache_type="quality_assessment",
        model="m",
        messages=[{"role": "user", "content": "x"}],
        options=None,
        default_ttl_seconds=1,
        policy=CachePolicy(),
        compute=compute,
    )
    assert v3 == {"ok": True}
    assert calls["n"] == 2
    assert d3.status == "MISS"


def test_l1_lru_eviction():
    gw = LLMCacheGateway(
        enabled=True,
        gateway_version="v1",
        prompt_version="v1",
        namespace="default",
        l1_max_entries=2,
        l1_ttl_seconds=60,
        redis_url=None,
        l2_enabled=False,
    )

    def compute_for(v):
        return lambda: CacheableValue(value={"v": v}, cacheable=True)

    gw.cached(
        cache_type="parameter_extraction",
        model="m",
        messages=[{"role": "user", "content": "a"}],
        options=None,
        default_ttl_seconds=60,
        policy=CachePolicy(),
        compute=compute_for("a"),
    )
    gw.cached(
        cache_type="parameter_extraction",
        model="m",
        messages=[{"role": "user", "content": "b"}],
        options=None,
        default_ttl_seconds=60,
        policy=CachePolicy(),
        compute=compute_for("b"),
    )
    # Touch "a" to make it most-recent
    gw.cached(
        cache_type="parameter_extraction",
        model="m",
        messages=[{"role": "user", "content": "a"}],
        options=None,
        default_ttl_seconds=60,
        policy=CachePolicy(),
        compute=compute_for("a2"),
    )
    # Insert "c" should evict "b"
    gw.cached(
        cache_type="parameter_extraction",
        model="m",
        messages=[{"role": "user", "content": "c"}],
        options=None,
        default_ttl_seconds=60,
        policy=CachePolicy(),
        compute=compute_for("c"),
    )

    calls = {"b": 0}

    def compute_b():
        calls["b"] += 1
        return CacheableValue(value={"v": "b"}, cacheable=True)

    _, diag_b = gw.cached(
        cache_type="parameter_extraction",
        model="m",
        messages=[{"role": "user", "content": "b"}],
        options=None,
        default_ttl_seconds=60,
        policy=CachePolicy(),
        compute=compute_b,
    )
    assert calls["b"] == 1
    assert diag_b.status == "MISS"


def test_singleflight_coalesces_threads():
    gw = LLMCacheGateway(
        enabled=True,
        gateway_version="v1",
        prompt_version="v1",
        namespace="default",
        l1_max_entries=100,
        l1_ttl_seconds=60,
        redis_url=None,
        l2_enabled=False,
    )

    calls = {"n": 0}
    lock = threading.Lock()

    def compute():
        with lock:
            calls["n"] += 1
        time.sleep(0.2)
        return CacheableValue(value={"ok": True}, cacheable=True)

    results = []

    def worker():
        v, d = gw.cached(
            cache_type="quality_assessment",
            model="m",
            messages=[{"role": "user", "content": "x"}],
            options=None,
            default_ttl_seconds=60,
            policy=CachePolicy(no_cache=True),  # force miss path for all threads
            compute=compute,
        )
        results.append((v, d.status))

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert calls["n"] == 1
    assert len(results) == 5
    assert all(v == {"ok": True} for v, _ in results)
    assert any(s == "COALESCED" for _, s in results)


def test_l2_auto_enable_probe(monkeypatch):
    import app.services.llm_gateway.gateway as gw_mod

    class FakeRedisBackend:
        def __init__(self, url, **kwargs):
            self.url = url
            self.hits = 0
            self.misses = 0
            self.sets = 0

        def ping(self):
            return True

    monkeypatch.setattr(gw_mod, "_RedisBackend", FakeRedisBackend)

    gw = gw_mod.LLMCacheGateway(
        enabled=True,
        gateway_version="v1",
        prompt_version="v1",
        namespace="default",
        l1_max_entries=10,
        l1_ttl_seconds=60,
        redis_url="redis://10.112.30.10:6379/0",
        l2_enabled=False,
        l2_auto_enable=True,
    )

    assert gw.l2 is not None
    assert gw.ping_l2()["enabled"] is True


def test_l2_probe_sets_error_on_failed_ping(monkeypatch):
    import app.services.llm_gateway.gateway as gw_mod

    class FakeRedisBackend:
        def __init__(self, url, **kwargs):
            self.url = url
            self.hits = 0
            self.misses = 0
            self.sets = 0

        def ping(self):
            return False

    monkeypatch.setattr(gw_mod, "_RedisBackend", FakeRedisBackend)

    gw = gw_mod.LLMCacheGateway(
        enabled=True,
        gateway_version="v1",
        prompt_version="v1",
        namespace="default",
        l1_max_entries=10,
        l1_ttl_seconds=60,
        redis_url="redis://10.112.30.10:6379/0",
        l2_enabled=False,
        l2_auto_enable=True,
    )

    assert gw.l2 is None
    assert gw.stats()["l2_last_error"] == "redis ping failed"
