from __future__ import annotations

from dataclasses import dataclass

from app.infrastructure.services.otp_ticket_service import OTPInvalidError, OTPTicketService


@dataclass(frozen=True)
class VerifyOTPInput:
    email: str
    otp: str


@dataclass(frozen=True)
class VerifyOTPOutput:
    signup_ticket: str


class VerifyOTPUseCase:
    def __init__(self, otp_svc: OTPTicketService) -> None:
        self._otp_svc = otp_svc

    async def execute(self, data: VerifyOTPInput) -> VerifyOTPOutput:
        ticket = await self._otp_svc.verify_otp_and_issue_ticket(data.email, data.otp)
        return VerifyOTPOutput(signup_ticket=ticket)


__all__ = [
    "VerifyOTPUseCase",
    "VerifyOTPInput",
    "VerifyOTPOutput",
    "OTPInvalidError",
]
