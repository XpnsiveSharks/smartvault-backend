from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends

from app.api.deps.users import get_authenticate_user_uc, get_create_user_uc
from app.application.services.token_service import TokenService
from app.application.use_cases.auth_login import LoginUseCase
from app.application.use_cases.auth_request_otp import RequestOTPUseCase
from app.application.use_cases.auth_signup import SignupUseCase
from app.application.use_cases.auth_verify_otp import VerifyOTPUseCase
from app.application.use_cases.authenticate_user import AuthenticateUser
from app.application.use_cases.create_user import CreateUser
from app.core.settings import settings
from app.infrastructure.notifications.email_service import (
    DevEmailService,
    EmailService,
    SMTPEmailService,
)
from app.infrastructure.security.rate_limiter import RateLimiter
from app.infrastructure.services.otp_ticket_service import OTPTicketService


def _build_email_service() -> EmailService:
    backend = settings.resolved_email_backend.lower()
    if backend == "smtp":
        if not settings.SMTP_HOST:
            raise ValueError("SMTP_HOST must be set when EMAIL_BACKEND=smtp")
        from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
        if not from_email:
            raise ValueError("SMTP_FROM_EMAIL or SMTP_USER must be set for SMTP email backend")

        return SMTPEmailService(
            host=settings.SMTP_HOST,
            port=settings.SMTP_PORT or 587,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            from_email=from_email,
            from_name=settings.SMTP_FROM_NAME,
            use_tls=True,
        )
    return DevEmailService()


def get_email_service() -> Generator[EmailService, None, None]:
    yield _build_email_service()


def get_otp_ticket_service() -> Generator[OTPTicketService, None, None]:
    yield OTPTicketService()


def get_rate_limiter() -> Generator[RateLimiter, None, None]:
    yield RateLimiter()


def get_token_service() -> Generator[TokenService, None, None]:
    yield TokenService()


def get_request_otp_uc(
    otp_svc: OTPTicketService = Depends(get_otp_ticket_service),
    email_svc: EmailService = Depends(get_email_service),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> Generator[RequestOTPUseCase, None, None]:
    yield RequestOTPUseCase(otp_svc=otp_svc, email_svc=email_svc, limiter=limiter)


def get_verify_otp_uc(
    otp_svc: OTPTicketService = Depends(get_otp_ticket_service),
) -> Generator[VerifyOTPUseCase, None, None]:
    yield VerifyOTPUseCase(otp_svc=otp_svc)


def get_signup_uc(
    otp_svc: OTPTicketService = Depends(get_otp_ticket_service),
    create_user_uc: CreateUser = Depends(get_create_user_uc),
) -> Generator[SignupUseCase, None, None]:
    yield SignupUseCase(otp_svc=otp_svc, create_user_uc=create_user_uc)


def get_login_uc(
    auth_uc: AuthenticateUser = Depends(get_authenticate_user_uc),
    token_svc: TokenService = Depends(get_token_service),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> Generator[LoginUseCase, None, None]:
    yield LoginUseCase(auth_uc=auth_uc, token_svc=token_svc, limiter=limiter)
