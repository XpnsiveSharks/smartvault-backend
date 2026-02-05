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
-- Keys: [OTP_KEY, TICKET_KEY, ATTEMPTS_KEY]
-- Args: [USER_INPUT_OTP, TICKET_VALUE, TICKET_TTL, MAX_ATTEMPTS]

local attempts_key = KEYS[3]
local current_attempts = tonumber(redis.call("GET", attempts_key) or "0")
local max_attempts = tonumber(ARGV[4])

-- 1. Check if already locked out
if current_attempts >= max_attempts then
    return -2 -- LOCKED
end

-- 2. Check if OTP exists
local stored_otp = redis.call("GET", KEYS[1])
if not stored_otp then
    return nil -- Expired or Not Found
end

-- 3. Verify OTP
if stored_otp == ARGV[1] then
    -- SUCCESS: Clean up and issue ticket
    redis.call("DEL", KEYS[1])
    redis.call("DEL", attempts_key)
    redis.call("SETEX", KEYS[2], ARGV[3], ARGV[2])
    return 1 -- SUCCESS
else
    -- FAILURE: Increment attempts
    local new_attempts = redis.call("INCR", attempts_key)
    redis.call("EXPIRE", attempts_key, 300) -- keep attempts briefly
    if new_attempts >= max_attempts then
        redis.call("DEL", KEYS[1]) -- invalidate OTP
        return -2 -- LOCKED
    end
    return 0 -- INVALID
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
        result = await redis.eval(self._TICKET_CONSUME_LUA, 1, key, expected)
        return result

    async def verify_otp_and_issue_ticket(self, email: str, otp: str) -> str:
        email = email.lower().strip()
        redis = await get_redis()
        ticket = secrets.token_urlsafe(32)
        otp_key = self._otp_key(email)
        ticket_key = self._ticket_key(ticket)
        attempts_key = f"otp_attempts:{email}"

        try:
            result = await redis.eval(
                self.ATOMIC_EXCHANGE_SCRIPT,
                3,
                otp_key,
                ticket_key,
                attempts_key,
                otp,
                email,
                settings.SIGNUP_TICKET_TTL_SECONDS,
                5,
            )
        except ResponseError as exc:
            raise OTPInvalidError('Invalid or expired OTP') from exc

        if result == 1:
            return ticket
        if result == 0:
            raise OTPInvalidError('Invalid OTP')
        if result == -2:
            raise OTPInvalidError('Too many failed attempts. OTP invalidated.')

        raise OTPInvalidError('OTP expired or not found')

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