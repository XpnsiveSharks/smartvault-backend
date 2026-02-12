# SmartVault Backend API

Backend API for SmartVault — a secure vault management system with PIN-based unlocking, biometric authentication, and real-time WebSocket communication.

Built with **FastAPI**, **PostgreSQL**, **Redis**, and **Docker** using **Clean Architecture** principles.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **API Framework** | FastAPI |
| **Database** | PostgreSQL 16 |
| **Cache / Rate Limiting** | Redis 7 |
| **ORM** | SQLAlchemy 2.0 |
| **Migrations** | Alembic |
| **Authentication** | PBKDF2 password hashing, JWT tokens |
| **WebSockets** | FastAPI native WebSocket support |
| **Biometrics** | Face recognition integration |
| **Observability** | Prometheus, Grafana, Sentry, Structlog |
| **Infrastructure** | Docker + Docker Compose |

---

## Architecture Overview

This project follows **Clean Architecture** with clear separation of concerns:

```
┌─────────────────────────────────────────────────┐
│  API Layer (FastAPI)                            │
│  - HTTP endpoints, WebSocket handlers           │
│  - Request/response validation                  │
│  - Dependency injection                         │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│  Application Layer                              │
│  - Use cases (business workflows)               │
│  - Services (reusable logic)                    │
│  - Ports (interface definitions)                │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│  Domain Layer                                   │
│  - Business models (User, Vault, etc.)          │
│  - Value objects (PIN, VaultStatus, etc.)       │
│  - Domain events                                │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│  Infrastructure Layer                           │
│  - Database repositories                        │
│  - Redis cache                                  │
│  - External services (email, biometrics)        │
│  - Monitoring & observability                   │
└─────────────────────────────────────────────────┘
```

**Dependency Rule:** Inner layers know nothing about outer layers. Domain is pure business logic with zero infrastructure dependencies.

For detailed architecture documentation, see [`Docs/ARCHITECTURE.md`](Docs/ARCHITECTURE.md).

---

## Project Structure

```
app/
├── api/                  # API layer (FastAPI routers, deps, middleware)
│   ├── deps/            # Dependency injection providers
│   ├── middleware/      # Request ID, logging, rate limiting
│   └── v1/              # API version 1 endpoints
├── application/          # Application layer (use cases, services, ports)
│   ├── use_cases/       # Business workflows
│   ├── services/        # Reusable application services
│   └── ports/           # Interface definitions for adapters
├── domain/               # Domain layer (business logic)
│   ├── models/          # Business entities (User, Vault, AccessLog)
│   ├── value_objects/   # Immutable domain concepts (PIN, VaultStatus)
│   └── events/          # Domain events
├── infrastructure/       # Infrastructure layer (external integrations)
│   ├── db/              # SQLAlchemy repositories
│   ├── cache/           # Redis client
│   ├── security/        # Password hashing, PIN validation
│   ├── messaging/       # WebSocket manager
│   ├── monitoring/      # Prometheus metrics, helpers
│   ├── biometrics/      # Face recognition service
│   └── notifications/   # Email service
├── core/                 # Cross-cutting concerns
│   ├── config.py        # Configuration models
│   ├── settings.py      # Environment-driven settings
│   ├── logging.py       # Structured logging setup
│   └── sentry.py        # Sentry error tracking
├── schemas/              # Pydantic request/response models
├── tests/                # Test suite
│   ├── api/             # API integration tests
│   ├── application/     # Use case unit tests
│   ├── domain/          # Domain model tests
│   ├── infrastructure/  # Infrastructure adapter tests
│   └── fakes/           # In-memory test doubles
├── websocket/            # WebSocket handlers
└── main.py               # Application bootstrap
```

---

## Observability Stack

SmartVault includes production-ready observability:

### Metrics (Prometheus + Grafana)
- **Prometheus**: Collects metrics from `/metrics` endpoint
- **Grafana**: Visualizes metrics with pre-configured dashboards
- **Access**: 
  - Prometheus: http://localhost:9090
  - Grafana: http://localhost:3000 (admin/admin)

**Available Metrics:**
- HTTP request duration, status codes, in-progress requests
- Vault unlock operations and duration
- PIN lockout events
- Authentication failures
- Business metrics (members added, PINs set, etc.)

