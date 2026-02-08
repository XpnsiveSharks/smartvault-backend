from fastapi import APIRouter, Depends, Request, Response

from app.api.deps.internal import get_ops_authenticator, get_ops_rate_limiter
from app.infrastructure.security.internal_auth import OpsAuthenticator
from app.infrastructure.security.rate_limiter import RateLimiter
from app.core.settings import settings

ops_router = APIRouter()


async def _ops_guard(
    request: Request,
    authenticator: OpsAuthenticator = Depends(get_ops_authenticator),
    limiter: RateLimiter = Depends(get_ops_rate_limiter),
) -> None:
    identity = authenticator.authenticate(request)
    client_ip = request.client.host if request.client else "unknown"
    await limiter.allow_request(
        key=f"ops:{identity.principal}:{client_ip}",
        limit=settings.INTERNAL_OPS_RATE_LIMIT_PER_MIN,
        window_seconds=60,
    )


@ops_router.get("/health", dependencies=[Depends(_ops_guard)])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@ops_router.get("/metrics", dependencies=[Depends(_ops_guard)])
async def metrics() -> dict[str, str]:
    # Placeholder: real metrics should be provided by dedicated service.
    return {"detail": "metrics placeholder"}


@ops_router.get("/security", dependencies=[Depends(_ops_guard)])
async def security_signals() -> dict[str, str]:
    # Placeholder for ops-focused security signals (e.g., abuse indicators).
    return {"detail": "security signals placeholder"}

