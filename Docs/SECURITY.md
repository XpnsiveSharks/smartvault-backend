# Contributing to SmartVault

Thank you for considering contributing to SmartVault! This document provides guidelines and standards for contributing code, documentation, and other improvements.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Development Workflow](#development-workflow)
3. [Branch Naming Conventions](#branch-naming-conventions)
4. [Commit Message Standards](#commit-message-standards)
5. [Pull Request Process](#pull-request-process)
6. [Code Standards](#code-standards)
7. [Testing Requirements](#testing-requirements)
8. [Code Review Checklist](#code-review-checklist)
9. [Documentation Requirements](#documentation-requirements)

---

## Getting Started

### Prerequisites

Before contributing, ensure you have:
- Docker and Docker Compose installed
- Git configured with your name and email
- Familiarity with Python, FastAPI, and SQLAlchemy
- Understanding of Clean Architecture principles (see [`ARCHITECTURE.md`](ARCHITECTURE.md))

### First-Time Setup

**1. Fork the repository**
```bash
# On GitHub, click "Fork" button
```

**2. Clone your fork**
```bash
git clone https://github.com/YOUR_USERNAME/smartvault-backend.git
cd smartvault-backend
```

**3. Add upstream remote**
```bash
git remote add upstream https://github.com/ORIGINAL_OWNER/smartvault-backend.git
```

**4. Set up development environment**
```bash
cp .env.example .env
# Edit .env and set SECRET_KEY (run: openssl rand -hex 32)
make dev
```

**5. Verify setup**
```bash
make test
curl http://localhost:8000/api/v1/health
```

---

## Development Workflow

### Standard Workflow

**1. Sync with upstream**
```bash
git checkout dev
git fetch upstream
git merge upstream/dev
git push origin dev
```

**2. Create feature branch**
```bash
git checkout -b feature/add-vault-sharing
```

**3. Make changes**
```bash
# Write code, tests, documentation
make test  # Run tests frequently
```

**4. Commit changes**
```bash
git add .
git commit -m "feat(vault): add vault sharing with members"
```

**5. Push to your fork**
```bash
git push origin feature/add-vault-sharing
```

**6. Open pull request**
- Go to GitHub
- Click "Compare & pull request"
- Fill out PR template
- Link related issues

**7. Address review feedback**
```bash
# Make changes
git add .
git commit -m "refactor: address code review feedback"
git push origin feature/add-vault-sharing
```

---

## Branch Naming Conventions

Use descriptive branch names with the following prefixes:

### Branch Types

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feature/` | New feature development | `feature/biometric-enrollment` |
| `fix/` | Bug fixes | `fix/pin-validation-error` |
| `refactor/` | Code refactoring (no behavior change) | `refactor/vault-repository-cleanup` |
| `docs/` | Documentation updates | `docs/add-deployment-guide` |
| `test/` | Test additions or improvements | `test/add-unlock-edge-cases` |
| `chore/` | Maintenance tasks | `chore/update-dependencies` |
| `perf/` | Performance improvements | `perf/optimize-vault-queries` |
| `security/` | Security fixes | `security/fix-pin-timing-attack` |

### Branch Naming Rules

- Use lowercase letters
- Use hyphens to separate words
- Be descriptive but concise
- Include issue number if applicable

**Examples:**
```bash
feature/vault-sharing-with-permissions
fix/pin-lockout-race-condition
refactor/split-user-repository
docs/update-observability-guide
test/add-membership-integration-tests
chore/upgrade-sqlalchemy-to-2.1
```

---

## Commit Message Standards

We follow **Conventional Commits** for clear, scannable history.

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Type

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `refactor` | Code change with no behavior change |
| `docs` | Documentation changes |
| `test` | Test additions or updates |
| `chore` | Maintenance (dependencies, configs) |
| `perf` | Performance improvements |
| `style` | Code style changes (formatting) |
| `ci` | CI/CD changes |
| `revert` | Revert previous commit |

### Scope

Optional but recommended. Indicates what part of the codebase is affected:

- `vault` — Vault-related features
- `auth` — Authentication/authorization
- `pin` — PIN management
- `api` — API layer changes
- `domain` — Domain layer changes
- `infra` — Infrastructure changes
- `obs` — Observability (metrics, logging, monitoring)
- `db` — Database migrations or repositories
- `websocket` — WebSocket functionality

### Subject

- Use imperative mood ("add" not "added" or "adds")
- No capitalization of first letter
- No period at the end
- Max 50 characters

### Body

Optional. Explains **what** and **why**, not **how**.

- Wrap at 72 characters
- Separate from subject with blank line
- Use bullet points for multiple items

### Footer

Optional. References issues, breaking changes.

```
Fixes #123
Closes #456
BREAKING CHANGE: PIN validation now requires 6-8 digits instead of 4-8
```

### Examples

**Simple commit:**
```
feat(vault): add vault sharing with role-based permissions
```

**Commit with body:**
```
fix(pin): prevent timing attack in PIN verification

Use constant-time comparison to prevent attackers from inferring
PIN correctness based on response time.

Fixes #234
```

**Breaking change:**
```
refactor(api): change unlock endpoint response format

BREAKING CHANGE: Unlock endpoint now returns vault status object
instead of simple string. Update clients accordingly.

Before: { "status": "unlocked" }
After: { "vault": { "id": "...", "status": "unlocked", ... } }
```

**Migration commit:**
```
chore(db): add vault_shares table migration

Migration: add vault_shares table for multi-user vault access.

Generated with: make migration msg="add vault shares table"
```

---

## Pull Request Process

### PR Title

Use commit message format:
```
feat(vault): add vault sharing with permissions
```

### PR Description Template

```markdown
## Summary
Brief description of what this PR does.

## Motivation
Why is this change needed? What problem does it solve?

## Changes
- Added X
- Modified Y
- Removed Z

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed

## Architecture Impact
- [ ] Domain layer changes
- [ ] Application layer changes
- [ ] Infrastructure layer changes
- [ ] API layer changes
- [ ] Database migration included

## Checklist
- [ ] Tests pass locally (`make test`)
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] Migration is reversible (if applicable)
- [ ] No breaking changes (or documented if unavoidable)
- [ ] Observability added (metrics/logs where appropriate)

## Related Issues
Fixes #123
Relates to #456
```

### PR Review Process

**1. Automated checks must pass:**
- CI tests
- Linting (if configured)
- Build succeeds

**2. Code review:**
- At least 1 approval required
- Address all comments
- Resolve conversations

**3. Merge:**
- Use **"Squash and merge"** for feature branches
- Use **"Merge commit"** for release branches
- Delete branch after merge

---

## Code Standards

### Python Style

- Follow **PEP 8**
- Use **type hints** for all function signatures
- Max line length: **100 characters**
- Use **Black** for formatting (if configured)
- Use **isort** for import sorting (if configured)

**Example:**
```python
def unlock_vault(
    vault_id: str,
    user_id: int,
    pin: str,
) -> VaultUnlockedEvent:
    """Unlock a vault using PIN authentication.
    
    Args:
        vault_id: Unique vault identifier
        user_id: ID of user attempting unlock
        pin: PIN for authentication
        
    Returns:
        VaultUnlockedEvent on success
        
    Raises:
        InvalidPINException: If PIN is incorrect
        VaultLockedOutException: If vault is locked due to too many failures
    """
    # Implementation
```

### Clean Architecture Rules

**Domain layer:**
- ✅ Pure Python, no framework imports
- ✅ Rich domain models with behavior
- ✅ Value objects for validated concepts
- ❌ NO SQLAlchemy imports
- ❌ NO FastAPI imports
- ❌ NO Redis imports

**Application layer:**
- ✅ Use case orchestration
- ✅ Depend on ports (interfaces), not implementations
- ✅ Track metrics using helpers
- ❌ NO direct database access
- ❌ NO HTTP request/response objects

**Infrastructure layer:**
- ✅ Implement ports from application layer
- ✅ Map domain models to database models
- ❌ NO business logic

**API layer:**
- ✅ Thin controllers
- ✅ Input validation with Pydantic
- ❌ NO business logic

### Error Handling

**Use domain exceptions:**
```python
# ✅ GOOD
raise VaultNotFoundException(f"Vault {vault_id} not found")

# ❌ BAD
raise Exception("Vault not found")
```

**Handle exceptions at API layer:**
```python
@router.post("/vaults/{vault_id}/unlock")
def unlock_vault(...):
    try:
        use_case.execute(...)
    except InvalidPINException:
        raise HTTPException(status_code=401, detail="Invalid PIN")
    except VaultLockedOutException:
        raise HTTPException(status_code=429, detail="Vault locked")
```

### Logging

**Use structured logging:**
```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# ✅ GOOD: Structured with context
logger.info("vault_unlocked", vault_id=vault.id, user_id=user.id)

# ❌ BAD: String formatting
logger.info(f"Vault {vault.id} unlocked by user {user.id}")
```

**Never log sensitive data:**
```python
# ❌ NEVER log PINs, passwords, tokens
logger.debug("pin_verified", pin=pin_value)  # ❌❌❌

# ✅ Log outcome only
logger.info("pin_verified", vault_id=vault_id, result="success")
```

---

## Testing Requirements

### Coverage Requirements

- **Minimum coverage:** 80% overall
- **Domain layer:** 90%+ coverage
- **Application layer:** 85%+ coverage
- **Critical paths:** 100% coverage (auth, unlock, PIN validation)

### Test Types

**1. Unit tests** — Domain and application layers
```python
# app/tests/application/test_unlock_vault.py
def test_unlock_with_valid_pin():
    vault_repo = InMemoryVaultRepository()
    use_case = UnlockVaultWithPIN(vault_repo, FakeRateLimiter())
    
    event = use_case.execute("vault-1", 123, "1234")
    
    assert event.vault_id == "vault-1"
    assert vault_repo.get_by_id("vault-1").status == VaultStatus.UNLOCKED
```

**2. Integration tests** — API layer
```python
# app/tests/api/test_unlock_endpoint.py
def test_unlock_endpoint_success(client, test_user, test_vault):
    response = client.post(
        f"/api/v1/vaults/{test_vault.id}/unlock",
        json={"pin": "1234"},
        headers={"Authorization": f"Bearer {test_user.token}"}
    )
    
    assert response.status_code == 200
    assert response.json()["status"] == "unlocked"
```

**3. Edge case tests** — Boundary conditions
```python
def test_unlock_with_expired_pin():
    # Test expired PIN handling
    
def test_unlock_during_rate_limit():
    # Test rate limit behavior
    
def test_unlock_with_concurrent_requests():
    # Test race conditions
```

### Test Organization

```
app/tests/
├── api/              # API integration tests
├── application/      # Use case unit tests
├── domain/           # Domain model tests
├── infrastructure/   # Infrastructure adapter tests
├── fakes/            # In-memory test doubles
└── conftest.py       # Shared fixtures
```

### Running Tests

```bash
# All tests
make test

# Verbose output
make test-vv

# Specific layer
make test-api
make test-app

# Single test file
docker compose exec api pytest app/tests/api/test_unlock.py -v

# Single test function
docker compose exec api pytest app/tests/api/test_unlock.py::test_unlock_success -v

# With coverage
docker compose exec api pytest --cov=app --cov-report=html
```

---

## Code Review Checklist

### For Authors

**Before requesting review:**
- [ ] All tests pass (`make test`)
- [ ] Code follows architecture guidelines
- [ ] No business logic in controllers or infrastructure
- [ ] Sensitive data is never logged
- [ ] New features have tests
- [ ] Documentation updated (if needed)
- [ ] Migration is reversible (if applicable)
- [ ] PR description is complete

### For Reviewers

**Architectural review:**
- [ ] Changes are in appropriate layer
- [ ] Dependencies flow inward (domain ← application ← infrastructure ← api)
- [ ] No infrastructure imports in domain
- [ ] Ports defined for new infrastructure adapters

**Code quality:**
- [ ] Code is readable and well-named
- [ ] Functions are focused and single-purpose
- [ ] Error handling is appropriate
- [ ] No hardcoded values (use config/env vars)

**Testing:**
- [ ] New features have tests
- [ ] Tests cover edge cases
- [ ] Tests are focused and fast
- [ ] No commented-out test code

**Security:**
- [ ] No sensitive data in logs
- [ ] Input validation present
- [ ] SQL injection prevented (using ORM correctly)
- [ ] Rate limiting applied where needed

**Observability:**
- [ ] Metrics added for significant operations
- [ ] Structured logging used appropriately
- [ ] Request context preserved in logs

**Database:**
- [ ] Migration is reversible
- [ ] Migration tested (up and down)
- [ ] No breaking schema changes (or coordinated deployment)
- [ ] Indexes added for new queries

---

## Documentation Requirements

### When to Update Documentation

| Change | Required Documentation |
|--------|----------------------|
| New feature | README.md feature list, API.md endpoint docs |
| Architecture change | ARCHITECTURE.md |
| New environment variable | README.md env table, .env.example |
| New metric | OBSERVABILITY.md metrics catalog |
| Breaking change | CHANGELOG.md, migration guide |
| Deployment process | DEPLOYMENT.md |
| Security model change | SECURITY.md |

### Documentation Standards

- Use clear, concise language
- Include examples
- Keep code samples up-to-date
- Link to related documentation
- Use tables for structured data
- Use code blocks with syntax highlighting

---

## Migration Guidelines

### Creating Migrations

**1. Modify domain models first**
```python
# app/domain/models/vault.py
class Vault:
    def __init__(self, ..., shared_with: list[int] = None):
        self.shared_with = shared_with or []
```

**2. Generate migration**
```bash
make migration msg="add vault sharing support"
```

**3. Review auto-generated migration**
```python
# app/alembic/versions/abc123_add_vault_sharing_support.py

def upgrade():
    # Review and adjust if needed
    op.add_column('vaults', sa.Column('shared_with', sa.JSON(), nullable=True))

def downgrade():
    # CRITICAL: Always implement downgrade
    op.drop_column('vaults', 'shared_with')
```

**4. Test migration**
```bash
make migrate      # Test upgrade
make rollback     # Test downgrade
make migrate      # Re-apply
```

**5. Test with actual data (if possible)**
```sql
-- In psql, create test data
INSERT INTO vaults (id, owner_id) VALUES ('test-1', 123);

-- Run migration
-- Verify data integrity
```

### Migration Rules

- ✅ Always implement `downgrade()`
- ✅ Make migrations backward-compatible when possible
- ✅ Use nullable columns for additive changes
- ✅ Test on realistic data
- ✅ Commit migration with feature code
- ❌ NEVER edit existing migrations in production
- ❌ NEVER drop columns without coordination

---

## Getting Help

- **Architecture questions:** Review [`ARCHITECTURE.md`](ARCHITECTURE.md)
- **Setup issues:** Check [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)
- **Development workflow:** See [`DEVELOPMENT.md`](DEVELOPMENT.md)
- **Stuck?** Open a GitHub discussion or ask in Slack/Discord

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (MIT License).