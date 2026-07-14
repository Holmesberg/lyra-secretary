"""Small in-memory cache and perf logging for bias-factor lookup."""

from __future__ import annotations

import copy
import logging
from time import monotonic
from typing import Any, Optional


BiasLookupCacheKey = tuple[int, str, str, int, int, str]

_BIAS_LOOKUP_CACHE_TTL_SECONDS = 30.0
_bias_lookup_cache: dict[BiasLookupCacheKey, tuple[float, dict[str, Any]]] = {}
_bias_lookup_perf_logger = logging.getLogger("lyraos.perf.bias_lookup")


def cached_bias_lookup_response(
    key: BiasLookupCacheKey,
) -> Optional[dict[str, Any]]:
    cached = _bias_lookup_cache.get(key)
    if cached is None:
        return None
    stored_at, payload = cached
    if monotonic() - stored_at > _BIAS_LOOKUP_CACHE_TTL_SECONDS:
        _bias_lookup_cache.pop(key, None)
        return None
    return copy.deepcopy(payload)


def store_bias_lookup_response(
    key: BiasLookupCacheKey,
    payload: dict[str, Any],
) -> dict[str, Any]:
    _bias_lookup_cache[key] = (monotonic(), copy.deepcopy(payload))
    return payload


def log_slow_bias_lookup(
    *,
    user_id: int,
    category: str,
    tod: str,
    planned_minutes: int,
    tasks_ms: float,
    blend_ms: float,
    exposure_ms: float,
    total_ms: float,
    source: Optional[str],
    sessions: Optional[int],
) -> None:
    if total_ms < 250:
        return
    _bias_lookup_perf_logger.info(
        (
            "user=%s category=%s tod=%s planned=%s tasks_ms=%.0f "
            "blend_ms=%.0f exposure_ms=%.0f total_ms=%.0f source=%s sessions=%s"
        ),
        user_id,
        category,
        tod,
        planned_minutes,
        tasks_ms,
        blend_ms,
        exposure_ms,
        total_ms,
        source,
        sessions,
    )
