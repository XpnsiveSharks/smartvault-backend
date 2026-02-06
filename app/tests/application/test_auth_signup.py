import pytest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.application.use_cases import auth_signup
from app.application.use_cases.auth_signup import SignupInput, SignupUseCase, TicketInvalidError
from app.domain.models.user import User


@pytest.mark.asyncio
async def test_signup_happy_path(monkeypatch):
    otp_service = SimpleNamespace(consume_ticket=AsyncMock())
    created_user = User(
        id="u1",
        email="user@example.com",
        password_hash="hash",
        full_name="User",
        created_at=datetime.now(timezone.utc),
    )
    create_user_uc = MagicMock()
    create_user_uc.execute = MagicMock(return_value=created_user)

    async def fake_run_in_threadpool(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(auth_signup, "run_in_threadpool", fake_run_in_threadpool)

    uc = SignupUseCase(otp_svc=otp_service, create_user_uc=create_user_uc)

    result = await uc.execute(
        SignupInput(
            email="user@example.com",
            password="passwordpassword",
            full_name="User",
            signup_ticket="ticket",
        )
    )

    otp_service.consume_ticket.assert_awaited_once_with("user@example.com", "ticket")
    create_user_uc.execute.assert_called_once()
    assert result is created_user


@pytest.mark.asyncio
async def test_signup_invalid_ticket(monkeypatch):
    consume = AsyncMock(side_effect=TicketInvalidError("bad ticket"))
    otp_service = SimpleNamespace(consume_ticket=consume)
    create_user_uc = MagicMock()
    create_user_uc.execute = MagicMock(return_value=None)

    async def fake_run_in_threadpool(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(auth_signup, "run_in_threadpool", fake_run_in_threadpool)

    uc = SignupUseCase(otp_svc=otp_service, create_user_uc=create_user_uc)

    with pytest.raises(TicketInvalidError):
        await uc.execute(
            SignupInput(
                email="user@example.com",
                password="passwordpassword",
                full_name=None,
                signup_ticket="ticket",
            )
        )

    create_user_uc.execute.assert_not_called()
