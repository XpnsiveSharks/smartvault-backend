from fastapi import APIRouter, Depends

from app.api.internal.dependencies import admin_guard

router = APIRouter(prefix="/business", dependencies=[Depends(admin_guard)])


@router.get("/kpis")
async def business_kpis() -> dict[str, str]:
    return {"detail": "business KPIs placeholder"}

