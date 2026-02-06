from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps.users import get_get_me_uc, get_update_me_uc
from app.api.deps.auth import get_current_user_id
from app.application.use_cases.get_me import GetMe
from app.application.use_cases.update_me import UpdateMe
from app.schemas.users import UserResponse, UpdateMeRequest
from app.api.deps.users import get_create_user_uc
from app.application.use_cases.create_user import CreateUser, CreateUserInput, DuplicateEmailError
from app.schemas.users import CreateUserRequest, UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: CreateUserRequest, uc: CreateUser = Depends(get_create_user_uc)) -> UserResponse:
    try:
        user = uc.execute(
            CreateUserInput(
                email=payload.email,
                password=payload.password,
                full_name=payload.full_name,
            )
        )
        return UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            created_at=user.created_at,
        )
    except DuplicateEmailError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

@router.get("/me", response_model=UserResponse)
async def get_me(
    user_id: str = Depends(get_current_user_id),
    uc: GetMe = Depends(get_get_me_uc),
) -> UserResponse:
    user = uc.execute(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)

@router.patch("/me", response_model=UserResponse)
async def update_me(
    payload: UpdateMeRequest,
    user_id: str = Depends(get_current_user_id),
    uc: UpdateMe = Depends(get_update_me_uc),
) -> UserResponse:
    user = uc.execute(user_id, payload.full_name)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse.model_validate(user)