from __future__ import annotations

from fastapi import Depends, Request, HTTPException

from app.api.deps.internal import (
    get_admin_authenticator,
    get_admin_rate_limiter,
    get_audit_logger,
)
from app.infrastructure.logging.audit import AuditLogger
from app.infrastructure.security.internal_auth import AdminAuthenticator
from app.infrastructure.security.rate_limiter import RateLimiter
from app.infrastructure.security.rate_limiter import RateLimitExceeded
from app.core.settings import settings


async def admin_guard(
    request: Request,
    authenticator: AdminAuthenticator = Depends(get_admin_authenticator),
    limiter: RateLimiter = Depends(get_admin_rate_limiter),
) -> None:
    identity = authenticator.authenticate(request)
    request.state.admin_identity = identity
    client_ip = request.client.host if request.client else "unknown"
    try:
        await limiter.allow_request(
            key=f"admin:{identity.principal}:{client_ip}",
            limit=settings.INTERNAL_ADMIN_RATE_LIMIT_PER_MIN,
            window_seconds=60,
        )
    except RateLimitExceeded:
        raise
    except HTTPException:
        raise
    except Exception:
        # Fail closed with controlled message to avoid leaking infra details
        raise HTTPException(status_code=503, detail="Admin rate limiting unavailable")


async def admin_audit_hook(
    request: Request,
    audit_logger: AuditLogger = Depends(get_audit_logger),
) -> None:
    # No-op dependency; middleware handles final emit. Exposes logger so tests can override easily.
    request.state.audit_logger = audit_logger
