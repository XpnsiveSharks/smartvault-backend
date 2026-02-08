from __future__ import annotations

import re
from datetime import datetime, timezone
from time import monotonic
from typing import Sequence, Any, Dict, Tuple, Optional

from app.application.ports.system_metrics import (
    SystemMetricsQueryService,
    OverviewSnapshot,
    PerformanceSnapshot,
    PerformancePoint,
    ErrorSummary,
    ErrorItem,
)

VALID_PERIOD = re.compile(r"^(\d+)(m|h|d)$", re.IGNORECASE)
VALID_GRANULARITY = re.compile(r"^(\d+)(s|m|h)$", re.IGNORECASE)


class InvalidWindow(ValueError):
    pass


class SystemMetricsService(SystemMetricsQueryService):
    def __init__(self, adapter, ttl_seconds: int = 5):
        self._adapter = adapter
        self._ttl = ttl_seconds
        self._cache: Dict[str, Tuple[float, Any]] = {}

    async def get_overview(self) -> OverviewSnapshot:
        cached = self._get_cached("overview")
        if cached:
            return cached
        result = await self._adapter.fetch_overview()
        self._set_cache("overview", result)
        return result

    async def get_performance(self, period: str, granularity: str) -> PerformanceSnapshot:
        if not VALID_PERIOD.match(period):
            raise InvalidWindow("Invalid period format; use number + m/h/d")
        if not VALID_GRANULARITY.match(granularity):
            raise InvalidWindow("Invalid granularity format; use number + s/m/h")
        key = f"perf:{period.lower()}:{granularity.lower()}"
        cached = self._get_cached(key)
        if cached:
            return cached
        result = await self._adapter.fetch_performance(period=period.lower(), granularity=granularity.lower())
        self._set_cache(key, result)
        return result

    async def get_errors(self, limit: int) -> ErrorSummary:
        if limit < 1 or limit > 100:
            raise ValueError("limit must be between 1 and 100")
        key = f"errors:{limit}"
        cached = self._get_cached(key)
        if cached:
            return cached
        result = await self._adapter.fetch_errors(limit=limit)
        self._set_cache(key, result)
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

    def _set_cache(self, key: str, value: Any) -> None:
        self._cache[key] = (monotonic() + self._ttl, value)


# ---------- DTO helpers used by adapter implementations ----------

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_point(lat_db: float | None, lat_redis: float | None) -> PerformancePoint:
    return PerformancePoint(timestamp=now_iso(), db_latency_ms=lat_db, redis_latency_ms=lat_redis)
