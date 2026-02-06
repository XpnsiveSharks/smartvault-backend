import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from app.application.use_cases.auth_verify_otp import (
    OTPInvalidError,
    VerifyOTPInput,
    VerifyOTPUseCase,
)


@pytest.mark.asyncio
async def test_verify_otp_happy_path():
    otp_service = SimpleNamespace(
        verify_otp_and_issue_ticket=AsyncMock(return_value="ticket-123")
    )
    uc = VerifyOTPUseCase(otp_svc=otp_service)

    result = await uc.execute(VerifyOTPInput(email="user@example.com", otp="123456"))

    assert result.signup_ticket == "ticket-123"
    otp_service.verify_otp_and_issue_ticket.assert_awaited_once_with(
        "user@example.com", "123456"
    )


@pytest.mark.asyncio
async def test_verify_otp_invalid_bubbles():
    otp_service = SimpleNamespace(
        verify_otp_and_issue_ticket=AsyncMock(side_effect=OTPInvalidError("bad"))
    )
    uc = VerifyOTPUseCase(otp_svc=otp_service)

    with pytest.raises(OTPInvalidError):
        await uc.execute(VerifyOTPInput(email="user@example.com", otp="000000"))

    otp_service.verify_otp_and_issue_ticket.assert_awaited_once()
