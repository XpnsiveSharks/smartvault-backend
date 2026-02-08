from fastapi import APIRouter, Depends

from app.api.internal.admin import system, business, security, exports
from app.api.internal.dependencies import admin_audit_hook

admin_router = APIRouter(dependencies=[Depends(admin_audit_hook)])

# Attach placeholder modules; they each apply admin guard via shared dependency.
admin_router.include_router(system.router, tags=["admin-system"])
admin_router.include_router(business.router, tags=["admin-business"])
admin_router.include_router(security.router, tags=["admin-security"])
admin_router.include_router(exports.router, tags=["admin-exports"])

