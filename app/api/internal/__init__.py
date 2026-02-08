from fastapi import APIRouter

from app.api.internal.ops.router import ops_router
from app.api.internal.admin.router import admin_router

# Root router for all internal surfaces
internal_router = APIRouter(prefix="/internal")

# Attach sub-surfaces
internal_router.include_router(ops_router, prefix="/ops", tags=["internal-ops"])
internal_router.include_router(admin_router, prefix="/admin", tags=["internal-admin"])

