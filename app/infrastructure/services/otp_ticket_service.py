from __future__ import annotations

import secrets
from dataclasses import dataclass

from redis.exceptions import ResponseError

from app.core.settings import settings
from app.infrastructure.cache.redis_client import (
    get_redis,
    redis_setex,
)

@dataclass(frozen=True)
class OTPResult:
    otp: str

class OTPInvalidError(ValueError):
    pass

class TicketInvalidError(ValueError):
    pass

class OTPTicketService:
    ATOMIC_EXCHANGE_SCRIPT = """
-- Keys: [OTP_KEY, TICKET_KEY]
-- Args: [USER_INPUT_OTP, TICKET_VALUE, TICKET_TTL_SECONDS]
local stored_otp = redis.call('GET', KEYS[1])
if stored_otp == ARGV[1] then
    redis.call('DEL', KEYS[1])
    redis.call('SETEX', KEYS[2], ARGV[3], ARGV[2])
    return 1
else
    return 0
end
"""

    _TICKET_CONSUME_LUA = """
local current = redis.call('GET', KEYS[1])
if not current then return nil end
if current ~= ARGV[1] then return 0 end
local ok, val = pcall(redis.call, 'GETDEL', KEYS[1])
if ok then
  return val
end
redis.call('DEL', KEYS[1])
return current
"""

    def _otp_key(self, email: str) -> str:
        return f"otp:{email.lower()}"

    def _ticket_key(self, ticket: str) -> str:
        return f"signup_ticket:{ticket}"

    def generate_otp(self) -> str:
        # 6 digits, cryptographically strong
        return f"{secrets.randbelow(1_000_000):06d}"

    async def issue_otp(self, email: str) -> OTPResult:
        email = email.lower().strip()
        otp = self.generate_otp()
        await redis_setex(self._otp_key(email), settings.OTP_TTL_SECONDS, otp.encode("utf-8"))
        return OTPResult(otp=otp)

    async def _consume_ticket_value(self, key: str, expected: str) -> bytes | None | int:
        """Atomically read-and-delete the signup ticket only when it matches expected email."""
        redis = await get_redis()
        try:
            result = await redis.eval(self._TICKET_CONSUME_LUA, 1, key, expected)
            return result
        except ResponseError:
            # Fallback if EVAL is disabled: best-effort match then delete
            value = await redis.get(key)
            if value is None:
                return None
            if value.decode("utf-8") != expected:
                return 0
            await redis.delete(key)
            return value

    async def verify_otp_and_issue_ticket(self, email: str, otp: str) -> str:
        email = email.lower().strip()
        redis = await get_redis()
        ticket = secrets.token_urlsafe(32)
        otp_key = self._otp_key(email)
        ticket_key = self._ticket_key(ticket)

        try:
            result = await redis.eval(
                self.ATOMIC_EXCHANGE_SCRIPT,
                2,
                otp_key,
                ticket_key,
                otp,
                email,
                settings.SIGNUP_TICKET_TTL_SECONDS,
            )
        except ResponseError as exc:
            raise OTPInvalidError('Invalid or expired OTP') from exc

        if result == 1:
            return ticket

        raise OTPInvalidError('Invalid or expired OTP')

    async def consume_ticket(self, email: str, ticket: str) -> None:
        email = email.lower().strip()
        key = self._ticket_key(ticket)
        expected = email
        result = await self._consume_ticket_value(key, expected)

        if result is None:
            raise TicketInvalidError("Signup ticket expired or invalid")

        if result == 0 or (isinstance(result, bytes) and result.decode("utf-8") != expected):
            raise TicketInvalidError("Signup ticket does not match email")

        # success path: ticket already deleted atomically