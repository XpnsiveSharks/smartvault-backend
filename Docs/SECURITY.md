# Security Guide

This document outlines SmartVault's security model, best practices, and policies for handling sensitive data.

---

## Table of Contents

1. [Security Model Overview](#security-model-overview)
2. [Authentication](#authentication)
3. [Authorization](#authorization)
4. [PIN Security](#pin-security)
5. [PII & Sensitive Data](#pii--sensitive-data)
6. [Secrets Management](#secrets-management)
7. [Rate Limiting](#rate-limiting)
8. [Security Testing](#security-testing)
9. [Vulnerability Reporting](#vulnerability-reporting)

---

## Security Model Overview

SmartVault implements **defense-in-depth** security with multiple layers:

```
┌─────────────────────────────────────────────────┐
│  Rate Limiting (Redis)                          │
│  - Prevents brute force attacks                 │
│  - Limits OTP/login attempts                    │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│  Authentication (JWT + Password Hashing)        │
│  - PBKDF2 password hashing                      │
│  - JWT token-based sessions                     │
│  - Refresh token rotation                       │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│  Authorization (Role-Based Access Control)      │
│  - ADMIN, MEMBER, VIEWER roles                  │
│  - Resource ownership validation                │
│  - Permission checks in use cases               │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│  Data Protection                                │
│  - PIN hashing (PBKDF2, never reversible)       │
│  - PII redaction in logs                        │
│  - Encrypted connections (HTTPS/TLS)            │
└─────────────────────────────────────────────────┘
```

### Core Security Principles

1. **Never trust user input** — Validate and sanitize all inputs
2. **Least privilege** — Grant minimum permissions necessary
3. **Defense in depth** — Multiple security layers
4. **Fail securely** — Errors should not leak sensitive information
5. **Zero PII in logs/metrics** — Never log passwords, PINs, tokens
6. **Secure by default** — Security features enabled out-of-the-box

---

## Authentication

### Password Security

**Hashing Algorithm:** PBKDF2-SHA256

**Configuration:**
```python
# app/infrastructure/security/password_hasher.py
from passlib.hash import pbkdf2_sha256

class PasswordHasher:
    @staticmethod
    def hash(password: str) -> str:
        return pbkdf2_sha256.hash(password)
    
    @staticmethod
    def verify(password: str, hash: str) -> bool:
        return pbkdf2_sha256.verify(password, hash)
```

**Password Requirements:**
- Minimum 8 characters
- No maximum length (handle long passwords gracefully)
- No complexity requirements (user choice)
- Never store plaintext passwords

**Password Storage:**
```python
# ✅ CORRECT: Store hash only
user.password_hash = PasswordHasher.hash(password)

# ❌ NEVER: Store plaintext
user.password = password  # ❌❌❌
```

### JWT Tokens

**Token Types:**
- **Access Token:** Short-lived (30 minutes), used for API requests
- **Refresh Token:** Long-lived (7 days), used to obtain new access tokens

**Token Structure:**
```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "exp": 1234567890,
  "iat": 1234567890,
  "type": "access"
}
```

**Token Generation:**
```python
from app.application.services.token_service import TokenService

# Generate tokens
access_token = TokenService.create_access_token(user_id=user.id)
refresh_token = TokenService.create_refresh_token(user_id=user.id)
```

**Token Validation:**
```python
# API layer dependency
@router.get("/protected")
def protected_route(user = Depends(get_current_user)):
    # User is authenticated
    return {"user_id": user.id}
```

**Security Considerations:**
- ✅ Tokens are signed with `SECRET_KEY`
- ✅ Tokens expire automatically
- ✅ Refresh token rotation recommended (future enhancement)
- ❌ Never log tokens
- ❌ Never send tokens in query parameters (use Authorization header)

### Session Management

**Stateless Sessions:**
- JWT tokens contain all session data
- No server-side session storage
- Enables horizontal scaling

**Token Revocation (Future):**
- Implement refresh token store in Redis
- Track revoked tokens
- Support logout across all devices

---

## Authorization

### Role-Based Access Control (RBAC)

**Roles:**

| Role | Permissions |
|------|-------------|
| **OWNER** | Full control (create, delete, manage members, unlock) |
| **ADMIN** | Manage members, unlock vault |
| **MEMBER** | Unlock vault, view status |
| **VIEWER** | View vault status only (cannot unlock) |

**Implementation:**
```python
# Domain model
class VaultMembership:
    vault_id: str
    user_id: int
    role: VaultRole  # OWNER, ADMIN, MEMBER, VIEWER

# Authorization service
class AuthorizationService:
    def can_unlock_vault(self, user_id: int, vault_id: str) -> bool:
        membership = self.get_membership(user_id, vault_id)
        return membership.role in [VaultRole.OWNER, VaultRole.ADMIN, VaultRole.MEMBER]
    
    def can_add_member(self, user_id: int, vault_id: str) -> bool:
        membership = self.get_membership(user_id, vault_id)
        return membership.role in [VaultRole.OWNER, VaultRole.ADMIN]
```

**Enforcement Points:**

**1. Use Case Layer:**
```python
class UnlockVaultWithPIN:
    def execute(self, vault_id: str, user_id: int, pin: str):
        # Authorization check
        if not self.auth_service.can_unlock_vault(user_id, vault_id):
            raise UnauthorizedException("User cannot unlock this vault")
        
        # Continue with unlock logic
```

**2. API Layer:**
```python
@router.post("/vaults/{vault_id}/unlock")
def unlock_vault(
    vault_id: str,
    request: UnlockRequest,
    user = Depends(get_current_user),
    auth = Depends(require_vault_member),  # Dependency check
):
    # User is authenticated and authorized
    use_case.execute(vault_id, user.id, request.pin)
```

### Resource Ownership

**Principle:** Users can only access resources they own or have been granted access to.

**Example:**
```python
# ✅ CORRECT: Check ownership
def get_vault(vault_id: str, user_id: int):
    vault = vault_repo.get_by_id(vault_id)
    
    if vault.owner_id != user_id and not vault.has_member(user_id):
        raise VaultNotFoundException()  # Don't leak existence
    
    return vault

# ❌ WRONG: No ownership check
def get_vault(vault_id: str):
    return vault_repo.get_by_id(vault_id)  # Any user can access
```

---

## PIN Security

### PIN Storage

**CRITICAL RULES:**
- ✅ PINs are **HASHED** using PBKDF2-SHA256
- ✅ PINs are **NEVER RETRIEVABLE** after creation
- ✅ PINs are **NEVER LOGGED** or sent to monitoring
- ❌ Never store plaintext PINs
- ❌ Never return PINs in API responses

**Implementation:**
```python
# app/domain/value_objects/pin.py
@dataclass(frozen=True)
class PIN:
    value: str
    
    def __post_init__(self):
        if not re.match(r'^\d{4,8}$', self.value):
            raise InvalidPINException()
    
    def hash(self) -> str:
        return pbkdf2_sha256.hash(self.value)
    
    def verify(self, hash: str) -> bool:
        return pbkdf2_sha256.verify(self.value, hash)
```

**Storage:**
```python
# ✅ CORRECT
vault.pin_hash = pin.hash()  # Store hash only

# ❌ NEVER
vault.pin = pin.value  # ❌❌❌ Never store plaintext
```

### PIN Validation

**Rate Limiting:**
- Maximum 5 attempts per 15 minutes per vault
- Automatic lockout after 5 failures
- Lockout duration: 15 minutes

**Implementation:**
```python
# app/infrastructure/cache/rate_limiter.py
class RedisRateLimiter:
    def check_and_record(self, key: str, max_attempts: int, window: int):
        attempts = redis.incr(f"attempts:{key}")
        
        if attempts == 1:
            redis.expire(f"attempts:{key}", window)
        
        if attempts > max_attempts:
            redis.setex(f"lockout:{key}", window, "1")
            raise RateLimitExceededException()
```

**Timing Attack Prevention:**
```python
# ✅ CORRECT: Constant-time comparison (built into PBKDF2 verify)
def verify_pin(pin: str, hash: str) -> bool:
    return pbkdf2_sha256.verify(pin, hash)  # Constant-time

# ❌ WRONG: Early exit leaks information
def verify_pin(pin: str, stored_pin: str) -> bool:
    return pin == stored_pin  # Timing attack vulnerable
```

---

## PII & Sensitive Data

### Sensitive Data Classification

| Category | Examples | Logging | Metrics | Sentry |
|----------|----------|---------|---------|--------|
| **Authentication Secrets** | Passwords, PINs, API keys | ❌ NEVER | ❌ NEVER | ❌ NEVER |
| **Tokens** | JWT tokens, session IDs | ❌ NEVER | ❌ NEVER | ❌ NEVER |
| **PII** | Email, phone, address | ⚠️ Redacted | ❌ No | ⚠️ Scrubbed |
| **Business Data** | Vault IDs, user IDs | ✅ Yes | ✅ Yes | ✅ Yes |
| **Audit Events** | Unlock events, failures | ✅ Yes | ✅ Yes | ✅ Yes |

### Logging Redaction

**Automatic redaction:**
```python
# app/core/logging.py
SENSITIVE_FIELDS = [
    "password",
    "pin",
    "token",
    "secret",
    "api_key",
    "authorization",
]

def redact_sensitive_fields(event_dict):
    for key in event_dict:
        if any(sensitive in key.lower() for sensitive in SENSITIVE_FIELDS):
            event_dict[key] = "[REDACTED]"
    return event_dict
```

**Example:**
```python
logger.info("user_authenticated", 
    user_id=123, 
    email="user@example.com",
    password="secret123"  # Automatically redacted
)

# Output: user_id=123 email="user@example.com" password="[REDACTED]"
```

### Sentry PII Scrubbing

**Configuration:**
```python
# app/core/sentry.py
sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    send_default_pii=False,  # CRITICAL: Always False
    before_send=scrub_sensitive_data,
)

def scrub_sensitive_data(event, hint):
    # Remove sensitive headers
    if 'request' in event:
        headers = event['request'].get('headers', {})
        headers.pop('Authorization', None)
        headers.pop('Cookie', None)
    
    # Remove sensitive POST data
    if 'request' in event and 'data' in event['request']:
        data = event['request']['data']
        for field in ['password', 'pin', 'token']:
            data.pop(field, None)
    
    return event
```

### API Response Security

**Never return sensitive data:**
```python
# ✅ CORRECT
@router.post("/vaults")
def create_vault(request: CreateVaultRequest):
    vault = use_case.execute(...)
    return {
        "vault_id": vault.id,
        "status": vault.status,
        # PIN hash NOT included
    }

# ❌ WRONG
@router.post("/vaults")
def create_vault(request: CreateVaultRequest):
    vault = use_case.execute(...)
    return {
        "vault_id": vault.id,
        "pin_hash": vault.pin_hash,  # ❌ Never expose hash
    }
```

---

## Secrets Management

### Secret Key Generation

**Generate strong secret key:**
```bash
openssl rand -hex 32
```

**Requirements:**
- Minimum 256 bits (32 bytes hex = 64 characters)
- Cryptographically random
- Unique per environment
- Never committed to version control

### Environment Variables

**Development:**
```bash
# .env (gitignored)
SECRET_KEY=dev-only-secret-not-for-production
DATABASE_URL=postgresql://localhost/smartvault
```

**Production:**
```bash
# Use secrets management service
SECRET_KEY=<from-AWS-Secrets-Manager>
DATABASE_URL=<from-environment-config>
```

### Secrets Rotation

**Secret Key Rotation:**
1. Generate new secret key
2. Update environment variable
3. Restart application
4. All existing JWT tokens will be invalidated
5. Users must re-authenticate

**Database Password Rotation:**
1. Create new database user
2. Grant same permissions
3. Update `DATABASE_URL`
4. Restart application
5. Revoke old user after verification

---

## Rate Limiting

### Rate Limit Configuration

| Endpoint | Limit | Window | Purpose |
|----------|-------|--------|---------|
| **OTP Request** | 3 requests | 1 minute | Prevent OTP spam |
| **Login** | 5 requests | 1 minute | Prevent brute force |
| **PIN Unlock** | 5 attempts | 15 minutes | Prevent PIN guessing |
| **API General** | 100 requests | 1 minute | Prevent abuse |

### Implementation

**PIN unlock rate limiting:**
```python
# app/application/use_cases/unlock_vault_with_pin.py
class UnlockVaultWithPIN:
    def execute(self, vault_id: str, user_id: int, pin: str):
        # Check lockout
        if self.rate_limiter.is_locked(f"pin_unlock:{vault_id}"):
            raise VaultLockedOutException()
        
        # Verify PIN
        if not vault.verify_pin(pin):
            # Record failure
            self.rate_limiter.record_failure(f"pin_unlock:{vault_id}")
            
            # Track metric
            metrics.pin_unlock_failed(vault_id=vault_id)
            
            raise InvalidPINException()
        
        # Reset on success
        self.rate_limiter.reset(f"pin_unlock:{vault_id}")
```

**Redis implementation:**
```python
# app/infrastructure/cache/rate_limiter.py
class RedisRateLimiter:
    def record_failure(self, key: str):
        attempts = self.redis.incr(f"attempts:{key}")
        
        if attempts == 1:
            self.redis.expire(f"attempts:{key}", 900)  # 15 minutes
        
        if attempts >= 5:
            self.redis.setex(f"lockout:{key}", 900, "1")
    
    def is_locked(self, key: str) -> bool:
        return self.redis.exists(f"lockout:{key}")
    
    def reset(self, key: str):
        self.redis.delete(f"attempts:{key}")
        self.redis.delete(f"lockout:{key}")
```

---

## Security Testing

### Testing Checklist

**Authentication:**
- [ ] Password hashing works correctly
- [ ] JWT tokens are validated
- [ ] Expired tokens are rejected
- [ ] Invalid tokens are rejected
- [ ] Token signature verification works

**Authorization:**
- [ ] Users cannot access other users' resources
- [ ] Role checks are enforced
- [ ] Permission checks prevent unauthorized actions

**PIN Security:**
- [ ] PINs are hashed (never plaintext)
- [ ] PIN verification uses constant-time comparison
- [ ] Rate limiting prevents brute force
- [ ] Lockout mechanism works correctly

**Input Validation:**
- [ ] SQL injection prevented (using ORM)
- [ ] XSS prevented (Pydantic validation)
- [ ] Path traversal prevented
- [ ] Command injection prevented

**Sensitive Data:**
- [ ] No passwords in logs
- [ ] No PINs in logs
- [ ] No tokens in logs
- [ ] Sentry scrubs PII

### Automated Security Tests

```python
# app/tests/security/test_pin_timing_attack.py
def test_pin_verification_timing():
    """Verify PIN verification is constant-time."""
    import time
    
    pin_hash = pbkdf2_sha256.hash("1234")
    
    # Measure time for correct PIN
    start = time.time()
    pbkdf2_sha256.verify("1234", pin_hash)
    correct_time = time.time() - start
    
    # Measure time for incorrect PIN
    start = time.time()
    pbkdf2_sha256.verify("9999", pin_hash)
    incorrect_time = time.time() - start
    
    # Times should be similar (within 10ms)
    assert abs(correct_time - incorrect_time) < 0.01
```

---

## Vulnerability Reporting

### Reporting Process

**If you discover a security vulnerability:**

1. **DO NOT** open a public GitHub issue
2. **DO NOT** disclose publicly until patched
3. **DO** email security@smartvault.com with:
   - Description of vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if known)

**Response Timeline:**
- **24 hours:** Acknowledgment
- **7 days:** Initial assessment
- **30 days:** Patch or mitigation plan
- **90 days:** Public disclosure (coordinated)

### Vulnerability Severity

| Severity | Examples | Response Time |
|----------|----------|---------------|
| **Critical** | RCE, authentication bypass, PIN leak | 24 hours |
| **High** | Authorization bypass, SQL injection | 7 days |
| **Medium** | XSS, CSRF, information disclosure | 30 days |
| **Low** | Missing headers, weak cipher suites | 90 days |

---

## Security Checklist

### Development

- [ ] Never commit secrets to version control
- [ ] Use `.env` files for local secrets (gitignored)
- [ ] Validate all user inputs
- [ ] Use parameterized queries (ORM prevents SQL injection)
- [ ] Never log passwords, PINs, or tokens
- [ ] Use HTTPS in production
- [ ] Set secure cookie flags (if using cookies)

### Deployment

- [ ] `SENTRY_SEND_DEFAULT_PII=false`
- [ ] Strong `SECRET_KEY` generated
- [ ] Database credentials are strong
- [ ] Redis password set (if exposed)
- [ ] HTTPS/TLS enabled
- [ ] Rate limiting enabled
- [ ] Firewall configured
- [ ] Security headers configured

### Monitoring

- [ ] Sentry alerts configured
- [ ] Unusual activity alerts (lockouts, auth failures)
- [ ] Log aggregation enabled
- [ ] Audit logs retained
- [ ] Access logs reviewed regularly

---

## Security Resources

- **OWASP Top 10:** https://owasp.org/www-project-top-ten/
- **OWASP Cheat Sheets:** https://cheatsheetseries.owasp.org/
- **Python Security:** https://python.readthedocs.io/en/latest/library/security_warnings.html
- **FastAPI Security:** https://fastapi.tiangolo.com/tutorial/security/

---

## Related Documentation

- [Architecture](ARCHITECTURE.md) — System design
- [Observability](OBSERVABILITY.md) — Monitoring and logging
- [Deployment](DEPLOYMENT.md) — Production deployment