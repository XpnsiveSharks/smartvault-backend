from fastapi import APIRouter, Depends

from app.api.internal.dependencies import admin_guard

router = APIRouter(prefix="/system", dependencies=[Depends(admin_guard)])


@router.get("/overview")
async def system_overview() -> dict[str, str]:
    return {"detail": "system overview placeholder"}

