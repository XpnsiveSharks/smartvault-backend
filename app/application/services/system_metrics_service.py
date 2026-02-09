from __future__ import annotations

from datetime import datetime, timezone
from time import monotonic
from typing import Any, Dict, Optional

from app.application.ports.system_metrics import (
    SystemMetricsQueryService,
    OverviewSnapshot,
    PerformanceSnapshot,
    PerformancePoint,
    ErrorSummary,
)

# Explicitly bounded windows to keep queries small and predictable.
ALLOWED_PERIODS = {
    "15m": 15 * 60,
    "1h": 60 * 60,
    "24h": 24 * 60 * 60,
}

ALLOWED_GRANULARITIES = {
    "1m": 60,
    "5m": 5 * 60,
    "15m": 15 * 60,
    "1h": 60 * 60,
}


class InvalidWindow(ValueError):
    pass


class SystemMetricsService(SystemMetricsQueryService):
    def __init__(
        self,
        adapter,
        ttl_seconds: int | None = None,
        overview_ttl: int = 10,
        performance_ttl: int = 30,
        errors_ttl: int = 2,
    ):
        self._adapter = adapter
        # Preserve backward compatibility: ttl_seconds applies to all caches when provided.
        if ttl_seconds is not None:
            overview_ttl = performance_ttl = errors_ttl = max(ttl_seconds, 0)
        self._ttl_overview = max(overview_ttl, 0)
        self._ttl_performance = max(performance_ttl, 0)
        self._ttl_errors = max(errors_ttl, 0)
        self._cache: Dict[str, tuple[float, Any]] = {}

    async def get_overview(self) -> OverviewSnapshot:
        cached = self._get_cached("overview")
        if cached:
            return cached
        result = await self._adapter.fetch_overview()
        self._set_cache("overview", result, ttl=self._ttl_overview)
        return result

    async def get_performance(self, period: str, granularity: str) -> PerformanceSnapshot:
        period = period.lower()
        granularity = granularity.lower()
        self._validate_window(period, granularity)

        key = f"perf:{period}:{granularity}"
        cached = self._get_cached(key)
        if cached:
            return cached
        result = await self._adapter.fetch_performance(period=period, granularity=granularity)
        self._set_cache(key, result, ttl=self._ttl_performance)
        return result

    async def get_errors(self, limit: int) -> ErrorSummary:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        key = f"errors:{limit}"
        cached = self._get_cached(key)
        if cached:
            return cached
        result = await self._adapter.fetch_errors(limit=limit)
        self._set_cache(key, result, ttl=self._ttl_errors)
        return result

    # ---- simple in-memory cache helpers ----
    def _get_cached(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if not entry:
            return None
        expiry, value = entry
        if monotonic() > expiry:
            self._cache.pop(key, None)
            return None
        return value

    def _set_cache(self, key: str, value: Any, ttl: int) -> None:
        if ttl <= 0:
            return
        self._cache[key] = (monotonic() + ttl, value)

    def _validate_window(self, period: str, granularity: str) -> None:
        if period not in ALLOWED_PERIODS:
            allowed = ", ".join(sorted(ALLOWED_PERIODS))
            raise InvalidWindow(f"period must be one of: {allowed}")
        if granularity not in ALLOWED_GRANULARITIES:
            allowed = ", ".join(sorted(ALLOWED_GRANULARITIES))
            raise InvalidWindow(f"granularity must be one of: {allowed}")
        if ALLOWED_GRANULARITIES[granularity] > ALLOWED_PERIODS[period]:
            raise InvalidWindow("granularity must not exceed period")


# ---------- DTO helpers used by adapter implementations ----------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_point(lat_db: float | None, lat_redis: float | None) -> PerformancePoint:
    return PerformancePoint(timestamp=now_iso(), db_latency_ms=lat_db, redis_latency_ms=lat_redis)
