from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from starlette.concurrency import run_in_threadpool

from app.application.use_cases.create_user import CreateUser, CreateUserInput
from app.domain.models.user import User
from app.infrastructure.services.otp_ticket_service import OTPTicketService, TicketInvalidError


@dataclass(frozen=True)
class SignupInput:
    email: str
    password: str
    full_name: Optional[str]
    signup_ticket: str


class SignupUseCase:
    def __init__(self, otp_svc: OTPTicketService, create_user_uc: CreateUser) -> None:
        self._otp_svc = otp_svc
        self._create_user_uc = create_user_uc

    async def execute(self, data: SignupInput) -> User:
        await self._otp_svc.consume_ticket(data.email, data.signup_ticket)
        user = await run_in_threadpool(
            self._create_user_uc.execute,
            CreateUserInput(
                email=data.email,
                password=data.password,
                full_name=data.full_name,
            ),
        )
        return user


__all__ = [
    "SignupUseCase",
    "SignupInput",
    "TicketInvalidError",
]
