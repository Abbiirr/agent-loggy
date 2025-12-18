# app/services/llm_cache.py
"""
LLM response caching service for reducing redundant Ollama API calls.
Uses content-based hashing to cache identical requests.
"""

import hashlib
import json
import logging
from typing import Optional, Dict, Any, List

from app.services.cache import cache_manager

logger = logging.getLogger(__name__)

# LLM cache TTLs in seconds (extended for longer caching)
LLM_CACHE_TTLS = {
    "parameter_extraction": 7200,    # 2 hours - same query text = same params
    "trace_analysis": 14400,         # 4 hours - same log content = same analysis
    "trace_entries_analysis": 14400, # 4 hours - same entries = same analysis
    "quality_assessment": 7200,      # 2 hours - overall quality scoring
    "relevance_analysis": 14400,     # 4 hours - same content = same relevance
}


def _hash_content(content: str) -> str:
    """Create deterministic hash from content string."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:24]


def _hash_messages(messages: List[Dict], model: str) -> str:
    """Create deterministic hash from messages and model."""
    content = json.dumps({"model": model, "messages": messages}, sort_keys=True)
    return _hash_content(content)


def get_llm_cache_key(
    cache_type: str,
    messages: List[Dict],
    model: str
) -> str:
    """
    Generate a cache key for LLM requests.

    Args:
        cache_type: Type of cache (e.g., 'parameter_extraction', 'trace_analysis')
        messages: List of message dicts with 'role' and 'content'
        model: Model name used for the request

    Returns:
        Cache key string
    """
    msg_hash = _hash_messages(messages, model)
    return f"{cache_type}:{msg_hash}"


def get_cached_llm_response(
    cache_type: str,
    messages: List[Dict],
    model: str
) -> Optional[Dict[str, Any]]:
    """
    Check cache for an existing LLM response.

    Args:
        cache_type: Type of cache to check
        messages: Request messages
        model: Model name

    Returns:
        Cached response dict or None if not cached
    """
    ttl = LLM_CACHE_TTLS.get(cache_type, 7200)
    cache = cache_manager.get_cache(f"llm_{cache_type}", ttl=ttl)
    cache_key = get_llm_cache_key(cache_type, messages, model)

    cached = cache.get(cache_key)
    if cached is not None:
        logger.debug(f"LLM cache hit for {cache_type}: {cache_key[:16]}...")
        return cached

    logger.debug(f"LLM cache miss for {cache_type}: {cache_key[:16]}...")
    return None


def cache_llm_response(
    cache_type: str,
    messages: List[Dict],
    model: str,
    response: Dict[str, Any],
    ttl: Optional[int] = None
) -> None:
    """
    Store an LLM response in cache.

    Args:
        cache_type: Type of cache
        messages: Request messages
        model: Model name
        response: Response to cache
        ttl: Optional TTL override in seconds
    """
    default_ttl = LLM_CACHE_TTLS.get(cache_type, 7200)
    cache = cache_manager.get_cache(f"llm_{cache_type}", ttl=default_ttl)
    cache_key = get_llm_cache_key(cache_type, messages, model)

    cache.set(cache_key, response, ttl=ttl or default_ttl)
    logger.debug(f"LLM response cached for {cache_type}: {cache_key[:16]}... (TTL: {ttl or default_ttl}s)")


def invalidate_llm_cache(cache_type: str) -> bool:
    """
    Invalidate all entries in a specific LLM cache.

    Args:
        cache_type: Type of cache to invalidate

    Returns:
        True if cache was invalidated
    """
    return cache_manager.invalidate(f"llm_{cache_type}")


def invalidate_all_llm_caches() -> None:
    """Invalidate all LLM caches."""
    for cache_type in LLM_CACHE_TTLS.keys():
        cache_manager.invalidate(f"llm_{cache_type}")
    logger.info("All LLM caches invalidated")


def get_llm_cache_stats() -> Dict[str, int]:
    """
    Get statistics for all LLM caches.

    Returns:
        Dict mapping cache name to entry count
    """
    stats = {}
    for cache_type in LLM_CACHE_TTLS.keys():
        cache_name = f"llm_{cache_type}"
        cache = cache_manager.get_cache(cache_name)
        stats[cache_name] = cache.size()
    return stats


# Convenience functions for specific cache types

def get_cached_parameter_extraction(messages: List[Dict], model: str) -> Optional[Dict]:
    """Get cached parameter extraction response."""
    return get_cached_llm_response("parameter_extraction", messages, model)


def cache_parameter_extraction(messages: List[Dict], model: str, response: Dict) -> None:
    """Cache parameter extraction response."""
    cache_llm_response("parameter_extraction", messages, model, response)


def get_cached_trace_analysis(messages: List[Dict], model: str) -> Optional[Dict]:
    """Get cached trace analysis response."""
    return get_cached_llm_response("trace_analysis", messages, model)


def cache_trace_analysis(messages: List[Dict], model: str, response: Dict) -> None:
    """Cache trace analysis response."""
    cache_llm_response("trace_analysis", messages, model, response)


def get_cached_relevance_analysis(messages: List[Dict], model: str) -> Optional[Dict]:
    """Get cached relevance analysis response."""
    return get_cached_llm_response("relevance_analysis", messages, model)


def cache_relevance_analysis(messages: List[Dict], model: str, response: Dict) -> None:
    """Cache relevance analysis response."""
    cache_llm_response("relevance_analysis", messages, model, response)
