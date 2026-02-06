from __future__ import annotations
import secrets
from redis import Redis
from app.core.settings import settings

class RedisRefreshTokenStore:
    def __init__(self, redis: Redis):
        self._redis = redis
        # 7 days expiration for refresh tokens
        self._ttl_seconds = 7 * 24 * 60 * 60 

    def create_token(self, user_id: str) -> str:
        """Generate opaque token and store mapping: token -> user_id"""
        token = secrets.token_urlsafe(32)
        key = f"refresh:{token}"
        self._redis.setex(key, self._ttl_seconds, user_id)
        return token

    def rotate_token(self, old_token: str) -> tuple[str | None, str | None]:
        """
        Atomically consume old_token and issue new_token.
        Returns: (new_token, user_id) OR (None, None) if invalid.
        """
        old_key = f"refresh:{old_token}"
        
        # ATOMIC: Get value AND Delete key in one op.
        # This prevents race conditions and ensures one-time use.
        user_id_bytes = self._redis.getdel(old_key)
        
        if not user_id_bytes:
            return None, None
            
        user_id = user_id_bytes.decode("utf-8")
        
        # Issue new token
        new_token = self.create_token(user_id)
        return new_token, user_id

    def revoke(self, token: str) -> None:
        """Destroy the token immediately."""
        key = f"refresh:{token}"
        self._redis.delete(key)