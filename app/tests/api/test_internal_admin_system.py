import hashlib

import pytest

from app.api.deps.internal import get_system_metrics_service, get_admin_rate_limiter
from app.core.settings import settings
from app.application.services.system_metrics_service import SystemMetricsService
from app.application.ports.system_metrics import OverviewSnapshot, PerformanceSnapshot, ErrorSummary


VALID_ADMIN_TOKEN = "admin-token"
VALID_ADMIN_HASH = hashlib.sha256(VALID_ADMIN_TOKEN.encode()).hexdigest()


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
        return ErrorSummary(total=0, items=[])


class _NoopLimiter:
    async def allow_request(self, *args, **kwargs):
        return None


@pytest.fixture(autouse=True)
def _configure_admin_shared_token():
    prev_hash = settings.ADMIN_SHARED_TOKEN_HASH
    prev_secret = settings.ADMIN_JWT_SECRET
    settings.ADMIN_SHARED_TOKEN_HASH = VALID_ADMIN_HASH
    settings.ADMIN_JWT_SECRET = None
    yield
    settings.ADMIN_SHARED_TOKEN_HASH = prev_hash
    settings.ADMIN_JWT_SECRET = prev_secret


@pytest.fixture
def fake_metrics_service(app):
    adapter = _Adapter()
    svc = SystemMetricsService(adapter, ttl_seconds=0)
    app.dependency_overrides[get_system_metrics_service] = lambda: svc
    yield adapter
    app.dependency_overrides.pop(get_system_metrics_service, None)


@pytest.fixture(autouse=True)
def no_rate_limit(app):
    limiter = _NoopLimiter()
    app.dependency_overrides[get_admin_rate_limiter] = lambda: limiter
    yield limiter
    app.dependency_overrides.pop(get_admin_rate_limiter, None)


def _auth_headers():
    return {"X-Admin-Token": VALID_ADMIN_TOKEN}


def test_overview_ok(client, fake_metrics_service):
    resp = client.get("/api/internal/admin/system/overview", headers=_auth_headers())
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
    assert fake_metrics_service.overview_calls == 1


def test_performance_validates(client, fake_metrics_service):
    bad = client.get(
        "/api/internal/admin/system/performance",
        params={"period": "5x", "granularity": "1m"},
        headers=_auth_headers(),
    )
    assert bad.status_code == 422

    ok = client.get(
        "/api/internal/admin/system/performance",
        params={"period": "1h", "granularity": "5m"},
        headers=_auth_headers(),
    )
    assert ok.status_code == 200
    assert fake_metrics_service.performance_calls[-1] == ("1h", "5m")


def test_errors_limits(client, fake_metrics_service):
    bad = client.get(
        "/api/internal/admin/system/errors",
        params={"limit": 0},
        headers=_auth_headers(),
    )
    assert bad.status_code == 422

    ok = client.get(
        "/api/internal/admin/system/errors",
        params={"limit": 5},
        headers=_auth_headers(),
    )
    assert ok.status_code == 200
    assert fake_metrics_service.errors_calls[-1] == 5
