from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence


@dataclass
class OverviewSnapshot:
    status: str
    db_connected: bool
    redis_connected: bool
    uptime_seconds: int | None = None
    version: str | None = None


@dataclass
class PerformancePoint:
    timestamp: str
    db_latency_ms: float | None
    redis_latency_ms: float | None


@dataclass
class PerformanceSnapshot:
    period: str
    granularity: str
    points: Sequence[PerformancePoint]


@dataclass
class ErrorItem:
    message: str
    count: int


@dataclass
class ErrorSummary:
    total: int
    items: Sequence[ErrorItem]


class SystemMetricsQueryService(Protocol):
    async def get_overview(self) -> OverviewSnapshot: ...

    async def get_performance(self, period: str, granularity: str) -> PerformanceSnapshot: ...

    async def get_errors(self, limit: int) -> ErrorSummary: ...

