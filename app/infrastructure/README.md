# Infrastructure Layer Documentation

Quick reference for `app/infrastructure` components and patterns.

---

## Overview

The **infrastructure layer** adapts external systems and services to the domain's needs. It implements the **ports** (interfaces) defined in the application layer.

**Key Principle:** The infrastructure layer **depends on** the domain and application layers, but they **don't depend on** infrastructure.

```
Domain Layer (pure business logic)
  ↑ defines interfaces
Application Layer (use cases, ports)
  ↑ implements interfaces
Infrastructure Layer (adapters, external services)
```

---

## Directory Structure

```
app/infrastructure/
├── db/              # Database adapters (SQLAlchemy)
├── cache/           # Redis client and rate limiting
├── security/        # Cryptographic operations
├── messaging/       # WebSocket manager
├── monitoring/      # Prometheus metrics, helpers
├── biometrics/      # Face recognition service
├── notifications/   # Email service
└── services/        # Other external integrations
```

---

## Database (`db/`)

### Purpose
Map domain models to database tables and provide CRUD operations.

### Key Files

**`session.py`** — Database connection and session management
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine)
```

**`models.py`** — SQLAlchemy database models
```python
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class DBUser(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
```

**Repository adapters:**
- `user_repository.py` — Implements `UserRepository` port
- `vault_repository.py` — Implements `VaultRepository` port
- `access_log_repository.py` — Implements `AccessLogRepository` port

### Pattern: Repository Adapter

**1. Application layer defines port (interface):**
```python
# app/application/ports/user_repository.py
from abc import ABC, abstractmethod
from app.domain.models.user import User

class UserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None:
        pass
    
    @abstractmethod
    def get_by_email(self, email: str) -> User | None:
        pass
    
    @abstractmethod
    def save(self, user: User) -> User:
        pass
```

**2. Infrastructure implements adapter:**
```python
# app/infrastructure/db/user_repository.py
from app.application.ports.user_repository import UserRepository
from app.domain.models.user import User
from app.infrastructure.db.models import DBUser

class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session):
        self.session = session
    
    def get_by_id(self, user_id: int) -> User | None:
        db_user = self.session.query(DBUser).filter_by(id=user_id).first()
        if not db_user:
            return None
        
        # Map database model → domain model
        return User(
            user_id=db_user.id,
            email=db_user.email,
            password_hash=db_user.password_hash,
        )
    
    def save(self, user: User) -> User:
        db_user = self.session.query(DBUser).filter_by(id=user.id).first()
        
        if not db_user:
            # Create new
            db_user = DBUser(
                email=user.email,
                password_hash=user.password_hash,
            )
            self.session.add(db_user)
        else:
            # Update existing
            db_user.email = user.email
            db_user.password_hash = user.password_hash
        
        self.session.commit()
        self.session.refresh(db_user)
        
        # Map back to domain model
        user.id = db_user.id
        return user
```

**Why This Pattern:**
- Domain models stay pure (no SQLAlchemy imports)
- Database can be swapped (e.g., PostgreSQL → MongoDB)
- Easy to test with in-memory repositories

---

## Cache (`cache/`)

### Purpose
Provide Redis-based caching and rate limiting.

### Key Files

**`redis_client.py`** — Redis connection management
```python
import redis
from app.core.settings import settings

redis_client = redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
    max_connections=50,
)

async def redis_startup():
    # Test connection
    redis_client.ping()

async def redis_shutdown():
    redis_client.close()
```

**`rate_limiter.py`** — Rate limiting implementation
```python
class RedisRateLimiter:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def check_rate_limit(self, key: str, max_attempts: int, window: int):
        """
        Check rate limit.
        
        Args:
            key: Unique identifier (e.g., "login:user@example.com")
            max_attempts: Maximum attempts allowed
            window: Time window in seconds
        
        Raises:
            RateLimitExceededException: If limit exceeded
        """
        attempts = self.redis.incr(f"attempts:{key}")
        
        if attempts == 1:
            self.redis.expire(f"attempts:{key}", window)
        
        if attempts > max_attempts:
            raise RateLimitExceededException()
    
    def is_locked(self, key: str) -> bool:
        return self.redis.exists(f"lockout:{key}")
    
    def reset(self, key: str):
        self.redis.delete(f"attempts:{key}")
        self.redis.delete(f"lockout:{key}")
