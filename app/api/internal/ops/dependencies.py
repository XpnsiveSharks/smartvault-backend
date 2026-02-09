from __future__ import annotations

from fastapi import Depends, HTTPException, Request

from app.api.deps.internal import get_ops_authenticator, get_ops_rate_limiter
from app.infrastructure.security.internal_auth import OpsAuthenticator
from app.infrastructure.security.rate_limiter import RateLimiter, RateLimitExceeded
from app.core.settings import settings


async def ops_guard(
    request: Request,
    authenticator: OpsAuthenticator = Depends(get_ops_authenticator),
    limiter: RateLimiter = Depends(get_ops_rate_limiter),
) -> None:
    """Shared guard for /api/internal/ops endpoints."""

    identity = authenticator.authenticate(request)
    client_ip = request.client.host if request.client else "unknown"
    try:
        await limiter.allow_request(
            key=f"ops:{identity.principal}:{client_ip}",
            limit=settings.INTERNAL_OPS_RATE_LIMIT_PER_MIN,
            window_seconds=60,
        )
    except RateLimitExceeded:
        raise
    except HTTPException:
        raise
    except Exception:
        # Fail closed but controlled
        raise HTTPException(status_code=503, detail="Ops rate limiting unavailable")
