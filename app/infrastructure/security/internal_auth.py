from __future__ import annotations

"""Centralized authentication for internal surfaces.

This module keeps API handlers free of credential handling while allowing
both shared-token and JWT-based authentication strategies.
"""

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from fastapi import HTTPException, Request, status
from jose import JWTError, jwt

from app.core.settings import settings


SENSITIVE_HEADERS: Iterable[str] = ("authorization", "x-admin-token", "x-ops-token")


@dataclass
class AuthIdentity:
    principal: str
    auth_type: str
    token_id: str | None = None
    issued_at: datetime | None = None


class AuthConfigError(HTTPException):
    def __init__(self, message: str = "Admin authentication is not configured"):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=message)


class ForbiddenError(HTTPException):
    def __init__(self, message: str = "Insufficient privileges"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=message)


class AdminAuthenticator:
    """Authenticate `internal/admin` requests.

    Supports two strategies:
    - Bearer JWT with an `admin` role claim
    - Shared admin token presented via `X-Admin-Token`
    """

    def __init__(self, cfg=settings):
        self._cfg = cfg

    def authenticate(self, request: Request) -> AuthIdentity:
        bearer = request.headers.get("authorization")
        shared = request.headers.get("x-admin-token")

        if bearer and bearer.lower().startswith("bearer "):
            token = bearer.split(" ", 1)[1].strip()
            return self._authenticate_jwt(token)

        if shared:
            return self._authenticate_shared_token(shared)

        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin credentials required")

    def _authenticate_jwt(self, token: str) -> AuthIdentity:
        secret = self._cfg.ADMIN_JWT_SECRET or self._cfg.SECRET_KEY
        if not secret:
            raise AuthConfigError()

        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=[self._cfg.ADMIN_JWT_ALGORITHM],
                options={"require_exp": False},
            )
        except JWTError as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired admin token") from exc

        role = payload.get("role") or payload.get("roles")
        if isinstance(role, str):
            has_role = role.lower() == "admin"
        elif isinstance(role, (list, tuple, set)):
            has_role = any(str(r).lower() == "admin" for r in role)
        else:
            has_role = False

        if not has_role:
            raise ForbiddenError()

        sub = str(payload.get("sub") or payload.get("admin_id") or "admin")
        issued_at = payload.get("iat")
        issued_dt = datetime.fromtimestamp(issued_at, tz=timezone.utc) if isinstance(issued_at, (int, float)) else None
        return AuthIdentity(
            principal=sub,
            auth_type="admin_jwt",
            token_id=str(payload.get("jti")) if payload.get("jti") else None,
            issued_at=issued_dt,
        )

    def _authenticate_shared_token(self, token: str) -> AuthIdentity:
        expected_hash = self._cfg.ADMIN_SHARED_TOKEN_HASH
        if not expected_hash:
            raise AuthConfigError("Shared admin token is not configured")

        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(digest, expected_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin credentials")

        token_id = self._cfg.ADMIN_TOKEN_ID or "admin-shared"
        return AuthIdentity(principal=token_id, auth_type="shared_token", token_id=token_id)


class OpsAuthenticator:
    """Authenticate `internal/ops` requests.

    By default expects a shared token. In development mode (`DEV_AUTH_BYPASS`),
    authentication can be skipped to avoid blocking local diagnostics.
    """

    def __init__(self, cfg=settings):
        self._cfg = cfg

    def authenticate(self, request: Request) -> AuthIdentity:
        if self._cfg.DEV_AUTH_BYPASS and not self._cfg.INTERNAL_OPS_TOKEN_HASH:
            return AuthIdentity(principal="dev-ops", auth_type="dev-bypass")

        expected_hash = self._cfg.INTERNAL_OPS_TOKEN_HASH
        if not expected_hash:
            raise AuthConfigError("Ops authentication is not configured")

        token = request.headers.get("x-ops-token")
        if not token:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Ops credentials required")

        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(digest, expected_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid ops credentials")

        token_id = self._cfg.INTERNAL_OPS_TOKEN_ID or "ops-shared"
        return AuthIdentity(principal=token_id, auth_type="shared_token", token_id=token_id)


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Redact sensitive headers for potential logging."""

    redacted: dict[str, str] = {}
    for key, value in headers.items():
        if key.lower() in SENSITIVE_HEADERS:
            redacted[key] = "[redacted]"
        else:
            redacted[key] = value
    return redacted

