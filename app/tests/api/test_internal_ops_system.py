import hashlib

import pytest

from app.api.deps.internal import get_system_metrics_service, get_ops_rate_limiter
from app.application.services.system_metrics_service import SystemMetricsService
from app.application.ports.system_metrics import OverviewSnapshot, PerformanceSnapshot, ErrorSummary
from app.core.settings import settings


VALID_OPS_TOKEN = "ops-token"
VALID_OPS_HASH = hashlib.sha256(VALID_OPS_TOKEN.encode()).hexdigest()


class _Adapter:
    def __init__(self):
        self.overview_calls = 0
        self.performance_calls = []
        self.errors_calls = []

    async def fetch_overview(self):
        self.overview_calls += 1
        return OverviewSnapshot(status="healthy", db_connected=True, redis_connected=True)

    async def fetch_performance(self, period: str, granularity: str):
        self.performance_calls.append((period, granularity))
        return PerformanceSnapshot(period=period, granularity=granularity, points=[])

    async def fetch_errors(self, limit: int):
        self.errors_calls.append(limit)
        return ErrorSummary(total=limit, items=[])


class _ErroringAdapter(_Adapter):
    async def fetch_overview(self):
        raise RuntimeError("boom")


class _NoopLimiter:
    async def allow_request(self, *args, **kwargs):
        return None


@pytest.fixture(autouse=True)
def _configure_ops_shared_token():
    prev_hash = settings.INTERNAL_OPS_TOKEN_HASH
    settings.INTERNAL_OPS_TOKEN_HASH = VALID_OPS_HASH
    yield
    settings.INTERNAL_OPS_TOKEN_HASH = prev_hash


@pytest.fixture(autouse=True)
def no_rate_limit(app):
    limiter = _NoopLimiter()
    app.dependency_overrides[get_ops_rate_limiter] = lambda: limiter
    yield limiter
    app.dependency_overrides.pop(get_ops_rate_limiter, None)


@pytest.fixture
def fake_metrics_service(app):
    adapter = _Adapter()
    svc = SystemMetricsService(adapter, ttl_seconds=0)
    app.dependency_overrides[get_system_metrics_service] = lambda: svc
    yield adapter
    app.dependency_overrides.pop(get_system_metrics_service, None)


@pytest.fixture
def cached_metrics_service(app):
    adapter = _Adapter()
    svc = SystemMetricsService(adapter)
    app.dependency_overrides[get_system_metrics_service] = lambda: svc
    yield adapter
    app.dependency_overrides.pop(get_system_metrics_service, None)


def _auth_headers():
    return {"X-Ops-Token": VALID_OPS_TOKEN}


def test_overview_requires_token(client):
    resp = client.get("/api/internal/ops/system/overview")
    assert resp.status_code == 401


def test_overview_ok(client, fake_metrics_service):
    resp = client.get("/api/internal/ops/system/overview", headers=_auth_headers())
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
    assert fake_metrics_service.overview_calls == 1


def test_performance_validates(client, fake_metrics_service):
    bad = client.get(
        "/api/internal/ops/system/performance",
        params={"period": "5x", "granularity": "1m"},
        headers=_auth_headers(),
    )
    assert bad.status_code == 422

    ok = client.get(
        "/api/internal/ops/system/performance",
        params={"period": "1h", "granularity": "5m"},
        headers=_auth_headers(),
    )
    assert ok.status_code == 200
    assert fake_metrics_service.performance_calls[-1] == ("1h", "5m")


def test_errors_limits_and_cache_isolated(client, cached_metrics_service):
    first = client.get(
        "/api/internal/ops/system/errors",
        params={"limit": 3},
        headers=_auth_headers(),
    )
    second = client.get(
        "/api/internal/ops/system/errors",
        params={"limit": 1},
        headers=_auth_headers(),
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["total"] == 3
    assert second.json()["total"] == 1
    assert cached_metrics_service.errors_calls == [3, 1]


def test_overview_degraded_returns_503(client, app):
    adapter = _ErroringAdapter()
    svc = SystemMetricsService(adapter, ttl_seconds=0)
    app.dependency_overrides[get_system_metrics_service] = lambda: svc

    try:
        resp = client.get("/api/internal/ops/system/overview", headers=_auth_headers())
        assert resp.status_code == 503
    finally:
        app.dependency_overrides.pop(get_system_metrics_service, None)
