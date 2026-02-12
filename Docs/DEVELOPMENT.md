# Development Guide

This document provides a comprehensive guide to developing SmartVault locally, including environment setup, workflows, debugging, and best practices.

---

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [IDE Configuration](#ide-configuration)
3. [Development Workflow](#development-workflow)
4. [Debugging](#debugging)
5. [Testing Patterns](#testing-patterns)
6. [Code Quality](#code-quality)
7. [Database Development](#database-development)
8. [Development Best Practices](#development-best-practices)

---

## Development Environment Setup

### Prerequisites

**Required:**
- Docker Desktop (Windows/Mac) or Docker Engine (Linux) — version 20.10+
- Docker Compose — version 2.0+
- Git — version 2.30+
- Text editor or IDE (VSCode, PyCharm, etc.)

**Recommended:**
- Make (for convenience commands)
- `curl` or Postman (for API testing)
- Redis CLI (for cache inspection)
- PostgreSQL client (for database inspection)

### Initial Setup

**1. Clone repository:**
```bash
git clone <repository-url>
cd smartvault-backend
```

**2. Create environment file:**
```bash
cp .env.example .env
```

**3. Generate secrets:**
```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Update .env
nano .env
# Set SECRET_KEY=<generated-key>
```

**4. Start services:**
```bash
make dev
```

**5. Verify setup:**
```bash
# Check all services are running
docker-compose ps

# Test API
curl http://localhost:8000/api

# Run tests
make test
```

### Access URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| **API** | http://localhost:8000 | N/A |
| **API Docs** | http://localhost:8000/docs | N/A |
| **Grafana** | http://localhost:3000 | admin / admin |
| **Prometheus** | http://localhost:9090 | N/A |
| **PostgreSQL** | localhost:5432 | postgres / postgres |
| **Redis** | localhost:6379 | No password |

---

## IDE Configuration

### Visual Studio Code

**Recommended Extensions:**
- **Python** (ms-python.python)
- **Pylance** (ms-python.vscode-pylance)
- **Docker** (ms-azuretools.vscode-docker)
- **SQLite Viewer** (qwtel.sqlite-viewer)
- **GitLens** (eamodio.gitlens)
- **Better Comments** (aaron-bond.better-comments)
- **REST Client** (humao.rest-client)

**Settings (`.vscode/settings.json`):**
```json
{
  "python.defaultInterpreterPath": "/usr/local/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length", "100"],
  "editor.formatOnSave": true,
  "editor.rulers": [100],
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "**/.pytest_cache": true
  }
}
```

**Tasks (`.vscode/tasks.json`):**
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Run Tests",
      "type": "shell",
      "command": "make test",
      "group": "test"
    },
    {
      "label": "Start Dev",
      "type": "shell",
      "command": "make dev",
      "group": "build"
    }
  ]
}
```

---

### PyCharm

**Project Setup:**
1. Open project directory
2. Configure Python interpreter:
   - Settings → Project → Python Interpreter
   - Add → Docker Compose
   - Service: `api`
3. Configure Docker:
   - Settings → Build, Execution, Deployment → Docker
   - Connect to Docker daemon

**Run Configurations:**

**API Server:**
- Type: Docker Compose
- Service: api
- Command: `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`

**Tests:**
- Type: Python tests → pytest
- Target: `app/tests`
- Python interpreter: Docker Compose (api)

---

## Development Workflow

### Daily Workflow

**1. Sync with upstream:**
```bash
git checkout dev
git pull origin dev
```

**2. Create feature branch:**
```bash
git checkout -b feature/add-biometric-unlock
```

**3. Start services:**
```bash
make dev
```

**4. Develop iteratively:**
```bash
# Make code changes

# Run tests frequently
make test

# Check logs
make logs

# Test manually
curl http://localhost:8000/api/v1/health
```

**5. Commit changes:**
```bash
git add .
git commit -m "feat(auth): add biometric unlock support"
```

**6. Push and open PR:**
```bash
git push origin feature/add-biometric-unlock
# Open pull request on GitHub
```

---

### Hot Reload

**FastAPI automatically reloads on code changes:**
```bash
# Make changes to Python files
# Server reloads automatically
# Check logs for reload confirmation
make logs
```

**No reload for:**
- Environment variable changes (restart required)
- Database migrations (run `make migrate`)
- Dependency changes (rebuild: `docker-compose up --build`)

---

### Running Individual Services

```bash
# Start only API + dependencies
docker-compose up api

# Start only database
docker-compose up postgres

# Start without observability stack
docker-compose up api postgres redis
```

---

## Debugging

### Print Debugging

**Using structured logging:**
```python
from app.core.logging import get_logger

logger = get_logger(__name__)

def unlock_vault(vault_id: str):
    logger.debug("unlock_started", vault_id=vault_id)
    
    vault = vault_repo.get_by_id(vault_id)
    logger.debug("vault_retrieved", vault_id=vault_id, status=vault.status)
    
    # ... rest of logic
    
    logger.info("unlock_completed", vault_id=vault_id)
```

**View logs:**
```bash
make logs
```

---

### Interactive Debugging (pdb)

**Insert breakpoint:**
```python
def unlock_vault(vault_id: str):
    import pdb; pdb.set_trace()  # Breakpoint
    vault = vault_repo.get_by_id(vault_id)
```

**Attach to container:**
```bash
docker attach smartvault-api
```

**PDB Commands:**
- `n` — Next line
- `s` — Step into function
- `c` — Continue execution
- `p variable` — Print variable
- `q` — Quit debugger

---

### VSCode Remote Debugging

**1. Install `debugpy` in container:**
```dockerfile
RUN pip install debugpy
```

**2. Modify startup command:**
```python
# app/main.py
if __name__ == "__main__":
    import debugpy
    debugpy.listen(("0.0.0.0", 5678))
    print("Waiting for debugger attach...")
    debugpy.wait_for_client()
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

**3. VSCode launch config (`.vscode/launch.json`):**
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Remote Attach",
      "type": "python",
      "request": "attach",
      "connect": {
        "host": "localhost",
        "port": 5678
      },
      "pathMappings": [
        {
          "localRoot": "${workspaceFolder}",
          "remoteRoot": "/app"
        }
      ]
    }
  ]
}
```

**4. Set breakpoints and attach:**
- Set breakpoints in VSCode
- Run → Start Debugging

---

### Database Inspection

**PostgreSQL shell:**
```bash
make psql

# List tables
\dt

# Describe table
\d users

# Query data
SELECT * FROM users;

# Check migrations
SELECT * FROM alembic_version;
```

**Using GUI client:**
- **DBeaver** (free, cross-platform)
- **TablePlus** (Mac)
- **pgAdmin** (web-based)

**Connection details:**
- Host: `localhost`
- Port: `5432`
- Database: `smartvault`
- User: `postgres`
- Password: `postgres`

---

### Redis Inspection

**Redis CLI:**
```bash
make redis

# List all keys
KEYS *

# Get value
GET attempts:pin_unlock:vault-123

# Check TTL
TTL attempts:pin_unlock:vault-123

# Flush database (⚠️ DEV ONLY)
FLUSHDB
```

---

## Testing Patterns

### Test Organization

```
app/tests/
├── api/              # Integration tests (HTTP endpoints)
├── application/      # Use case unit tests
├── domain/           # Domain model tests
├── infrastructure/   # Infrastructure adapter tests
├── fakes/            # In-memory test doubles
└── conftest.py       # Shared fixtures
```

---

### Writing Unit Tests

**Domain model test:**
```python
# app/tests/domain/test_vault.py
from app.domain.models.vault import Vault
from app.domain.value_objects.vault_status import VaultStatus

def test_unlock_vault():
    vault = Vault(vault_id="vault-1", owner_id=123)
    
    event = vault.unlock(user_id=123)
    
    assert vault.status == VaultStatus.UNLOCKED
    assert event.vault_id == "vault-1"
    assert event.user_id == 123
```

**Use case test:**
```python
# app/tests/application/test_unlock_vault.py
from app.application.use_cases.unlock_vault_with_pin import UnlockVaultWithPIN
from app.tests.fakes.fake_vault_repository import FakeVaultRepository
from app.tests.fakes.fake_rate_limiter import FakeRateLimiter

def test_unlock_with_valid_pin():
    # Arrange
    vault_repo = FakeVaultRepository()
    rate_limiter = FakeRateLimiter()
    use_case = UnlockVaultWithPIN(vault_repo, rate_limiter)
    
    # Act
    event = use_case.execute("vault-1", 123, "1234")
    
    # Assert
    assert event.vault_id == "vault-1"
    assert vault_repo.get_by_id("vault-1").status == VaultStatus.UNLOCKED
```

---

### Writing Integration Tests

**API endpoint test:**
```python
# app/tests/api/test_unlock_endpoint.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_unlock_vault_success(test_user, test_vault):
    # Login
    response = client.post("/api/v1/auth/login", json={
        "email": test_user.email,
        "password": "password123"
    })
    token = response.json()["access_token"]
    
    # Unlock vault
    response = client.post(
        f"/api/v1/vaults/{test_vault.id}/unlock",
        json={"pin": "1234"},
        headers={"Authorization": f"Bearer {token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "unlocked"
```

---

### Test Fixtures

**Shared fixtures (`conftest.py`):**
```python
import pytest
from app.tests.fakes.fake_vault_repository import FakeVaultRepository

@pytest.fixture
def vault_repo():
    return FakeVaultRepository()

@pytest.fixture
def test_user(db):
    user = User(email="test@example.com")
    db.add(user)
    db.commit()
    return user

@pytest.fixture
def test_vault(db, test_user):
    vault = Vault(owner_id=test_user.id)
    db.add(vault)
    db.commit()
    return vault
```

---

### Running Tests

```bash
# All tests
make test

# Verbose output
make test-vv

# Specific layer
make test-api      # API tests only
make test-app      # Application tests only

# Single file
docker-compose exec api pytest app/tests/api/test_unlock.py

# Single test
docker-compose exec api pytest app/tests/api/test_unlock.py::test_unlock_success -v

# With coverage
docker-compose exec api pytest --cov=app --cov-report=html

# Stop on first failure
docker-compose exec api pytest -x

# Show print statements
docker-compose exec api pytest -s
```

---

### Test Coverage

**Generate coverage report:**
```bash
docker-compose exec api pytest --cov=app --cov-report=html

# Open in browser
open htmlcov/index.html
```

**Coverage requirements:**
- Overall: 80%+
- Domain layer: 90%+
- Application layer: 85%+
- Critical paths: 100%

---

## Code Quality

### Linting (if configured)

```bash
# Flake8
docker-compose exec api flake8 app/

# Pylint
docker-compose exec api pylint app/
```

---

### Formatting (if configured)

```bash
# Black
docker-compose exec api black app/

# isort (import sorting)
docker-compose exec api isort app/
```

---

### Type Checking (if configured)

```bash
# mypy
docker-compose exec api mypy app/
```

---

## Database Development

### Creating Migrations

**1. Modify domain models:**
```python
# app/domain/models/vault.py
class Vault:
    def __init__(self, ..., description: str = ""):
        self.description = description
```

**2. Update database models:**
```python
# app/infrastructure/db/models.py
class DBVault(Base):
    __tablename__ = "vaults"
    
    description = Column(String, nullable=True)
```

**3. Generate migration:**
```bash
make migration msg="add vault description field"
```

**4. Review migration:**
```python
# app/alembic/versions/xxx_add_vault_description_field.py
def upgrade():
    op.add_column('vaults', sa.Column('description', sa.String(), nullable=True))

def downgrade():
    op.drop_column('vaults', 'description')
```

**5. Test migration:**
```bash
# Apply
make migrate

# Rollback
make rollback

# Re-apply
make migrate
```

---

### Seeding Test Data

**Create seed script:**
```python
# scripts/seed_data.py
from app.infrastructure.db.session import SessionLocal
from app.domain.models.user import User
from app.domain.models.vault import Vault

def seed():
    db = SessionLocal()
    
    # Create test user
    user = User(email="test@example.com")
    db.add(user)
    db.commit()
    
    # Create test vault
    vault = Vault(owner_id=user.id, vault_uuid="test-vault-1")
    db.add(vault)
    db.commit()
    
    print(f"Created user: {user.id}")
    print(f"Created vault: {vault.id}")

if __name__ == "__main__":
    seed()
```

**Run seed:**
```bash
docker-compose exec api python scripts/seed_data.py
```

---

### Database Reset (DEV ONLY)

```bash
# ⚠️ Deletes all data
make db-reset

# Manually:
make psql
DROP SCHEMA public CASCADE;
CREATE SCHEMA public;
\q

make migrate
```

---

## Development Best Practices

### Clean Architecture

**Follow layer boundaries:**
```python
# ✅ CORRECT: Domain is pure
class Vault:
    def unlock(self, user_id: int):
        self.status = VaultStatus.UNLOCKED
        return VaultUnlockedEvent(...)

# ❌ WRONG: Domain imports infrastructure
from app.infrastructure.db.session import Session  # ❌

class Vault:
    def save(self):
        db.commit()  # ❌ Infrastructure in domain
```

---

### Error Handling

**Use domain exceptions:**
```python
# app/domain/exceptions.py
class VaultNotFoundException(Exception):
    pass

# Usage
def get_vault(vault_id: str):
    vault = vault_repo.get_by_id(vault_id)
    if not vault:
        raise VaultNotFoundException(f"Vault {vault_id} not found")
    return vault
```

**Handle at API layer:**
```python
# app/api/v1/vaults.py
@router.get("/vaults/{vault_id}")
def get_vault(vault_id: str):
    try:
        use_case.execute(vault_id)
    except VaultNotFoundException:
        raise HTTPException(status_code=404, detail="Vault not found")
```

---

### Logging

**Use structured logging:**
```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# ✅ CORRECT: Structured
logger.info("vault_unlocked", vault_id=vault.id, user_id=user.id)

# ❌ WRONG: String formatting
logger.info(f"Vault {vault.id} unlocked by user {user.id}")
```

**Never log sensitive data:**
```python
# ❌ NEVER
logger.debug("pin_verified", pin=pin_value)  # ❌❌❌

# ✅ CORRECT
logger.info("pin_verified", vault_id=vault_id, result="success")
```

---

### Security

**Always validate input:**
```python
# ✅ CORRECT: Pydantic validation
class UnlockRequest(BaseModel):
    pin: str = Field(..., min_length=4, max_length=8, pattern=r"^\d+$")

# ❌ WRONG: No validation
def unlock_vault(pin: str):
    # What if pin is "'; DROP TABLE users; --" ?
```

**Use parameterized queries:**
```python
# ✅ CORRECT: ORM (safe)
user = db.query(User).filter_by(email=email).first()

# ❌ WRONG: String concatenation (SQL injection)
db.execute(f"SELECT * FROM users WHERE email = '{email}'")
```

---

### Testing

**Test one thing at a time:**
```python
# ✅ CORRECT: Focused test
def test_unlock_with_invalid_pin():
    use_case = UnlockVaultWithPIN(...)
    
    with pytest.raises(InvalidPINException):
        use_case.execute("vault-1", 123, "9999")

# ❌ WRONG: Testing multiple things
def test_unlock_flow():
    # Creates user
    # Creates vault
    # Sets PIN
    # Unlocks
    # Checks status
    # ... (too much in one test)
```

---

### Git Commits

**Make atomic commits:**
```bash
# ✅ CORRECT: One logical change
git commit -m "feat(vault): add vault description field"

# ❌ WRONG: Multiple unrelated changes
git commit -m "feat(vault): add description, fix PIN bug, update deps"
```

**Use conventional commits:**
```bash
feat(scope): add new feature
fix(scope): fix bug
refactor(scope): refactor code
docs(scope): update documentation
test(scope): add tests
chore(scope): maintenance tasks
```

---

## Related Documentation

- [Contributing Guidelines](CONTRIBUTING.md)
- [Architecture](ARCHITECTURE.md)
- [Testing Guide](test.md)
- [Troubleshooting](TROUBLESHOOTING.md)