import hashlib

import pytest

from app.api.deps.internal import get_admin_rate_limiter, get_audit_logger
from app.core.settings import settings
from app.infrastructure.security.rate_limiter import RateLimitExceeded


VALID_ADMIN_TOKEN = "super-secret-admin"
VALID_ADMIN_HASH = hashlib.sha256(VALID_ADMIN_TOKEN.encode("utf-8")).hexdigest()


class _StubRateLimiter:
    def __init__(self, limit: int):
        self.limit = limit
        self.count = 0

    async def allow_request(self, *args, **kwargs):
        self.count += 1
        if self.count > self.limit:
            raise RateLimitExceeded()


class _CaptureAuditLogger:
    def __init__(self):
        self.records = []

    def log(self, record):
        self.records.append(record)


@pytest.fixture(autouse=True)
def _configure_admin_tokens():
    prev_hash = settings.ADMIN_SHARED_TOKEN_HASH
    prev_secret = settings.ADMIN_JWT_SECRET
    prev_id = settings.ADMIN_TOKEN_ID
    settings.ADMIN_SHARED_TOKEN_HASH = VALID_ADMIN_HASH
    settings.ADMIN_JWT_SECRET = None
    settings.ADMIN_TOKEN_ID = "admin-shared-test"
    yield
    settings.ADMIN_SHARED_TOKEN_HASH = prev_hash
    settings.ADMIN_JWT_SECRET = prev_secret
    settings.ADMIN_TOKEN_ID = prev_id


@pytest.fixture(autouse=True)
def _default_admin_rate_limiter(app):
    limiter = _StubRateLimiter(limit=100)
    app.dependency_overrides[get_admin_rate_limiter] = lambda: limiter
    yield limiter
    app.dependency_overrides.pop(get_admin_rate_limiter, None)


@pytest.fixture
def capture_audit_logger(app):
    logger = _CaptureAuditLogger()
    app.dependency_overrides[get_audit_logger] = lambda: logger
    yield logger
    app.dependency_overrides.pop(get_audit_logger, None)


@pytest.fixture
def stub_rate_limiter(app):
    limiter = _StubRateLimiter(limit=1)
    app.dependency_overrides[get_admin_rate_limiter] = lambda: limiter
    yield limiter
    app.dependency_overrides.pop(get_admin_rate_limiter, None)


def test_admin_requires_credentials(client):
    response = client.get("/api/internal/admin/system/overview")
    assert response.status_code == 401


def test_admin_allows_valid_shared_token_and_audits(client, capture_audit_logger):
    response = client.get(
        "/api/internal/admin/system/overview?foo=bar",
        headers={"X-Admin-Token": VALID_ADMIN_TOKEN},
    )
    assert response.status_code == 200
    assert capture_audit_logger.records, "Audit log should be emitted"
    record = capture_audit_logger.records[-1]
    assert record.principal == "admin-shared-test"
    assert record.headers.get("x-admin-token") == "[redacted]"
    assert record.query_params.get("foo") == "bar"


def test_admin_rejects_invalid_token(client, capture_audit_logger):
    response = client.get(
        "/api/internal/admin/system/overview",
        headers={"X-Admin-Token": "wrong-token"},
    )
    assert response.status_code == 401
    assert capture_audit_logger.records, "Audit log should still be emitted on failure"
    record = capture_audit_logger.records[-1]
    assert record.principal == "anonymous"
    assert record.status == 401


def test_admin_rate_limiting(client, stub_rate_limiter):
    ok = client.get(
        "/api/internal/admin/system/overview",
        headers={"X-Admin-Token": VALID_ADMIN_TOKEN},
    )
    assert ok.status_code == 200
    limited = client.get(
        "/api/internal/admin/system/overview",
        headers={"X-Admin-Token": VALID_ADMIN_TOKEN},
    )
    assert limited.status_code == 429
