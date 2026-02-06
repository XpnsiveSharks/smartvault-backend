from __future__ import annotations

import logging
from email.message import EmailMessage
from email.utils import formataddr
from typing import Protocol, runtime_checkable

try:
    import aiosmtplib  # type: ignore
except ImportError:  # pragma: no cover - only hit when optional dep missing
    aiosmtplib = None  # type: ignore

log = logging.getLogger(__name__)


@runtime_checkable
class EmailService(Protocol):
    async def send_otp(self, to_email: str, otp: str) -> None:
        ...


class DevEmailService:
    async def send_otp(self, to_email: str, otp: str) -> None:
        # Dev-only backend; log full OTP for easier testing.
        log.debug("DEV EMAIL: sending OTP to %s code=%s", to_email, otp)


class SMTPEmailService:
    def __init__(
        self,
        *,
        host: str,
        port: int = 587,
        username: str | None = None,
        password: str | None = None,
        from_email: str,
        from_name: str | None = None,
        use_tls: bool = True,
    ) -> None:
        if aiosmtplib is None:
            raise RuntimeError("aiosmtplib is required for SMTPEmailService")
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.from_email = from_email
        self.from_name = from_name
        self.use_tls = use_tls

    async def send_otp(self, to_email: str, otp: str) -> None:
        assert aiosmtplib is not None, "SMTP backend not available"

        msg = EmailMessage()
        msg["From"] = (
            formataddr((self.from_name, self.from_email))
            if self.from_name
            else self.from_email
        )
        msg["To"] = to_email
        msg["Subject"] = "Your SmartVault verification code"
        msg.set_content(
            "Use the code below to finish signing in to SmartVault.\n\n"
            f"Code: {otp}\n"
            "If you did not request this code, you can ignore this email."
        )

        await aiosmtplib.send(
            message=msg,
            hostname=self.host,
            port=self.port,
            username=self.username,
            password=self.password,
            start_tls=self.use_tls,
        )