import pytest
from fastapi.testclient import TestClient
from typing import Generator
import fakeredis.aioredis as fakeredis

from app.main import create_app
from app.api.deps.vaults import get_vault_repo
from app.api.deps.auth import get_email_service
from app.core.settings import settings
from app.infrastructure.db.repositories.in_memory_vault_repository import InMemoryVaultRepository
from app.tests.fakes.email_service import CaptureEmailService


@pytest.fixture
def app():
    previous = settings.DEV_AUTH_BYPASS
    settings.DEV_AUTH_BYPASS = True
    app = create_app()
    try:
        yield app
    finally:
        settings.DEV_AUTH_BYPASS = previous


@pytest.fixture(autouse=True)
async def _fake_redis(monkeypatch):
    import app.infrastructure.cache.redis_client as rc

    fake = fakeredis.FakeRedis()

    async def _get_redis():
        return fake

    async def _shutdown():
        await fake.aclose()
        rc._redis = None

    async def _eval(script, numkeys, *parts):
        keys = parts[:numkeys]
        argv = parts[numkeys:]

        # OTP verify script: KEYS[0]=otp_key, KEYS[1]=ticket_key, ARGV=[otp, email, ttl]
        if numkeys == 2 and len(argv) == 3:
            otp_key, ticket_key = keys
            otp, email, ttl = argv
            stored = await fake.get(otp_key)
            if stored is None:
                return 0
            stored_val = stored.decode("utf-8") if isinstance(stored, bytes) else stored
            if stored_val != otp:
                return 0
            await fake.delete(otp_key)
            value_to_set = email if isinstance(stored, str) else email.encode("utf-8")
            await fake.setex(ticket_key, int(ttl), value_to_set)
            return 1

        # Ticket consume script: KEYS[0]=ticket_key, ARGV=[expected]
        if numkeys == 1 and len(argv) == 1:
            ticket_key = keys[0]
            expected = argv[0]
            current = await fake.get(ticket_key)
            if current is None:
                return None
            current_val = current.decode("utf-8") if isinstance(current, bytes) else current
            if current_val != expected:
                return 0
            await fake.delete(ticket_key)
            return current

        return 0

    fake.eval = _eval

    rc._redis = fake
    monkeypatch.setattr(rc, "get_redis", _get_redis)
    monkeypatch.setattr(rc, "redis_shutdown", _shutdown)
    yield
    await fake.aclose()
    rc._redis = None


@pytest.fixture
def vault_repo(app) -> Generator[InMemoryVaultRepository, None, None]:
    repo = InMemoryVaultRepository()
    app.dependency_overrides[get_vault_repo] = lambda: repo
    yield repo
    app.dependency_overrides.pop(get_vault_repo, None)


@pytest.fixture
def capture_email_service(app) -> Generator[CaptureEmailService, None, None]:
    svc = CaptureEmailService()
    app.dependency_overrides[get_email_service] = lambda: svc
    yield svc
    app.dependency_overrides.pop(get_email_service, None)


@pytest.fixture
def client(app, vault_repo) -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c