```

**Usage in use case:**
```python
# app/application/use_cases/unlock_vault_with_pin.py
class UnlockVaultWithPIN:
    def __init__(self, ..., rate_limiter: RateLimiter):
        self.rate_limiter = rate_limiter
    
    def execute(self, vault_id: str, user_id: int, pin: str):
        # Check if vault is locked out
        if self.rate_limiter.is_locked(f"pin_unlock:{vault_id}"):
            raise VaultLockedOutException()
        
        # Verify PIN
        if not vault.verify_pin(pin):
            self.rate_limiter.record_failure(f"pin_unlock:{vault_id}")
            raise InvalidPINException()
        
        # Reset on success
        self.rate_limiter.reset(f"pin_unlock:{vault_id}")
```

---

## Security (`security/`)

### Purpose
Provide cryptographic operations (password hashing, PIN hashing).

### Key Files

**`password_hasher.py`** — PBKDF2 password hashing
```python
from passlib.hash import pbkdf2_sha256

class PasswordHasher:
    @staticmethod
    def hash(password: str) -> str:
        return pbkdf2_sha256.hash(password)
    
    @staticmethod
    def verify(password: str, hash: str) -> bool:
        return pbkdf2_sha256.verify(password, hash)
```

**Usage in domain:**
```python
# app/domain/value_objects/pin.py
from app.infrastructure.security.password_hasher import PasswordHasher

@dataclass(frozen=True)
class PIN:
    value: str
    
    def hash(self) -> str:
        return PasswordHasher.hash(self.value)
    
    def verify(self, hash: str) -> bool:
        return PasswordHasher.verify(self.value, hash)
```

**Why in Infrastructure:**
- Hashing is an external dependency (passlib)
- Could be swapped (e.g., bcrypt, argon2)
- Domain shouldn't know about hashing libraries

---

## Messaging (`messaging/`)

### Purpose
Manage WebSocket connections for real-time communication.

### Key Files

**`websocket_manager.py`** — WebSocket connection pool
```python
from fastapi import WebSocket

class WebSocketManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket
    
    def disconnect(self, client_id: str):
        self.active_connections.pop(client_id, None)
    
    async def send_message(self, client_id: str, message: dict):
        websocket = self.active_connections.get(client_id)
        if websocket:
            await websocket.send_json(message)
    
    async def broadcast(self, message: dict):
        for websocket in self.active_connections.values():
            await websocket.send_json(message)

manager = WebSocketManager()
```

**Usage in API:**
```python
# app/websocket/handlers.py
from app.infrastructure.messaging.websocket_manager import manager

