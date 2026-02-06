import pytest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from app.application.use_cases import auth_login
from app.application.use_cases.auth_login import LoginInputDTO, LoginOutput, LoginUseCase
from app.application.use_cases.authenticate_user import InvalidCredentialsError
from app.core.settings import settings


@pytest.mark.asyncio
async def test_login_happy_path(monkeypatch):
    user = SimpleNamespace(id="user-1")
    auth_uc = MagicMock()
    auth_uc.execute = MagicMock(return_value=user)

    token_svc = MagicMock()
    token_svc.create_access_token.return_value = "jwt-token"

    limiter_call = AsyncMock()
    limiter = SimpleNamespace(allow_request=limiter_call)

    async def fake_run_in_threadpool(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(auth_login, "run_in_threadpool", fake_run_in_threadpool)

    uc = LoginUseCase(auth_uc=auth_uc, token_svc=token_svc, limiter=limiter)

    result = await uc.execute(
        LoginInputDTO(email="user@example.com", password="pw", client_ip="9.9.9.9")
    )

    assert isinstance(result, LoginOutput)
    assert result.access_token == "jwt-token"
    limiter_call.assert_awaited_once_with(
        key="login_req:9.9.9.9",
        limit=settings.RATE_LIMIT_LOGIN_REQ_PER_MIN,
        window_seconds=60,
    )
    auth_uc.execute.assert_called_once()
    token_svc.create_access_token.assert_called_once_with(subject="user-1")


@pytest.mark.asyncio
async def test_login_invalid_credentials(monkeypatch):
    auth_uc = MagicMock()
    auth_uc.execute = MagicMock(side_effect=InvalidCredentialsError)
    token_svc = MagicMock()
    limiter = SimpleNamespace(allow_request=AsyncMock())

    async def fake_run_in_threadpool(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(auth_login, "run_in_threadpool", fake_run_in_threadpool)

    uc = LoginUseCase(auth_uc=auth_uc, token_svc=token_svc, limiter=limiter)

    with pytest.raises(InvalidCredentialsError):
        await uc.execute(LoginInputDTO(email="x@y.com", password="pw", client_ip="3.3.3.3"))

    token_svc.create_access_token.assert_not_called()


@pytest.mark.asyncio
async def test_login_rate_limit_called(monkeypatch):
    auth_uc = MagicMock()
    auth_uc.execute = MagicMock(return_value=SimpleNamespace(id="u"))
    token_svc = MagicMock()
    token_svc.create_access_token.return_value = "t"
    limiter_call = AsyncMock()
    limiter = SimpleNamespace(allow_request=limiter_call)

    async def fake_run_in_threadpool(func, *args, **kwargs):
        return func(*args, **kwargs)

    monkeypatch.setattr(auth_login, "run_in_threadpool", fake_run_in_threadpool)

    uc = LoginUseCase(auth_uc=auth_uc, token_svc=token_svc, limiter=limiter)

    await uc.execute(LoginInputDTO(email="a@b.com", password="pw", client_ip="4.4.4.4"))

    limiter_call.assert_awaited_once()
    args, kwargs = limiter_call.await_args
    assert kwargs["key"] == "login_req:4.4.4.4"