### Error Tracking (Sentry)
- Automatic exception capture
- Request context attached to errors
- PII scrubbing enforced by default
- Environment-based sample rates

### Structured Logging
- JSON output in production
- Pretty console in development
- Automatic request ID correlation
- Sensitive field redaction (PIN, password, token)

### Health Checks
- `/api/v1/health` — Liveness probe
- `/api/v1/health/detailed` — Readiness probe with DB + Redis latency

**For complete observability setup, see [`Docs/OBSERVABILITY.md`](Docs/OBSERVABILITY.md).**

---

## Getting Started

### Prerequisites

- **Docker** (20.10+)
- **Docker Compose** (2.0+)
- **Make** (optional, for convenience commands)

**Windows Users:** See [`Docs/wsl.md`](Docs/wsl.md) for WSL setup instructions.

### Quick Start

**1. Clone the repository**
```bash
git clone <repository-url>
cd smartvault-backend
```

**2. Create environment file**
```bash
cp .env.example .env
```

**3. Generate a secret key**
```bash
openssl rand -hex 32
```
Update `SECRET_KEY` in `.env` with the generated value.

**4. Start everything**
```bash
make dev
```

This will:
- Build Docker images
- Start API, PostgreSQL, Redis, Prometheus, Grafana
- Apply database migrations
- Display connection status

**5. Verify the API**
```bash
curl http://localhost:8000/api
```

**API Documentation:** http://localhost:8000/docs

---

## Environment Configuration

### Core Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | `postgresql+psycopg://...` | PostgreSQL connection string |
| `REDIS_URL` | Yes | `redis://redis:6379/0` | Redis connection string |
| `SECRET_KEY` | **Yes** | - | JWT signing key (generate with `openssl rand -hex 32`) |
| `environment` | No | `development` | Environment name (development/staging/production) |
| `DEV_AUTH_BYPASS` | No | `false` | **DEV ONLY:** Bypass authentication for testing |

### Security

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | JWT access token lifetime |
| `RATE_LIMIT_OTP_REQ_PER_MIN` | No | `3` | OTP request rate limit |
| `RATE_LIMIT_LOGIN_REQ_PER_MIN` | No | `5` | Login attempt rate limit |

### Email / SMTP

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `EMAIL_BACKEND` | No | Auto-detected | Email backend (`dev` or `smtp`) |
| `SMTP_HOST` | No | - | SMTP server hostname |
| `SMTP_PORT` | No | `587` | SMTP server port |
| `SMTP_USER` | No | - | SMTP username |
| `SMTP_PASSWORD` | No | - | SMTP password |
| `SMTP_FROM_EMAIL` | No | - | Sender email address |

### Observability (Sentry)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SENTRY_DSN` | No | - | Sentry DSN (get from https://sentry.io) |
| `SENTRY_ENVIRONMENT` | No | `development` | Environment tag for Sentry events |
| `SENTRY_TRACES_SAMPLE_RATE` | No | `0.1` | Percentage of transactions to trace (0.0-1.0) |
| `SENTRY_PROFILES_SAMPLE_RATE` | No | `0.1` | Percentage of transactions to profile (0.0-1.0) |
| `SENTRY_SEND_DEFAULT_PII` | No | `false` | **KEEP FALSE** — Never send PII to Sentry |

