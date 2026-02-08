from fastapi import APIRouter

from app.api.v1 import health, vaults, users, auth, access
from app.websocket import vault_socket

# Root API router
api_router = APIRouter()

# Versioned API router
v1_router = APIRouter(prefix="/v1")

# HTTP (v1)
v1_router.include_router(health.router)
v1_router.include_router(vaults.router)
v1_router.include_router(users.router)
v1_router.include_router(auth.router)
v1_router.include_router(access.router)
# Attach v1 to root
api_router.include_router(v1_router)

# WEBSOCKET (versioned)
api_router.include_router(vault_socket.router, prefix="/v1", tags=["websockets"])
