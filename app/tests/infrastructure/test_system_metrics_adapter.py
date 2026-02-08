import asyncio
import types

import pytest

from app.infrastructure.services.system_metrics_adapter import SystemMetricsAdapter


class _FakeEngine:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail

    def connect(self):
        if self.should_fail:
            raise RuntimeError("db down")
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, *_args, **_kwargs):
        return types.SimpleNamespace(scalar=lambda: 1)


class _FakeRedis:
    def __init__(self, should_fail=False):
        self.should_fail = should_fail

    async def ping(self):
        if self.should_fail:
            raise RuntimeError("redis down")
        return True


@pytest.mark.asyncio
async def test_overview_degrades_on_fail(monkeypatch):
    adapter = SystemMetricsAdapter()

    monkeypatch.setattr("app.infrastructure.services.system_metrics_adapter._get_engine", lambda: _FakeEngine(should_fail=True))

    async def _fake_redis():
        return _FakeRedis(should_fail=True)

    monkeypatch.setattr("app.infrastructure.services.system_metrics_adapter.get_redis", _fake_redis)

    result = await adapter.fetch_overview()
    assert result.status == "degraded"
    assert result.db_connected is False
    assert result.redis_connected is False


@pytest.mark.asyncio
async def test_performance_returns_point(monkeypatch):
    adapter = SystemMetricsAdapter()

    monkeypatch.setattr("app.infrastructure.services.system_metrics_adapter._get_engine", lambda: _FakeEngine())

    async def _fake_redis_ok():
        return _FakeRedis()

    monkeypatch.setattr("app.infrastructure.services.system_metrics_adapter.get_redis", _fake_redis_ok)

    result = await adapter.fetch_performance("1h", "5m")
    assert result.points
    point = result.points[0]
    assert point.db_latency_ms is not None
    assert point.redis_latency_ms is not None