### Grafana

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GRAFANA_ADMIN_PASSWORD` | No | `admin` | Grafana admin password |

**Complete `.env.example` reference:** [`.env.example`](.env.example)

---

## Common Commands

### Development Workflow

```bash
make dev          # Build + start + migrate + show status
make up           # Build and start all services
make stop         # Stop services (keeps data)
make down         # Stop and remove containers
make restart      # Restart all services
make logs         # Tail API logs
make test         # Run pytest suite
```

### Database (PostgreSQL + Alembic)

```bash
make migrate               # Apply pending migrations
make migration msg="..."   # Create new migration
make rollback              # Rollback last migration
make psql                  # Open PostgreSQL shell
make db-reset              # DEV ONLY: Drop and recreate schema
```

**Migration Guide:** [`Docs/alembic.md`](Docs/alembic.md)

### Cache (Redis)

```bash
make redis         # Open Redis CLI
make redis-info    # Show Redis server info
make redis-flush   # DEV ONLY: Flush Redis database
```

**Redis Guide:** [`Docs/redis.md`](Docs/redis.md)

### Testing

```bash
make test          # Run all tests (quiet)
make test-vv       # Run all tests (verbose)
make test-api      # Run API tests only
make test-app      # Run application tests only
make test-k k="pattern"  # Run tests matching pattern
```

**Testing Guide:** [`Docs/test.md`](Docs/test.md)

---

## Key Features

### ✅ Implemented

**Authentication & Authorization**
- User registration and login
- Password hashing (PBKDF2)
- JWT token generation (access + refresh)
- Role-based access control (ADMIN, MEMBER, VIEWER)

**Vault Management**
- Vault provisioning (hardware UUID binding)
- Vault membership management
- Vault status tracking
- Access control enforcement

**PIN-Based Unlocking**
- Secure PIN creation and storage (PBKDF2 hashing)
- PIN-based vault unlocking
- Rate limiting (5 attempts per 15 minutes)
- Automatic lockout on excessive failures
- Role-based unlock permissions

**Security**
- Redis-based rate limiting
- Request ID correlation
- Structured audit logging
- Domain event tracking

**Quality Assurance**
- 119+ tests across all layers
- In-memory test doubles for fast testing
- API integration tests
- Use case unit tests

### ⚠️ Partial Integration

- OTP email verification (infrastructure exists, needs endpoint integration)
- Biometric enrollment (service exists, needs endpoint integration)
- WebSocket unlock commands (code exists, needs hardware integration)

### 🚧 Future Features

- Hardware vault WebSocket integration
- Push notifications
- Activity dashboard
- Admin panel

---

## Migrations

**Important Rules:**
- Alembic is the **source of truth** for schema changes
- Never edit database tables manually in production
- Always commit migrations with the feature that introduced them
- Test migrations in both upgrade and downgrade directions

**Migration Workflow:**
1. Modify domain models
2. Generate migration: `make migration msg="add user role field"`
3. Review auto-generated migration file
4. Test: `make migrate` then `make rollback`
5. Commit migration file with your feature

---

## Architecture Decisions

### Clean Architecture

- **Domain** is infrastructure-agnostic (no SQLAlchemy, no FastAPI imports)
- **Application** orchestrates use cases without knowing HTTP or database details
- **Infrastructure** adapts external systems to domain interfaces
- **API** translates HTTP to application layer calls

### Repository Pattern

- Domain models are separate from database models
- Repositories map between domain and persistence
- In-memory repositories enable fast, database-free testing

### Event-Driven Design

- Domain events capture significant business occurrences
- Events enable audit trails and extensibility
- Events decouple components

### Observability-First

- Structured logging from day one
- Metrics for business and technical operations
- Health checks for production readiness
- Error tracking with PII protection

---

## Documentation Index

### Core Documentation
- [Architecture Deep Dive](Docs/ARCHITECTURE.md)
- [Observability Guide](Docs/OBSERVABILITY.md)
- [API Reference](Docs/API.md)
- [Security Model](Docs/SECURITY.md)

### Operational Guides
- [Deployment Guide](Docs/DEPLOYMENT.md)
- [Troubleshooting](Docs/TROUBLESHOOTING.md)
- [Release Strategy](Docs/releases.md)
- [Changelog](Docs/CHANGELOG.md)

### Development
- [Contributing Guidelines](Docs/CONTRIBUTING.md)
- [Development Workflow](Docs/DEVELOPMENT.md)
- [Testing Guide](Docs/test.md)

### Tool-Specific
- [Docker Commands](Docs/docker-commands.md)
- [PostgreSQL](Docs/postgres.md)
- [Alembic Migrations](Docs/alembic.md)
- [Redis](Docs/redis.md)
- [WSL Setup](Docs/wsl.md)

---

## Contributing

We welcome contributions! Please read our [Contributing Guidelines](Docs/CONTRIBUTING.md) before submitting pull requests.

**Quick Contribution Checklist:**
- [ ] Tests pass (`make test`)
- [ ] New features have tests
- [ ] Migrations are reversible
- [ ] Documentation updated
- [ ] PR description follows template

---

## License

MIT License - See [LICENSE](LICENSE) file.

---

## Support

- **Issues:** Open a GitHub issue
- **Security:** See [SECURITY.md](Docs/SECURITY.md) for vulnerability reporting
- **Questions:** Check [Troubleshooting](Docs/TROUBLESHOOTING.md) first