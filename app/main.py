from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.router import api_router
from app.core.settings import settings
from app.core.logging import setup_logging
from app.infrastructure.messaging.websocket_manager import manager
from app.infrastructure.cache.redis_client import redis_startup, redis_shutdown



@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()

    await redis_startup()
    await manager.start()
    print("✅ WebSocket manager started")

    yield

    await manager.stop()
    await redis_shutdown()
    print("👋 WebSocket manager stopped")



def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        lifespan=lifespan,
    )

    app.include_router(api_router, prefix="/api")
    return app


app = create_app()


# ============================================
# Quick test endpoint to verify WebSocket works
# ============================================

@app.get("/api")
async def api_root():
    stats = manager.get_connection_stats()
    return {
        "message": "SmartVault API",
        "websocket_stats": stats,
    }
