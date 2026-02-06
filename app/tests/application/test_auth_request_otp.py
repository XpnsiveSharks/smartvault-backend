import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, ANY

from app.application.use_cases.auth_request_otp import RequestOTPInput, RequestOTPUseCase
from app.infrastructure.security.rate_limiter import RateLimitExceeded


@pytest.mark.asyncio
async def test_request_otp_happy_path():
    otp_service = SimpleNamespace(issue_otp=AsyncMock(return_value=SimpleNamespace(otp="123456")))
    email_service = SimpleNamespace(send_otp=AsyncMock())
    allow_request = AsyncMock()
    limiter = SimpleNamespace(allow_request=allow_request)

    uc = RequestOTPUseCase(
        otp_svc=otp_service,
        email_svc=email_service,
        limiter=limiter,
    )

    await uc.execute(RequestOTPInput(email="user@example.com", client_ip="1.1.1.1"))

    assert allow_request.await_count == 2
    allow_request.assert_any_await(key="otp_req:1.1.1.1", limit=ANY, window_seconds=60)
    allow_request.assert_any_await(key="otp_req:email:user@example.com", limit=3, window_seconds=900)
    otp_service.issue_otp.assert_awaited_once_with("user@example.com")
    email_service.send_otp.assert_awaited_once_with("user@example.com", "123456")


@pytest.mark.asyncio
async def test_request_otp_rate_limited():
    otp_service = SimpleNamespace(issue_otp=AsyncMock())
    email_service = SimpleNamespace(send_otp=AsyncMock())
    allow_request = AsyncMock(side_effect=RateLimitExceeded())
    limiter = SimpleNamespace(allow_request=allow_request)

    uc = RequestOTPUseCase(
        otp_svc=otp_service,
        email_svc=email_service,
        limiter=limiter,
    )

    with pytest.raises(RateLimitExceeded):
        await uc.execute(RequestOTPInput(email="user@example.com", client_ip="2.2.2.2"))

    otp_service.issue_otp.assert_not_awaited()
    email_service.send_otp.assert_not_awaited()
