from __future__ import annotations
from dataclasses import dataclass
from app.application.ports.otp_ticket_service import OTPTicketService
from app.application.ports.email_service import EmailService
from app.application.ports.rate_limiter import RateLimiter
from app.core.settings import settings

@dataclass
class RequestOTPInput:
    email: str
    client_ip: str

class RateLimitError(Exception):
    pass

class RequestOTP:
    def __init__(
        self,
        otp_service: OTPTicketService,
        email_service: EmailService,
        rate_limiter: RateLimiter,
    ):
        self._otp_service = otp_service
        self._email_service = email_service
        self._rate_limiter = rate_limiter

    async def execute(self, data: RequestOTPInput) -> None:
        if not await self._rate_limiter.allow_request(
            key=f"otp_req:{data.client_ip}",
            limit=settings.RATE_LIMIT_OTP_REQ_PER_MIN,
            window_seconds=60
        ):
            raise RateLimitError("Too many requests from this IP")

        if not await self._rate_limiter.allow_request(
            key=f"otp_req:email:{data.email.lower()}",
            limit=3,
            window_seconds=900,
        ):
            raise RateLimitError("Too many requests for this email")

        result = await self._otp_service.issue_otp(data.email)
        await self._email_service.send_otp(data.email, result.otp)