@app.websocket("/api/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(client_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Handle message
    except WebSocketDisconnect:
        manager.disconnect(client_id)
```

---

## Monitoring (`monitoring/`)

### Purpose
Expose Prometheus metrics and provide metric tracking helpers.

### Key Files

**`metrics.py`** — Prometheus metric definitions
```python
from prometheus_client import Counter, Histogram, Gauge

# HTTP metrics (auto-instrumented)
# Provided by prometheus-fastapi-instrumentator

# Business metrics
vault_unlocks_total = Counter(
    'vault_unlocks_total',
    'Total vault unlock attempts',
    ['vault_id', 'user_id', 'result']
)

vault_unlock_duration = Histogram(
    'vault_unlock_duration_seconds',
    'Time to unlock vault',
    ['vault_id']
)

pin_lockouts_total = Counter(
    'pin_lockouts_total',
    'Total PIN lockout events',
    ['vault_id']
)

def set_app_info(version: str, environment: str):
    """Set application info metric."""
    app_info = Gauge(
        'smartvault_app_info',
        'Application version and environment',
        ['version', 'environment']
    )
    app_info.labels(version=version, environment=environment).set(1)
```

**`helpers.py`** — Metric tracking utilities
```python
from app.infrastructure.monitoring.metrics import vault_unlocks_total
import time

def track_vault_unlock(vault_id: str, user_id: int, result: str):
    """Track vault unlock attempt."""
    vault_unlocks_total.labels(
        vault_id=vault_id,
        user_id=user_id,
        result=result
    ).inc()

def track_unlock_duration(vault_id: str):
    """Context manager to track unlock duration."""
    from contextlib import contextmanager
    
    @contextmanager
    def timer():
        start = time.time()
        yield
        duration = time.time() - start
        vault_unlock_duration.labels(vault_id=vault_id).observe(duration)
    
    return timer()
```

**Usage in use case:**
```python
# app/application/use_cases/unlock_vault_with_pin.py
from app.infrastructure.monitoring.helpers import track_vault_unlock

class UnlockVaultWithPIN:
    def execute(self, vault_id: str, user_id: int, pin: str):
        try:
            # Unlock logic
            vault.unlock(user_id)
            
            # Track success
            track_vault_unlock(vault_id, user_id, "success")
            
        except InvalidPINException:
            # Track failure
            track_vault_unlock(vault_id, user_id, "failure")
            raise
```

---

## Biometrics (`biometrics/`)

### Purpose
Integrate with face recognition service for biometric authentication.

### Key Files

**`face_recognition_service.py`** — Face recognition adapter
```python
import face_recognition

class FaceRecognitionService:
    def enroll_face(self, user_id: int, image_data: bytes) -> str:
        """
        Enroll user's face for biometric authentication.
        
        Returns:
            encoding_id: Unique identifier for face encoding
        """
        # Load image
        image = face_recognition.load_image_file(image_data)
        
        # Generate encoding
        encodings = face_recognition.face_encodings(image)
        if not encodings:
            raise NoFaceDetectedException()
        
        # Store encoding (simplified)
        encoding_id = f"face_{user_id}"
        # In production: store in database or secure storage
        
        return encoding_id
    
    def verify_face(self, encoding_id: str, image_data: bytes) -> bool:
        """Verify face against stored encoding."""
        # Load stored encoding
        stored_encoding = self._get_encoding(encoding_id)
        
        # Load new image
        image = face_recognition.load_image_file(image_data)
        new_encodings = face_recognition.face_encodings(image)
        
        if not new_encodings:
            return False
        
        # Compare
        matches = face_recognition.compare_faces(
            [stored_encoding],
            new_encodings[0],
            tolerance=0.6
        )
        
        return matches[0]
```

---

## Notifications (`notifications/`)

### Purpose
Send email notifications via SMTP.

### Key Files

**`email_service.py`** — Email adapter
```python
import aiosmtplib
from email.message import EmailMessage

class EmailService:
    def __init__(self, smtp_settings):
        self.host = smtp_settings.SMTP_HOST
        self.port = smtp_settings.SMTP_PORT
        self.user = smtp_settings.SMTP_USER
        self.password = smtp_settings.SMTP_PASSWORD
        self.from_email = smtp_settings.SMTP_FROM_EMAIL
    
    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        html_body: str = None
    ):
        """Send email."""
        message = EmailMessage()
        message["From"] = self.from_email
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)
        
        if html_body:
            message.add_alternative(html_body, subtype="html")
        
        await aiosmtplib.send(
            message,
            hostname=self.host,
            port=self.port,
            username=self.user,
            password=self.password,
            use_tls=True,
        )
```

**Usage in use case:**
```python
# app/application/use_cases/send_otp.py
class SendOTPEmail:
    def __init__(self, email_service: EmailService):
        self.email_service = email_service
    
    async def execute(self, user_email: str, otp_code: str):
        await self.email_service.send_email(
            to=user_email,
            subject="Your SmartVault OTP",
            body=f"Your OTP code is: {otp_code}",
        )
