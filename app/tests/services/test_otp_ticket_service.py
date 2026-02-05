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
