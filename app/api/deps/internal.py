from __future__ import annotations

from functools import lru_cache

from app.infrastructure.security.internal_auth import AdminAuthenticator, OpsAuthenticator
from app.infrastructure.security.rate_limiter import RateLimiter
from app.infrastructure.logging.audit import AuditLogger


# Authentication providers
@lru_cache(maxsize=1)
def get_admin_authenticator() -> AdminAuthenticator:
    return AdminAuthenticator()


@lru_cache(maxsize=1)
def get_ops_authenticator() -> OpsAuthenticator:
    return OpsAuthenticator()


# Rate limiters (shared singleton per process)
_admin_rate_limiter = RateLimiter()
_ops_rate_limiter = RateLimiter()


def get_admin_rate_limiter() -> RateLimiter:
    return _admin_rate_limiter


def get_ops_rate_limiter() -> RateLimiter:
    return _ops_rate_limiter


@lru_cache(maxsize=1)
def get_audit_logger() -> AuditLogger:
    return AuditLogger()