```

---

## Adding New Infrastructure

### Example: Add SMS Service

**1. Define port in application layer:**
```python
# app/application/ports/sms_service.py
from abc import ABC, abstractmethod

class SMSService(ABC):
    @abstractmethod
    async def send_sms(self, phone: str, message: str):
        pass
```

**2. Implement adapter in infrastructure:**
```python
# app/infrastructure/notifications/twilio_sms_service.py
from app.application.ports.sms_service import SMSService
from twilio.rest import Client

class TwilioSMSService(SMSService):
    def __init__(self, account_sid: str, auth_token: str, from_number: str):
        self.client = Client(account_sid, auth_token)
        self.from_number = from_number
    
    async def send_sms(self, phone: str, message: str):
        self.client.messages.create(
            to=phone,
            from_=self.from_number,
            body=message
        )
```

**3. Wire in API layer:**
```python
# app/api/deps.py
from app.infrastructure.notifications.twilio_sms_service import TwilioSMSService

def get_sms_service() -> SMSService:
    return TwilioSMSService(
        account_sid=settings.TWILIO_ACCOUNT_SID,
        auth_token=settings.TWILIO_AUTH_TOKEN,
        from_number=settings.TWILIO_FROM_NUMBER,
    )
```

**4. Use in use case:**
```python
# app/application/use_cases/send_otp_sms.py
class SendOTPSMS:
    def __init__(self, sms_service: SMSService):
        self.sms_service = sms_service
    
    async def execute(self, phone: str, otp_code: str):
        await self.sms_service.send_sms(
            phone=phone,
            message=f"Your SmartVault OTP is: {otp_code}"
        )
```

---

## Testing Infrastructure

### In-Memory Adapters

**Create fake implementations for testing:**
```python
# app/tests/fakes/fake_vault_repository.py
from app.application.ports.vault_repository import VaultRepository
from app.domain.models.vault import Vault

class FakeVaultRepository(VaultRepository):
    def __init__(self):
        self.vaults: dict[str, Vault] = {}
    
    def get_by_id(self, vault_id: str) -> Vault | None:
        return self.vaults.get(vault_id)
    
    def save(self, vault: Vault) -> Vault:
        self.vaults[vault.id] = vault
        return vault
```

**Use in tests:**
```python
def test_unlock_vault():
    vault_repo = FakeVaultRepository()  # In-memory, fast
    use_case = UnlockVaultWithPIN(vault_repo, ...)
    
    # Test without database
```

---

## Design Patterns

### Dependency Injection

Infrastructure adapters are **injected** into use cases:

```python
# API layer (wiring)
@router.post("/vaults/{vault_id}/unlock")
def unlock_vault(
    vault_id: str,
    db = Depends(get_db),
):
    # Instantiate use case with concrete implementations
    use_case = UnlockVaultWithPIN(
        vault_repo=SQLAlchemyVaultRepository(db),
        rate_limiter=RedisRateLimiter(),
    )
    
    use_case.execute(vault_id, ...)
```

**Benefits:**
- Swappable implementations
- Easy testing (use fakes)
- Clear dependencies

---

## Common Anti-Patterns

### ❌ Business Logic in Infrastructure

```python
# BAD: Repository contains business logic
class SQLAlchemyVaultRepository:
    def unlock_vault(self, vault_id: str):
        vault = self.get_by_id(vault_id)
        vault.status = "unlocked"  # ❌ Business logic
        self.save(vault)
```

**Fix:** Move logic to domain/use case.

---

### ❌ Infrastructure Imports in Domain

```python
# BAD: Domain imports SQLAlchemy
from sqlalchemy import Column, String  # ❌

class Vault:
    id = Column(String, primary_key=True)  # ❌
```

**Fix:** Keep domain pure, map in repository.

---

## Related Documentation

- [Architecture](../Docs/ARCHITECTURE.md)
- [Contributing](../Docs/CONTRIBUTING.md)
- [Development](../Docs/DEVELOPMENT.md)