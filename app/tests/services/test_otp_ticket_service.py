import pytest
from unittest.mock import AsyncMock

from app.core.settings import settings
from app.infrastructure.services.otp_ticket_service import OTPTicketService, OTPInvalidError


@pytest.mark.asyncio
async def test_verify_otp_issues_ticket_atomically(monkeypatch):
    svc = OTPTicketService()
    email = 'concurrent@example.com'
    otp = '123456'
    ticket_value = 'ticket-success'
    redis = AsyncMock()
    redis.eval.return_value = 1
    monkeypatch.setattr('app.infrastructure.services.otp_ticket_service.secrets.token_urlsafe', lambda n=32: ticket_value)
    monkeypatch.setattr('app.infrastructure.services.otp_ticket_service.get_redis', AsyncMock(return_value=redis))

    ticket = await svc.verify_otp_and_issue_ticket(email, otp)

    assert ticket == ticket_value
    redis.eval.assert_awaited_once_with(
        svc.ATOMIC_EXCHANGE_SCRIPT,
        2,
        svc._otp_key(email),
        svc._ticket_key(ticket_value),
        otp,
        email.lower(),
        settings.SIGNUP_TICKET_TTL_SECONDS,
    )

@pytest.mark.asyncio
async def test_verify_otp_rejects_invalid_code(monkeypatch):
    svc = OTPTicketService()
    email = 'wrong@example.com'
    otp = '000000'
    ticket_value = 'ticket-fail'
    redis = AsyncMock()
    redis.eval.return_value = 0
    monkeypatch.setattr('app.infrastructure.services.otp_ticket_service.secrets.token_urlsafe', lambda n=32: ticket_value)
    monkeypatch.setattr('app.infrastructure.services.otp_ticket_service.get_redis', AsyncMock(return_value=redis))

    with pytest.raises(OTPInvalidError):
        await svc.verify_otp_and_issue_ticket(email, otp)

    redis.eval.assert_awaited_once_with(
        svc.ATOMIC_EXCHANGE_SCRIPT,
        2,
        svc._otp_key(email),
        svc._ticket_key(ticket_value),
        otp,
        email.lower(),
        settings.SIGNUP_TICKET_TTL_SECONDS,
    )

@pytest.mark.asyncio
async def test_email_normalization_consistency(monkeypatch):
    import fakeredis.aioredis as fakeredis

    svc = OTPTicketService()
    mixed_email = "  CamelCase@Example.com  "
    normalized = "camelcase@example.com"
    fixed_otp = "654321"
    fixed_ticket = "ticket-normalized"

    fake = fakeredis.FakeRedis()

    async def fake_setex(key: str, ttl: int, value: bytes):
        await fake.setex(key, ttl, value)

    async def fake_eval(script, numkeys, *parts):
        keys = parts[:numkeys]
        argv = parts[numkeys:]
        otp_key, ticket_key = keys
        otp_val, email_val, ttl = argv
        stored = await fake.get(otp_key)
        if stored is None:
            return 0
        stored_val = stored.decode("utf-8") if isinstance(stored, bytes) else stored
        if stored_val != otp_val:
            return 0
        await fake.delete(otp_key)
        await fake.setex(ticket_key, int(ttl), email_val.encode("utf-8"))
        return 1

    monkeypatch.setattr('app.infrastructure.services.otp_ticket_service.redis_setex', fake_setex)
    monkeypatch.setattr('app.infrastructure.services.otp_ticket_service.get_redis', AsyncMock(return_value=fake))
    monkeypatch.setattr('app.infrastructure.services.otp_ticket_service.secrets.token_urlsafe', lambda n=32: fixed_ticket)
    monkeypatch.setattr(svc, 'generate_otp', lambda: fixed_otp)
    fake.eval = fake_eval

    result = await svc.issue_otp(mixed_email)
    assert result.otp == fixed_otp
    stored_otp = await fake.get(f"otp:{normalized}")
    assert stored_otp is not None

    ticket = await svc.verify_otp_and_issue_ticket("CamelCase@Example.com", fixed_otp)
    assert ticket == fixed_ticket

    stored_ticket_email = await fake.get(f"signup_ticket:{fixed_ticket}")
    assert stored_ticket_email.decode("utf-8") == normalized
