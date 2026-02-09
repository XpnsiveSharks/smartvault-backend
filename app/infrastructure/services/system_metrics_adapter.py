from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from time import monotonic

from sqlalchemy import text

from app.infrastructure.cache.redis_client import get_redis
from app.infrastructure.db.session import _get_engine
from app.application.ports.system_metrics import (
    OverviewSnapshot,
    PerformanceSnapshot,
    PerformancePoint,
    ErrorSummary,
)
from app.application.services.system_metrics_service import build_point


log = logging.getLogger(__name__)


@dataclass
class SystemMetricsAdapter:
    db_timeout: float = 1.0
    redis_timeout: float = 0.5
    cache_ttl: int = 5

    async def fetch_overview(self) -> OverviewSnapshot:
        db_ok = await self._ping_db()
        redis_ok = await self._ping_redis()
        status = "healthy" if db_ok and redis_ok else "degraded"
        return OverviewSnapshot(status=status, db_connected=db_ok, redis_connected=redis_ok)

    async def fetch_performance(self, period: str, granularity: str) -> PerformanceSnapshot:
        # For now, produce lightweight current-point metrics; extend later with real aggregates.
        db_latency = await self._measure_db_latency()
        redis_latency = await self._measure_redis_latency()
        points: Sequence[PerformancePoint] = [build_point(db_latency, redis_latency)]
        return PerformanceSnapshot(period=period, granularity=granularity, points=points)

    async def fetch_errors(self, limit: int) -> ErrorSummary:
        try:
            return await self._collect_errors(limit)
        except Exception:  # noqa: BLE001
            log.warning("Error summary unavailable", exc_info=True)
            return ErrorSummary(total=0, items=[])

    # -------- internals --------
    async def _ping_db(self) -> bool:
        try:
            await asyncio.wait_for(asyncio.to_thread(self._execute_db_ping), timeout=self.db_timeout)
            return True
        except Exception:  # noqa: BLE001
            log.warning("DB ping failed", exc_info=True)
            return False

    async def _ping_redis(self) -> bool:
        try:
            redis = await get_redis()
            async with asyncio.timeout(self.redis_timeout):
                await redis.ping()
            return True
        except Exception:  # noqa: BLE001
            log.warning("Redis ping failed", exc_info=True)
            return False

    async def _measure_db_latency(self) -> float | None:
        try:
            start = monotonic()
            await asyncio.wait_for(asyncio.to_thread(self._execute_db_ping), timeout=self.db_timeout)
            return (monotonic() - start) * 1000
        except Exception:  # noqa: BLE001
            log.warning("DB latency probe failed", exc_info=True)
            return None

    async def _measure_redis_latency(self) -> float | None:
        try:
            redis = await get_redis()
            start = monotonic()
            async with asyncio.timeout(self.redis_timeout):
                await redis.ping()
            return (monotonic() - start) * 1000
        except Exception:  # noqa: BLE001
            log.warning("Redis latency probe failed", exc_info=True)
            return None

    async def _collect_errors(self, _limit: int) -> ErrorSummary:
        # Placeholder: return bounded empty summary; ready to plug real source later.
        return ErrorSummary(total=0, items=[])

    @staticmethod
    def _execute_db_ping() -> None:
        engine = _get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
