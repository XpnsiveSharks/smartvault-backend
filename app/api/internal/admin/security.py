from fastapi import APIRouter, Depends

from app.api.internal.dependencies import admin_guard

router = APIRouter(prefix="/security", dependencies=[Depends(admin_guard)])


@router.get("/signals")
async def security_signals() -> dict[str, str]:
    return {"detail": "admin security signals placeholder"}

