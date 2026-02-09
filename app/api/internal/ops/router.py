from fastapi import APIRouter, Depends

from app.api.internal.ops.dependencies import ops_guard
from app.api.internal.ops import system

ops_router = APIRouter()

# Attach system routes under /ops/system
ops_router.include_router(system.router, tags=["ops-system"])


@ops_router.get("/health", dependencies=[Depends(ops_guard)])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@ops_router.get("/metrics", dependencies=[Depends(ops_guard)])
async def metrics() -> dict[str, str]:
    # Placeholder: real metrics should be provided by dedicated service.
    return {"detail": "metrics placeholder"}


@ops_router.get("/security", dependencies=[Depends(ops_guard)])
async def security_signals() -> dict[str, str]:
    # Placeholder for ops-focused security signals (e.g., abuse indicators).
    return {"detail": "security signals placeholder"}
