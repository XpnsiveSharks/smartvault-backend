# SmartVault Architecture

This document explains SmartVault's **Clean Architecture** implementation, layer responsibilities, dependency rules, and design decisions.

---

## Table of Contents

1. [Architectural Overview](#architectural-overview)
2. [Layer Responsibilities](#layer-responsibilities)
3. [Dependency Rules](#dependency-rules)
4. [Code Organization](#code-organization)
5. [Design Patterns](#design-patterns)
6. [Adding New Features](#adding-new-features)
7. [Common Anti-Patterns](#common-anti-patterns)

---

## Architectural Overview

SmartVault follows **Clean Architecture** (aka Hexagonal Architecture, Ports & Adapters) with four distinct layers:

```
┌──────────────────────────────────────────────────────────────┐
│                      API Layer                               │
│  - FastAPI routers                                           │
│  - HTTP request/response handling                            │
│  - WebSocket handlers                                        │
│  - Dependency injection setup                                │
│  - Middleware (request ID, logging, rate limiting)           │
└───────────────────────────┬──────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────┐
│                   Application Layer                          │
│  - Use cases (orchestration of business workflows)           │
│  - Application services (reusable logic)                     │
│  - Ports (interface definitions)                             │
│  - Metric tracking helpers                                   │
└───────────────────────────┬──────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────┐
│                     Domain Layer                             │
│  - Business entities (User, Vault, AccessLog)                │
│  - Value objects (PIN, VaultStatus, BiometricResult)         │
│  - Domain events (VaultUnlocked, PINLockout, etc.)           │
│  - Business rules and invariants                             │
│  - **NO INFRASTRUCTURE DEPENDENCIES**                        │
└───────────────────────────┬──────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────┐
│                  Infrastructure Layer                        │
│  - Database repositories (SQLAlchemy)                        │
│  - Redis cache client                                        │
│  - External service adapters (email, biometrics)             │
│  - Monitoring (Prometheus metrics, Sentry)                   │
│  - Security (password hashing, PIN validation)               │
└──────────────────────────────────────────────────────────────┘
```

### Core Principle: Dependency Inversion

**The Dependency Rule:**
> Source code dependencies can only point **inward**. Inner layers know nothing about outer layers.

```
Domain Layer
  ↑ knows about
  Application Layer
    ↑ knows about
    Infrastructure Layer
      ↑ knows about
      API Layer
```

**This means:**
- Domain models never import SQLAlchemy, FastAPI, or Redis
- Application use cases never import HTTP request objects
- Infrastructure adapts external systems to domain interfaces

---

## Layer Responsibilities

### 1. Domain Layer (`app/domain/`)

**Purpose:** Pure business logic with zero infrastructure coupling.

**Contains:**
- **Models** (`models/`): Business entities with behavior
  - `User`: User accounts and authentication
  - `Vault`: Vault entity with status and operations
  - `AccessLog`: Audit trail records
  
- **Value Objects** (`value_objects/`): Immutable domain concepts
  - `PIN`: Validated PIN with hashing
  - `VaultStatus`: Vault state (locked/unlocked)
  - `BiometricResult`: Face recognition results
  
- **Domain Events** (`events/`): Significant business occurrences
  - `VaultUnlockedEvent`
  - `PINLockoutEvent`
  - `MemberAddedEvent`

**Rules:**
- ✅ Pure Python (no framework dependencies)
- ✅ Business rules and invariants
- ✅ Rich domain models
- ❌ NO database imports (SQLAlchemy, psycopg)
- ❌ NO HTTP imports (FastAPI, Starlette)
- ❌ NO infrastructure imports (Redis, Sentry)

**Example:**
```python
# ✅ GOOD: Pure domain logic
class Vault:
    def __init__(self, vault_id: str, owner_id: int):
        self.id = vault_id
        self.owner_id = owner_id
        self.status = VaultStatus.LOCKED
        
    def unlock(self, user_id: int) -> VaultUnlockedEvent:
        if self.status == VaultStatus.UNLOCKED:
            raise VaultAlreadyUnlockedException()
        
        self.status = VaultStatus.UNLOCKED
        return VaultUnlockedEvent(vault_id=self.id, user_id=user_id)

# ❌ BAD: Infrastructure in domain
from sqlalchemy import Column, String  # ❌ Never import ORM in domain
```

---

### 2. Application Layer (`app/application/`)

**Purpose:** Orchestrate business workflows without infrastructure details.

**Contains:**
- **Use Cases** (`use_cases/`): Business workflows
  - `UnlockVaultWithPIN`: Unlock vault using PIN
  - `ProvisionVault`: Create new vault
  - `AuthenticateUser`: User login
  
- **Services** (`services/`): Reusable application logic
  - `TokenService`: JWT token operations
  - `AuthorizationService`: Permission checks
  - `LivenessService`: Health monitoring
  
- **Ports** (`ports/`): Interface definitions for infrastructure
  - `UserRepository`: Abstract user storage
  - `VaultRepository`: Abstract vault storage
  - `CachePort`: Abstract caching interface

**Rules:**
- ✅ Orchestrates domain objects
- ✅ Defines ports (interfaces) for infrastructure
- ✅ Calls domain methods
- ✅ Can track metrics (via helpers)
- ❌ NO direct database access
- ❌ NO direct Redis calls
- ❌ NO HTTP request/response objects

**Example:**
```python
# ✅ GOOD: Use case orchestration
class UnlockVaultWithPIN:
    def __init__(
        self,
        vault_repo: VaultRepository,  # Port (interface)
        user_repo: UserRepository,    # Port (interface)
        rate_limiter: RateLimiter,    # Port (interface)
    ):
        self.vault_repo = vault_repo
        self.user_repo = user_repo
        self.rate_limiter = rate_limiter
    
    def execute(self, vault_id: str, user_id: int, pin: str):
        # 1. Check rate limit
        if self.rate_limiter.is_locked(vault_id):
            raise VaultLockedOutException()
        
        # 2. Get domain objects
        vault = self.vault_repo.get_by_id(vault_id)
        user = self.user_repo.get_by_id(user_id)
        
        # 3. Business logic (domain layer)
        if not vault.verify_pin(pin):
            self.rate_limiter.record_failure(vault_id)
            raise InvalidPINException()
        
        # 4. Unlock (domain layer)
        event = vault.unlock(user_id)
        
        # 5. Persist
        self.vault_repo.save(vault)
        
        return event

# ❌ BAD: Direct infrastructure in use case
from app.infrastructure.db.session import get_db  # ❌ Never import concrete infra
from redis import Redis  # ❌ Never import Redis directly
```

---

### 3. Infrastructure Layer (`app/infrastructure/`)

**Purpose:** Adapt external systems to domain interfaces.

**Contains:**
- **Database** (`db/`): SQLAlchemy repositories
  - `SQLAlchemyUserRepository`: Implements `UserRepository` port
  - `SQLAlchemyVaultRepository`: Implements `VaultRepository` port
  
- **Cache** (`cache/`): Redis client
  - `RedisRateLimiter`: Implements rate limiting
  - `RedisClient`: Connection management
  
- **Security** (`security/`): Cryptographic operations
  - `PasswordHasher`: PBKDF2 hashing
  - `PINValidator`: PIN verification
  
- **Monitoring** (`monitoring/`): Observability adapters
  - `MetricsCollector`: Prometheus metrics
  - `MetricTrackingHelpers`: Use case metric decorators
  
- **Messaging** (`messaging/`): Communication
  - `WebSocketManager`: WebSocket connection pool
  
- **Services** (`services/`): External integrations
  - `FaceRecognitionService`: Biometric verification
  - `EmailService`: SMTP integration

**Rules:**
- ✅ Implements ports defined in application layer
- ✅ Maps domain models to database models
- ✅ Handles external service communication
- ✅ Manages connections and sessions
- ❌ NO business logic (delegate to domain)
- ❌ NO use case orchestration

**Example:**
```python
# ✅ GOOD: Repository adapter
class SQLAlchemyVaultRepository(VaultRepository):  # Implements port
    def __init__(self, session: Session):
        self.session = session
    
    def get_by_id(self, vault_id: str) -> Vault:
        # Map database model → domain model
        db_vault = self.session.query(DBVault).filter_by(id=vault_id).first()
        if not db_vault:
            raise VaultNotFoundException()
        
        return Vault(
            vault_id=db_vault.id,
            owner_id=db_vault.owner_id,
            status=VaultStatus(db_vault.status),
        )
    
    def save(self, vault: Vault):
        # Map domain model → database model
        db_vault = self.session.query(DBVault).filter_by(id=vault.id).first()
        db_vault.status = vault.status.value
        self.session.commit()

# ❌ BAD: Business logic in infrastructure
class SQLAlchemyVaultRepository(VaultRepository):
    def unlock_vault(self, vault_id: str):  # ❌ Business logic in repo
        vault = self.get_by_id(vault_id)
        vault.status = "unlocked"  # ❌ Should be in domain
```

---

### 4. API Layer (`app/api/`)

**Purpose:** Translate HTTP to application layer calls.

**Contains:**
- **Routers** (`v1/`): FastAPI endpoint handlers
  - `users.py`: User endpoints
  - `vaults.py`: Vault endpoints
  - `auth.py`: Authentication endpoints
  
- **Dependencies** (`deps/`): Dependency injection
  - `get_db()`: Provides database session
  - `get_current_user()`: Extracts authenticated user
  - `require_admin()`: Authorization checks
  
- **Middleware** (`middleware/`): Request processing
  - `RequestIDMiddleware`: Request correlation
  - Rate limiting middleware (future)

**Rules:**
- ✅ HTTP request/response handling
- ✅ Input validation (Pydantic schemas)
- ✅ Dependency injection
- ✅ Calls use cases from application layer
- ❌ NO business logic
- ❌ NO direct database access
- ❌ NO direct domain model manipulation

**Example:**
```python
# ✅ GOOD: Thin controller
@router.post("/vaults/{vault_id}/unlock")
def unlock_vault(
    vault_id: str,
    request: UnlockRequest,
    user = Depends(get_current_user),
    db = Depends(get_db),
):
    # Instantiate use case with dependencies
    use_case = UnlockVaultWithPIN(
        vault_repo=SQLAlchemyVaultRepository(db),
        user_repo=SQLAlchemyUserRepository(db),
        rate_limiter=RedisRateLimiter(),
    )
    
    # Execute use case
    event = use_case.execute(vault_id, user.id, request.pin)
    
    # Return HTTP response
    return {"status": "unlocked", "event_id": event.id}

# ❌ BAD: Business logic in controller
@router.post("/vaults/{vault_id}/unlock")
def unlock_vault(vault_id: str, pin: str, db = Depends(get_db)):
    vault = db.query(DBVault).filter_by(id=vault_id).first()  # ❌ Direct DB
    if verify_pin(vault.pin_hash, pin):  # ❌ Business logic in controller
        vault.status = "unlocked"
        db.commit()
```

---

## Dependency Rules

### Allowed Dependencies

```
Domain       → None (pure Python)
Application  → Domain
Infrastructure → Domain, Application
API          → Domain, Application, Infrastructure
```

### Forbidden Dependencies

```
Domain       → Application ❌
Domain       → Infrastructure ❌
Domain       → API ❌
Application  → Infrastructure ❌ (only via ports)
Application  → API ❌
```

### How to Enforce

**Use dependency injection:**
```python
# Application layer defines interface (port)
class VaultRepository(ABC):
    @abstractmethod
    def get_by_id(self, vault_id: str) -> Vault:
        pass

# Infrastructure implements adapter
class SQLAlchemyVaultRepository(VaultRepository):
    def get_by_id(self, vault_id: str) -> Vault:
        # Implementation details
        pass

# API layer wires dependencies
use_case = UnlockVaultWithPIN(
    vault_repo=SQLAlchemyVaultRepository(db),  # Concrete implementation
)
```

---

## Code Organization

### Where to Put New Code

| You Want To... | Add To... | Layer |
|----------------|-----------|-------|
| Add business entity | `app/domain/models/` | Domain |
| Add immutable concept | `app/domain/value_objects/` | Domain |
| Add domain event | `app/domain/events/` | Domain |
| Add business workflow | `app/application/use_cases/` | Application |
| Add reusable service | `app/application/services/` | Application |
| Add infrastructure adapter | `app/infrastructure/` | Infrastructure |
| Add HTTP endpoint | `app/api/v1/` | API |
| Add middleware | `app/api/middleware/` | API |
| Add request/response schema | `app/schemas/` | API |
| Add test | `app/tests/<layer>/` | Test |

---

## Design Patterns

### Repository Pattern

**Purpose:** Abstract data persistence from domain logic.

**Implementation:**
1. Define port (interface) in application layer
2. Implement adapter in infrastructure layer
3. Inject concrete implementation at runtime

**Example:**
```python
# 1. Port (application/ports/vault_repository.py)
class VaultRepository(ABC):
    @abstractmethod
    def get_by_id(self, vault_id: str) -> Vault:
        pass

# 2. Adapter (infrastructure/db/vault_repository.py)
class SQLAlchemyVaultRepository(VaultRepository):
    def get_by_id(self, vault_id: str) -> Vault:
        # SQLAlchemy implementation
        pass

# 3. Injection (api/deps.py)
def get_vault_repo(db = Depends(get_db)) -> VaultRepository:
    return SQLAlchemyVaultRepository(db)
```

---

### Value Objects

**Purpose:** Encapsulate validated domain concepts.

**Characteristics:**
- Immutable
- Self-validating
- Compared by value, not identity

**Example:**
```python
@dataclass(frozen=True)
class PIN:
    value: str
    
    def __post_init__(self):
        if not re.match(r'^\d{4,8}$', self.value):
            raise InvalidPINException("PIN must be 4-8 digits")
    
    def hash(self) -> str:
        return pbkdf2_sha256.hash(self.value)
    
    def verify(self, hash: str) -> bool:
        return pbkdf2_sha256.verify(self.value, hash)
```

---

### Domain Events

**Purpose:** Capture significant business occurrences.

**Benefits:**
- Audit trail
- Decoupling
- Extensibility

**Example:**
```python
@dataclass
class VaultUnlockedEvent:
    vault_id: str
    user_id: int
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
# Domain model emits event
class Vault:
    def unlock(self, user_id: int) -> VaultUnlockedEvent:
        self.status = VaultStatus.UNLOCKED
        return VaultUnlockedEvent(vault_id=self.id, user_id=user_id)
```

---

## Adding New Features

### Example: Add "Change PIN" Feature

**1. Domain Layer** — Add business logic
```python
# app/domain/models/vault.py
class Vault:
    def change_pin(self, old_pin: PIN, new_pin: PIN) -> PINChangedEvent:
        if not self.verify_pin(old_pin):
            raise InvalidPINException("Old PIN incorrect")
        
        self.pin_hash = new_pin.hash()
        return PINChangedEvent(vault_id=self.id)
```

**2. Application Layer** — Add use case
```python
# app/application/use_cases/change_vault_pin.py
class ChangeVaultPIN:
    def __init__(self, vault_repo: VaultRepository, rate_limiter: RateLimiter):
        self.vault_repo = vault_repo
        self.rate_limiter = rate_limiter
    
    def execute(self, vault_id: str, user_id: int, old_pin: str, new_pin: str):
        # Rate limiting
        if self.rate_limiter.is_locked(f"change_pin:{vault_id}"):
            raise RateLimitExceededException()
        
        # Get vault
        vault = self.vault_repo.get_by_id(vault_id)
        
        # Business logic
        event = vault.change_pin(PIN(old_pin), PIN(new_pin))
        
        # Persist
        self.vault_repo.save(vault)
        
        return event
```

**3. API Layer** — Add endpoint
```python
# app/api/v1/vaults.py
@router.post("/vaults/{vault_id}/pin")
def change_pin(
    vault_id: str,
    request: ChangePINRequest,
    user = Depends(get_current_user),
    db = Depends(get_db),
):
    use_case = ChangeVaultPIN(
        vault_repo=SQLAlchemyVaultRepository(db),
        rate_limiter=RedisRateLimiter(),
    )
    
    event = use_case.execute(vault_id, user.id, request.old_pin, request.new_pin)
    
    return {"status": "success", "event": event}
```

**4. Test** — Add test coverage
```python
# app/tests/application/test_change_vault_pin.py
def test_change_pin_success():
    vault_repo = InMemoryVaultRepository()
    use_case = ChangeVaultPIN(vault_repo, FakeRateLimiter())
    
    event = use_case.execute("vault-1", 123, "1234", "5678")
    
    assert event.vault_id == "vault-1"
    assert vault_repo.get_by_id("vault-1").verify_pin(PIN("5678"))
```

---

## Common Anti-Patterns

### ❌ Business Logic in Controllers

```python
# BAD
@router.post("/vaults/{vault_id}/unlock")
def unlock(vault_id: str, pin: str, db = Depends(get_db)):
    vault = db.query(DBVault).filter_by(id=vault_id).first()
    if vault.pin_hash == hash_pin(pin):  # Business logic in controller
        vault.status = "unlocked"
        db.commit()
```

**Fix:** Move logic to use case.

---

### ❌ Infrastructure in Domain

```python
# BAD
from sqlalchemy import Column, String  # Infrastructure import in domain

class Vault:
    id = Column(String, primary_key=True)  # SQLAlchemy in domain model
```

**Fix:** Keep domain pure, map in repository.

---

### ❌ Direct Database Access in Use Cases

```python
# BAD
class UnlockVaultWithPIN:
    def execute(self, vault_id: str):
        vault = db.query(DBVault).filter_by(id=vault_id).first()  # Direct DB
```

**Fix:** Use repository port.

---

### ❌ God Objects

```python
# BAD
class VaultService:  # Does everything
    def create_vault(self): ...
    def unlock_vault(self): ...
    def add_member(self): ...
    def remove_member(self): ...
    def send_notification(self): ...
    def log_activity(self): ...
```

**Fix:** Split into focused use cases.

---

## Summary

SmartVault's architecture prioritizes:
- **Separation of concerns** — Each layer has clear responsibilities
- **Testability** — Pure domain logic, in-memory repositories
- **Maintainability** — Changes are localized to appropriate layers
- **Flexibility** — Infrastructure can be swapped without changing business logic

**Key Principle:**
> Business logic lives in the domain. Everything else adapts to it.

**Related Documentation:**
- [Observability](OBSERVABILITY.md) — Monitoring and logging
- [Development](DEVELOPMENT.md) — Development workflow
- [Contributing](CONTRIBUTING.md) — Contribution guidelines