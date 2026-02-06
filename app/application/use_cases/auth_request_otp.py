from __future__ import annotations

import logging
from dataclasses import dataclass

from app.core.settings import settings
from app.infrastructure.notifications.email_service import EmailService
from app.infrastructure.security.rate_limiter import RateLimiter
from app.infrastructure.services.otp_ticket_service import OTPTicketService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RequestOTPInput:
    email: str
    client_ip: str


class RequestOTPUseCase:
    def __init__(
        self,
        otp_svc: OTPTicketService,
        email_svc: EmailService,
        limiter: RateLimiter,
    ) -> None:
        self._otp_svc = otp_svc
        self._email_svc = email_svc
        self._limiter = limiter

    async def execute(self, data: RequestOTPInput) -> None:
        await self._limiter.allow_request(
            key=f"otp_req:{data.client_ip}",
            limit=settings.RATE_LIMIT_OTP_REQ_PER_MIN,
            window_seconds=60,
        )
        await self._limiter.allow_request(
            key=f"otp_req:email:{data.email.lower()}",
            limit=3,
            window_seconds=900,
        )

        logger.info("OTP_REQUEST email=%s ip=%s", data.email, data.client_ip)
        result = await self._otp_svc.issue_otp(data.email)
        await self._email_svc.send_otp(data.email, result.otp)
