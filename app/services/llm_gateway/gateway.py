from __future__ import annotations

import hashlib
import json
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple, TypeVar

from app.config import settings

T = TypeVar("T")


_RE_GENERATED_LINE = re.compile(r"(?mi)^\s*Generated:\s*.*?$")
_RE_ANALYSIS_COMPLETED_LINE = re.compile(r"(?mi)^\s*Analysis completed:\s*.*?$")
_RE_TIMESTAMP_FIELD_LINE = re.compile(r"(?mi)^\s*-\s*Timestamp:\s*.*?$")


def _canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256_hex(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def _now_s() -> float:
    return time.time()


def _normalize_text(text: str) -> str:
    return (text or "").replace("\r\n", "\n").strip()


def canonicalize_messages(messages: list[dict[str, Any]], *, cache_type: str) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for msg in messages or []:
        role = msg.get("role")
        content = msg.get("content")
        if isinstance(content, str):
            content = _normalize_text(content)
            if cache_type == "relevance_analysis":
                content = _RE_GENERATED_LINE.sub("", content)
                content = _RE_ANALYSIS_COMPLETED_LINE.sub("", content)
                content = _RE_TIMESTAMP_FIELD_LINE.sub("", content)
                content = _normalize_text(content)
        normalized.append({"role": role, "content": content})
    return normalized


def _filter_generation_options(options: Optional[dict[str, Any]]) -> dict[str, Any]:
    if not options:
        return {}
    filtered = {}
    for k, v in options.items():
        if k == "timeout":
            continue
        filtered[k] = v
    return filtered


def make_cache_key(
    *,
    cache_type: str,
    namespace: str,
    model: str,
    messages: list[dict[str, Any]],
    options: Optional[dict[str, Any]],
    gateway_version: str,
    prompt_version: str,
) -> str:
    payload = {
        "cache_type": cache_type,
        "namespace": namespace,
        "gateway_version": gateway_version,
        "prompt_version": prompt_version,
        "model": model,
        "messages": canonicalize_messages(messages, cache_type=cache_type),
        "options": _filter_generation_options(options),
    }
    digest = _sha256_hex(_canonical_json(payload))
    return f"llm:{cache_type}:{digest}"


@dataclass(frozen=True)
class CachePolicy:
    enabled: bool = True
    no_cache: bool = False
    no_store: bool = False
    ttl_seconds: Optional[int] = None
    s_maxage_seconds: Optional[int] = None
    namespace: Optional[str] = None

    @staticmethod
    def from_dict(d: Optional[dict[str, Any]]) -> "CachePolicy":
        if not d:
            return CachePolicy()
        return CachePolicy(
            enabled=bool(d.get("enabled", True)),
            no_cache=bool(d.get("no_cache", False)),
            no_store=bool(d.get("no_store", False)),
            ttl_seconds=d.get("ttl_seconds"),
            s_maxage_seconds=d.get("s_maxage_seconds"),
            namespace=d.get("namespace"),
        )


@dataclass(frozen=True)
class CacheDiagnostics:
    status: str  # HIT_L1 | HIT_L2 | MISS | BYPASS | COALESCED
    key_prefix: str
    layer: Optional[str] = None  # l1|l2
    ttl_seconds: Optional[int] = None
    waited: bool = False


@dataclass(frozen=True)
class CacheableValue:
    value: Any
    cacheable: bool = True


class _LRUTTLCache:
    def __init__(self, *, max_entries: int, default_ttl_seconds: int):
        from collections import OrderedDict

        self._data: "OrderedDict[str, tuple[float, bytes]]" = OrderedDict()
        self._max = max_entries
        self._default_ttl = default_ttl_seconds
        self._lock = threading.RLock()

        self.hits = 0
        self.misses = 0
        self.evictions = 0
        self.sets = 0

    def _purge_expired_locked(self) -> None:
        now = _now_s()
        expired = [k for k, (exp, _) in self._data.items() if exp <= now]
        for k in expired:
            self._data.pop(k, None)

    def get(self, key: str) -> Optional[bytes]:
        with self._lock:
            item = self._data.get(key)
            if item is None:
                self.misses += 1
                return None
            exp, payload = item
            if exp <= _now_s():
                self._data.pop(key, None)
                self.misses += 1
                return None
            self._data.move_to_end(key)
            self.hits += 1
            return payload

    def set(self, key: str, payload: bytes, *, ttl_seconds: Optional[int] = None) -> None:
        ttl = int(ttl_seconds if ttl_seconds is not None else self._default_ttl)
        exp = _now_s() + max(ttl, 1)
        with self._lock:
            self._purge_expired_locked()
            if key in self._data:
                self._data.pop(key, None)
            self._data[key] = (exp, payload)
            self._data.move_to_end(key)
            self.sets += 1
            while len(self._data) > self._max:
                self._data.popitem(last=False)
                self.evictions += 1

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._data.pop(key, None) is not None

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

    def size(self) -> int:
        with self._lock:
            return len(self._data)


class _ThreadSingleFlight:
    def __init__(self):
        from concurrent.futures import Future

        self._Future = Future
        self._lock = threading.Lock()
        self._inflight: dict[str, "Future[Any]"] = {}

    def do(self, key: str, fn: Callable[[], T]) -> Tuple[T, bool]:
        with self._lock:
            fut = self._inflight.get(key)
            if fut is None:
                fut = self._Future()
                self._inflight[key] = fut
                leader = True
            else:
                leader = False

        if not leader:
            return fut.result(), True

        try:
            result = fn()
            fut.set_result(result)
            return result, False
        except Exception as e:  # pragma: no cover
            fut.set_exception(e)
            raise
        finally:
            with self._lock:
                self._inflight.pop(key, None)


class _RedisBackend:
    def __init__(self, redis_url: str, *, socket_connect_timeout_s: float = 1.0, socket_timeout_s: float = 1.0):
        try:
            import redis  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("redis package not installed") from e
        self._redis = redis.Redis.from_url(
            redis_url,
            decode_responses=False,
            socket_connect_timeout=float(socket_connect_timeout_s),
            socket_timeout=float(socket_timeout_s),
        )

        self.hits = 0
        self.misses = 0
        self.sets = 0

        self._unlock_script = self._redis.register_script(
            "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end"
        )

    def ping(self) -> bool:
        return bool(self._redis.ping())

    def get(self, key: str) -> Optional[bytes]:
        raw = self._redis.get(key)
        if raw is None:
            self.misses += 1
            return None
        self.hits += 1
        return raw

    def set(self, key: str, payload: bytes, *, ttl_seconds: int) -> None:
        self._redis.set(key, payload, ex=int(ttl_seconds))
        self.sets += 1

    def delete(self, key: str) -> int:
        return int(self._redis.delete(key))

    def acquire_lock(self, key: str, *, ttl_ms: int) -> Optional[str]:
        token = _sha256_hex(f"{key}:{_now_s()}:{threading.get_ident()}")
        ok = self._redis.set(f"lock:{key}", token.encode("utf-8"), nx=True, px=int(ttl_ms))
        return token if ok else None

    def release_lock(self, key: str, token: str) -> None:
        try:
            self._unlock_script(keys=[f"lock:{key}"], args=[token.encode("utf-8")])
        except Exception:  # pragma: no cover
            return


class LLMCacheGateway:
    def __init__(
        self,
        *,
        enabled: bool,
        gateway_version: str,
        prompt_version: str,
        namespace: str,
        l1_max_entries: int,
        l1_ttl_seconds: int,
        redis_url: Optional[str],
        l2_enabled: bool,
        l2_auto_enable: bool = True,
        lock_ttl_ms: int = 30_000,
        lock_wait_ms: int = 2_000,
    ):
        self.enabled = enabled
        self.gateway_version = gateway_version
        self.prompt_version = prompt_version
        self.namespace = namespace

        self.l1 = _LRUTTLCache(max_entries=l1_max_entries, default_ttl_seconds=l1_ttl_seconds)
        self.sf = _ThreadSingleFlight()

        self.l2: Optional[_RedisBackend] = None
        self._redis_url = redis_url
        self._l2_enabled_flag = bool(l2_enabled)
        self._l2_auto_enable = bool(l2_auto_enable)
        self._l2_lock = threading.Lock()
        self._l2_last_error: Optional[str] = None
        self._l2_last_checked_s: Optional[float] = None

        if (self._l2_enabled_flag or self._l2_auto_enable) and self._redis_url:
            self._ensure_l2()

        self.lock_ttl_ms = lock_ttl_ms
        self.lock_wait_ms = lock_wait_ms

        self.calls = 0
        self.bypasses = 0
        self.misses = 0
        self.l1_hits = 0
        self.l2_hits = 0
        self.coalesced = 0
        self.stores = 0

    @staticmethod
    def from_settings() -> "LLMCacheGateway":
        enabled = bool(getattr(settings, "LLM_CACHE_ENABLED", True))
        namespace = getattr(settings, "LLM_CACHE_NAMESPACE", "default")
        gateway_version = getattr(settings, "LLM_GATEWAY_VERSION", "v1")
        prompt_version = getattr(settings, "PROMPT_VERSION", "v1")

        l1_max_entries = int(getattr(settings, "LLM_CACHE_L1_MAX_ENTRIES", 10_000))
        l1_ttl_seconds = int(getattr(settings, "LLM_CACHE_L1_TTL_SECONDS", 60))

        redis_url = getattr(settings, "LLM_CACHE_REDIS_URL", None)
        l2_enabled = bool(getattr(settings, "LLM_CACHE_L2_ENABLED", False))
        l2_auto_enable = bool(getattr(settings, "LLM_CACHE_L2_AUTO_ENABLE", True))
        return LLMCacheGateway(
            enabled=enabled,
            gateway_version=gateway_version,
            prompt_version=prompt_version,
            namespace=namespace,
            l1_max_entries=l1_max_entries,
            l1_ttl_seconds=l1_ttl_seconds,
            redis_url=redis_url,
            l2_enabled=l2_enabled,
            l2_auto_enable=l2_auto_enable,
        )

    def _ensure_l2(self) -> None:
        if not self._redis_url:
            return
        if not (self._l2_enabled_flag or self._l2_auto_enable):
            return
        if self.l2 is not None:
            return
        with self._l2_lock:
            if self.l2 is not None:
                return
            self._l2_last_checked_s = _now_s()
            try:
                backend = _RedisBackend(self._redis_url, socket_connect_timeout_s=0.5, socket_timeout_s=0.5)
                if not backend.ping():
                    self._l2_last_error = "redis ping failed"
                    return
                self.l2 = backend
                self._l2_last_error = None
            except Exception as e:
                self._l2_last_error = str(e)
                return

    def _encode_envelope(self, value: Any) -> bytes:
        envelope = {"created_at": _now_s(), "value": value}
        return _canonical_json(envelope).encode("utf-8")

    def _decode_envelope(self, payload: bytes) -> tuple[float, Any]:
        obj = json.loads(payload.decode("utf-8"))
        created_at = float(obj.get("created_at") or 0.0)
        return created_at, obj.get("value")

    def _is_stale(self, created_at: float, *, s_maxage_seconds: Optional[int]) -> bool:
        if s_maxage_seconds is None:
            return False
        return (_now_s() - created_at) > float(s_maxage_seconds)

    def cached(
        self,
        *,
        cache_type: str,
        model: str,
        messages: list[dict[str, Any]],
        options: Optional[dict[str, Any]],
        default_ttl_seconds: int,
        policy: Optional[CachePolicy],
        compute: Callable[[], CacheableValue],
    ) -> tuple[Any, CacheDiagnostics]:
        self.calls += 1

        pol = policy or CachePolicy()
        if not self.enabled or not pol.enabled:
            self.bypasses += 1
            v = compute()
            return v.value, CacheDiagnostics(status="BYPASS", key_prefix="", ttl_seconds=pol.ttl_seconds)

        namespace = pol.namespace or self.namespace
        ttl = int(pol.ttl_seconds if pol.ttl_seconds is not None else default_ttl_seconds)

        key = make_cache_key(
            cache_type=cache_type,
            namespace=namespace,
            model=model,
            messages=messages,
            options=options,
            gateway_version=self.gateway_version,
            prompt_version=self.prompt_version,
        )
        key_prefix = key.split(":")[-1][:12]

        self._ensure_l2()

        if not pol.no_cache:
            raw = self.l1.get(key)
            if raw is not None:
                created_at, value = self._decode_envelope(raw)
                if not self._is_stale(created_at, s_maxage_seconds=pol.s_maxage_seconds):
                    self.l1_hits += 1
                    return value, CacheDiagnostics(status="HIT_L1", key_prefix=key_prefix, layer="l1", ttl_seconds=ttl)

            if self.l2 is not None:
                raw = self.l2.get(key)
                if raw is not None:
                    created_at, value = self._decode_envelope(raw)
                    if not self._is_stale(created_at, s_maxage_seconds=pol.s_maxage_seconds):
                        self.l2_hits += 1
                        self.l1.set(key, raw, ttl_seconds=ttl)
                        return value, CacheDiagnostics(status="HIT_L2", key_prefix=key_prefix, layer="l2", ttl_seconds=ttl)

        def leader_compute() -> Any:
            waited = False
            lock_token: Optional[str] = None

            if self.l2 is not None:
                lock_token = self.l2.acquire_lock(key, ttl_ms=self.lock_ttl_ms)
                if lock_token is None:
                    deadline = _now_s() + (self.lock_wait_ms / 1000.0)
                    while _now_s() < deadline:
                        raw2 = self.l2.get(key)
                        if raw2 is not None:
                            created_at2, value2 = self._decode_envelope(raw2)
                            if not self._is_stale(created_at2, s_maxage_seconds=pol.s_maxage_seconds):
                                self.l2_hits += 1
                                self.l1.set(key, raw2, ttl_seconds=ttl)
                                return value2, CacheDiagnostics(
                                    status="HIT_L2",
                                    key_prefix=key_prefix,
                                    layer="l2",
                                    ttl_seconds=ttl,
                                    waited=True,
                                )
                        waited = True
                        time.sleep(0.05)

            result = compute()
            if (not pol.no_store) and result.cacheable:
                payload = self._encode_envelope(result.value)
                if self.l2 is not None:
                    self.l2.set(key, payload, ttl_seconds=ttl)
                self.l1.set(key, payload, ttl_seconds=ttl)
                self.stores += 1

            if self.l2 is not None and lock_token is not None:
                self.l2.release_lock(key, lock_token)

            return result.value, CacheDiagnostics(status="MISS", key_prefix=key_prefix, ttl_seconds=ttl, waited=waited)

        out, coalesced = self.sf.do(key, leader_compute)
        if isinstance(out, tuple) and len(out) == 2 and isinstance(out[1], CacheDiagnostics):
            value, diag = out
        else:
            value, diag = out, CacheDiagnostics(status="MISS", key_prefix=key_prefix, ttl_seconds=ttl)

        if coalesced:
            self.coalesced += 1
            diag = CacheDiagnostics(
                status="COALESCED" if diag.status == "MISS" else diag.status,
                key_prefix=diag.key_prefix,
                layer=diag.layer,
                ttl_seconds=diag.ttl_seconds,
                waited=diag.waited,
            )
        else:
            if diag.status == "MISS":
                self.misses += 1
        return value, diag

    def stats(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "namespace": self.namespace,
            "gateway_version": self.gateway_version,
            "prompt_version": self.prompt_version,
            "l2_configured": bool(self._redis_url),
            "l2_enabled_flag": bool(self._l2_enabled_flag),
            "l2_auto_enable": bool(self._l2_auto_enable),
            "l2_last_error": self._l2_last_error,
            "l2_last_checked_s": self._l2_last_checked_s,
            "calls": self.calls,
            "bypasses": self.bypasses,
            "misses": self.misses,
            "l1_hits": self.l1_hits,
            "l2_hits": self.l2_hits,
            "coalesced": self.coalesced,
            "stores": self.stores,
            "l1": {
                "size": self.l1.size(),
                "hits": self.l1.hits,
                "misses": self.l1.misses,
                "sets": self.l1.sets,
                "evictions": self.l1.evictions,
            },
            "l2": None
            if self.l2 is None
            else {
                "hits": self.l2.hits,
                "misses": self.l2.misses,
                "sets": self.l2.sets,
            },
        }

    def delete(self, key: str) -> dict[str, Any]:
        l1 = self.l1.delete(key)
        l2 = self.l2.delete(key) if self.l2 is not None else 0
        return {"l1_deleted": bool(l1), "l2_deleted": int(l2)}

    def clear_l1(self) -> None:
        self.l1.clear()

    def ping_l2(self) -> dict[str, Any]:
        self._ensure_l2()
        if self.l2 is None:
            return {"enabled": False, "configured": bool(self._redis_url), "error": self._l2_last_error}
        try:
            ok = self.l2.ping()
            return {"enabled": True, "ok": ok}
        except Exception as e:  # pragma: no cover
            return {"enabled": True, "ok": False, "error": str(e)}


_gateway_singleton: Optional[LLMCacheGateway] = None
_gateway_lock = threading.Lock()


def get_llm_cache_gateway() -> LLMCacheGateway:
    global _gateway_singleton
    if _gateway_singleton is None:
        with _gateway_lock:
            if _gateway_singleton is None:
                _gateway_singleton = LLMCacheGateway.from_settings()
    return _gateway_singleton
