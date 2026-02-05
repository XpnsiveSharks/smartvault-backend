from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status, Request
from starlette.concurrency import run_in_threadpool

from app.api.deps.users import get_create_user_uc, get_authenticate_user_uc
# This import is correct HERE (in the router), but NOT in deps/auth.py
from app.api.deps.auth import get_email_service, get_otp_ticket_service, get_rate_limiter, get_token_service
from app.application.use_cases.create_user import CreateUser, CreateUserInput, DuplicateEmailError
from app.application.use_cases.authenticate_user import AuthenticateUser, LoginInput, InvalidCredentialsError
from app.application.services.token_service import TokenService
from app.infrastructure.notifications.email_service import EmailService
from app.infrastructure.services.otp_ticket_service import OTPTicketService, OTPInvalidError, TicketInvalidError
from app.infrastructure.security.rate_limiter import RateLimiter
from app.core.settings import settings
from app.schemas.auth import OTPRequest, OTPVerifyRequest, OTPVerifyResponse, SignupRequest, LoginRequest, Token
from app.schemas.users import UserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/request-otp", status_code=status.HTTP_204_NO_CONTENT)
async def request_otp(  
    request: Request,
    payload: OTPRequest,
    otp_svc: OTPTicketService = Depends(get_otp_ticket_service),
    email_svc: EmailService = Depends(get_email_service),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> None:
    client_ip = request.client.host if request.client else "unknown"
    await limiter.allow_request(
        key=f"otp_req:{client_ip}",
        limit=settings.RATE_LIMIT_OTP_REQ_PER_MIN,
        window_seconds=60
    )
    # Limit requests per target email to mitigate distributed harassment/flooding
    await limiter.allow_request(
        key=f"otp_req:email:{payload.email.lower()}",
        limit=3,
        window_seconds=900,
    )
    logger.info("OTP_REQUEST email=%s ip=%s", payload.email, client_ip)
    result = await otp_svc.issue_otp(payload.email)
    await email_svc.send_otp(payload.email, result.otp)

@router.post("/verify-otp", response_model=OTPVerifyResponse)
async def verify_otp(
    payload: OTPVerifyRequest,
    otp_svc: OTPTicketService = Depends(get_otp_ticket_service),
) -> OTPVerifyResponse:
    try:
        ticket = await otp_svc.verify_otp_and_issue_ticket(payload.email, payload.otp)
        return OTPVerifyResponse(signup_ticket=ticket)
    except OTPInvalidError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))

@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupRequest,
    otp_svc: OTPTicketService = Depends(get_otp_ticket_service),
    uc: CreateUser = Depends(get_create_user_uc),
) -> UserResponse:
    try:
        await otp_svc.consume_ticket(payload.email, payload.signup_ticket)
        user = await run_in_threadpool(
            uc.execute,
            CreateUserInput(
                email=payload.email,
                password=payload.password,
                full_name=payload.full_name,
            )
        )
        return UserResponse.model_validate(user)
    except TicketInvalidError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))
    except DuplicateEmailError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.post("/login", response_model=Token)
async def login(
    request: Request,
    payload: LoginRequest,
    uc: AuthenticateUser = Depends(get_authenticate_user_uc),
    token_svc: TokenService = Depends(get_token_service),
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> Token:
    client_ip = request.client.host if request.client else "unknown"
    await limiter.allow_request(
        key=f"login_req:{client_ip}",
        limit=settings.RATE_LIMIT_LOGIN_REQ_PER_MIN,
        window_seconds=60
    )
    try:
        user = await run_in_threadpool(
            uc.execute,
            LoginInput(email=payload.email, password=payload.password)
        )
        
        token = token_svc.create_access_token(subject=user.id)
        return Token(access_token=token, token_type="bearer")
        
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )