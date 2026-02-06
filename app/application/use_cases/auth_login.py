from __future__ import annotations

from dataclasses import dataclass

from starlette.concurrency import run_in_threadpool

from app.application.services.token_service import TokenService
from app.application.use_cases.authenticate_user import AuthenticateUser, LoginInput
from app.core.settings import settings
from app.infrastructure.security.rate_limiter import RateLimiter


@dataclass(frozen=True)
class LoginInputDTO:
    email: str
    password: str
    client_ip: str


@dataclass(frozen=True)
class LoginOutput:
    access_token: str
    token_type: str = "bearer"


class LoginUseCase:
    def __init__(
        self,
        auth_uc: AuthenticateUser,
        token_svc: TokenService,
        limiter: RateLimiter,
    ) -> None:
        self._auth_uc = auth_uc
        self._token_svc = token_svc
        self._limiter = limiter

    async def execute(self, data: LoginInputDTO) -> LoginOutput:
        await self._limiter.allow_request(
            key=f"login_req:{data.client_ip}",
            limit=settings.RATE_LIMIT_LOGIN_REQ_PER_MIN,
            window_seconds=60,
        )

        user = await run_in_threadpool(
            self._auth_uc.execute,
            LoginInput(email=data.email, password=data.password),
        )

        token = self._token_svc.create_access_token(subject=user.id)
        return LoginOutput(access_token=token)
