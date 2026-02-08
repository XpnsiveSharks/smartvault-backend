from __future__ import annotations

from functools import lru_cache

from app.infrastructure.security.internal_auth import AdminAuthenticator, OpsAuthenticator
from app.infrastructure.security.rate_limiter import RateLimiter
from app.infrastructure.logging.audit import AuditLogger
from app.application.services.system_metrics_service import SystemMetricsService
from app.infrastructure.services.system_metrics_adapter import SystemMetricsAdapter


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


@lru_cache(maxsize=1)
def get_system_metrics_service() -> SystemMetricsService:
    adapter = SystemMetricsAdapter()
    return SystemMetricsService(adapter)
