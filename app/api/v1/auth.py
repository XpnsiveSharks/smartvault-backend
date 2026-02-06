from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps.auth import (
    get_login_uc,
    get_request_otp_uc,
    get_signup_uc,
    get_verify_otp_uc,
)
from app.application.use_cases.auth_login import LoginInputDTO, LoginUseCase
from app.application.use_cases.auth_request_otp import RequestOTPInput, RequestOTPUseCase
from app.application.use_cases.auth_signup import SignupInput, SignupUseCase, TicketInvalidError
from app.application.use_cases.auth_verify_otp import (
    OTPInvalidError,
    VerifyOTPInput,
    VerifyOTPUseCase,
)
from app.application.use_cases.authenticate_user import InvalidCredentialsError
from app.application.use_cases.create_user import DuplicateEmailError
from app.schemas.auth import (
    LoginRequest,
    OTPRequest,
    OTPVerifyRequest,
    OTPVerifyResponse,
    SignupRequest,
    Token,
)
from app.schemas.users import UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/request-otp", status_code=status.HTTP_204_NO_CONTENT)
async def request_otp(
    request: Request,
    payload: OTPRequest,
    uc: RequestOTPUseCase = Depends(get_request_otp_uc),
) -> None:
    client_ip = request.client.host if request.client else "unknown"
    await uc.execute(RequestOTPInput(email=payload.email, client_ip=client_ip))


@router.post("/verify-otp", response_model=OTPVerifyResponse)
async def verify_otp(
    payload: OTPVerifyRequest,
    uc: VerifyOTPUseCase = Depends(get_verify_otp_uc),
) -> OTPVerifyResponse:
    try:
        result = await uc.execute(VerifyOTPInput(email=payload.email, otp=payload.otp))
        return OTPVerifyResponse(signup_ticket=result.signup_ticket)
    except OTPInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    payload: SignupRequest,
    uc: SignupUseCase = Depends(get_signup_uc),
) -> UserResponse:
    try:
        user = await uc.execute(
            SignupInput(
                email=payload.email,
                password=payload.password,
                full_name=payload.full_name,
                signup_ticket=payload.signup_ticket,
            )
        )
        return UserResponse.model_validate(user)
    except TicketInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    except DuplicateEmailError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


# UPDATED LOGIN
@router.post("/login", response_model=Token)
async def login(
    request: Request,
    payload: LoginRequest,
    uc: LoginUseCase = Depends(get_login_uc),
) -> Token:
    client_ip = request.client.host if request.client else "unknown"
    try:
        result = await uc.execute(
            LoginInputDTO(
                email=payload.email,
                password=payload.password,
                client_ip=client_ip,
            )
        )
        return Token(access_token=result.access_token, token_type=result.token_type)
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
