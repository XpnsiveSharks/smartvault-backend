from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.infrastructure.logging.audit import AuditLogger, AuditRecord
from app.infrastructure.security.internal_auth import redact_headers


class AdminAuditMiddleware(BaseHTTPMiddleware):
    """Emit audit records for all /internal/admin requests."""

    def __init__(self, app: ASGIApp, audit_logger: AuditLogger | None = None) -> None:
        super().__init__(app)
        self._audit_logger = audit_logger or AuditLogger()
        self._log = logging.getLogger(__name__)

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        path = request.url.path
        if not path.startswith("/api/internal/admin"):
            return await call_next(request)

        start = datetime.now(timezone.utc)
        status_code: int | None = None
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:  # noqa: BLE001
            status_code = getattr(exc, "status_code", None) or 500
            raise
        finally:
            identity = getattr(request.state, "admin_identity", None)
            logger = getattr(request.state, "audit_logger", self._audit_logger)
            record = AuditRecord(
                timestamp=start,
                principal=identity.principal if identity else "anonymous",
                auth_type=identity.auth_type if identity else "unknown",
                endpoint=path,
                method=request.method,
                status=status_code or 500,
                path_params=request.path_params or {},
                query_params=dict(request.query_params),
                headers=redact_headers(dict(request.headers)),
            )
            try:
                logger.log(record)
            except Exception:  # noqa: BLE001
                self._log.exception("Failed to emit admin audit record")

