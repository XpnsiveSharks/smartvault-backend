from __future__ import annotations
from datetime import datetime, timedelta, timezone
from jose import jwt
from app.core.settings import settings
from app.infrastructure.services.refresh_token_store import RedisRefreshTokenStore

class TokenService:
    def __init__(self, refresh_store: RedisRefreshTokenStore):
        self._refresh_store = refresh_store

    def create_access_token(self, subject: str | int) -> str:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode = {"exp": expire, "sub": str(subject)}
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
        return encoded_jwt

    def create_refresh_token(self, user_id: str) -> str:
        return self._refresh_store.create_token(user_id)

    def rotate_refresh_token(self, old_token: str) -> tuple[str, str, str]:
        """
        Rotates the refresh token.
        Returns: (new_access_token, new_refresh_token, user_id)
        Raises: ValueError if invalid.
        """
        new_refresh, user_id = self._refresh_store.rotate_token(old_token)
        
        if not new_refresh or not user_id:
            raise ValueError("Invalid or expired refresh token")
            
        new_access = self.create_access_token(user_id)
        return new_access, new_refresh, user_id

    def revoke_refresh_token(self, token: str) -> None:
        self._refresh_store.revoke(token)