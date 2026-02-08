from fastapi import APIRouter, Depends

from app.api.internal.dependencies import admin_guard

router = APIRouter(prefix="/exports", dependencies=[Depends(admin_guard)])


@router.get("/preview")
async def exports_preview() -> dict[str, str]:
    return {"detail": "exports placeholder"}

