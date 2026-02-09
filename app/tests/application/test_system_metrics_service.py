import pytest

from app.application.services.system_metrics_service import SystemMetricsService, InvalidWindow
from app.application.ports.system_metrics import OverviewSnapshot, PerformanceSnapshot, ErrorSummary


class _Adapter:
    def __init__(self):
        self.called = {}

    async def fetch_overview(self):
        self.called["overview"] = self.called.get("overview", 0) + 1
        return OverviewSnapshot(status="healthy", db_connected=True, redis_connected=True)

    async def fetch_performance(self, period: str, granularity: str):
        perf = self.called.get("performance", [])
        perf.append((period, granularity))
        self.called["performance"] = perf
        return PerformanceSnapshot(period=period, granularity=granularity, points=[])

    async def fetch_errors(self, limit: int):
        errors = self.called.get("errors", [])
        errors.append(limit)
        self.called["errors"] = errors
        return ErrorSummary(total=0, items=[])


@pytest.mark.asyncio
async def test_overview_pass_through():
    adapter = _Adapter()
    svc = SystemMetricsService(adapter)
    res = await svc.get_overview()
    assert res.status == "healthy"
    assert adapter.called["overview"] == 1


@pytest.mark.asyncio
async def test_performance_validates_window():
    svc = SystemMetricsService(_Adapter())
    with pytest.raises(InvalidWindow):
        await svc.get_performance("5x", "1m")
    with pytest.raises(InvalidWindow):
        await svc.get_performance("1h", "1x")
    with pytest.raises(InvalidWindow):
        await svc.get_performance("15m", "1h")  # granularity cannot exceed period


@pytest.mark.asyncio
async def test_errors_limit_bounds():
    svc = SystemMetricsService(_Adapter())
    with pytest.raises(ValueError):
        await svc.get_errors(0)
    with pytest.raises(ValueError):
        await svc.get_errors(101)

    res = await svc.get_errors(10)
    assert res.total == 0
    assert svc._cache  # errors cache populated by default


@pytest.mark.asyncio
async def test_caches_overview():
    adapter = _Adapter()
    svc = SystemMetricsService(adapter, ttl_seconds=60)
    await svc.get_overview()
    await svc.get_overview()
    assert adapter.called["overview"] == 1


@pytest.mark.asyncio
async def test_errors_cache_can_be_disabled():
    adapter = _Adapter()
    svc = SystemMetricsService(adapter, errors_ttl=0)
    await svc.get_errors(5)
    await svc.get_errors(5)
    # No caching when ttl <= 0
    assert adapter.called["errors"] == [5, 5]
