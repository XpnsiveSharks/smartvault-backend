# Troubleshooting Guide

This document covers common issues and their solutions when developing, deploying, or operating SmartVault.

---

## Table of Contents

1. [Docker Issues](#docker-issues)
2. [Database Issues](#database-issues)
3. [Redis Issues](#redis-issues)
4. [Migration Issues](#migration-issues)
5. [Authentication Issues](#authentication-issues)
6. [Observability Issues](#observability-issues)
7. [Performance Issues](#performance-issues)
8. [WebSocket Issues](#websocket-issues)

---

## Docker Issues

### Services Won't Start

**Symptom:** `docker-compose up` fails or services crash immediately.

**Solution 1: Check Docker daemon**
```bash
# Verify Docker is running
docker ps

# If not running, start Docker Desktop (Windows/Mac)
# Or start Docker service (Linux):
sudo systemctl start docker
```

**Solution 2: Check for port conflicts**
```bash
# Check if ports are already in use
lsof -i :8000   # API
lsof -i :5432   # PostgreSQL
lsof -i :6379   # Redis
lsof -i :9090   # Prometheus
lsof -i :3000   # Grafana

# Kill conflicting processes or change ports in docker-compose.yml
```

**Solution 3: Clean rebuild**
```bash
# Stop everything
make down

# Remove volumes (⚠️ deletes data)
docker-compose down -v

# Rebuild from scratch
make dev
```

---

### Container Keeps Restarting

**Symptom:** API container restarts in a loop.

**Check logs:**
```bash
docker-compose logs -f api
```

**Common causes:**

**1. Database connection failure**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solution:**
```bash
# Verify PostgreSQL is healthy
docker-compose ps postgres

# Check DATABASE_URL in .env
cat .env | grep DATABASE_URL

# Ensure it points to 'postgres' (service name) not 'localhost'
DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/smartvault
```

**2. Missing environment variable**
```
pydantic_core._pydantic_core.ValidationError: 1 validation error for Settings
SECRET_KEY
  Field required
```

**Solution:**
```bash
# Check .env file exists
ls -la .env

# Ensure SECRET_KEY is set
echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env

# Restart
make restart
```

**3. Migration failure**
```
alembic.util.exc.CommandError: Can't locate revision identified by 'abc123'
```

**Solution:**
```bash
# Reset database (⚠️ DEV ONLY)
make db-reset

# Or manually fix migrations
make psql
# DROP SCHEMA public CASCADE; CREATE SCHEMA public;
# \q

make migrate
```

---

### "Permission Denied" Errors

**Symptom:** Cannot access files or volumes.

**Windows (WSL2):**
```bash
# Ensure repository is in WSL filesystem, not /mnt/c/
pwd  # Should show /home/username/..., not /mnt/c/...

# If in /mnt/c/, move to WSL home directory
cd ~
git clone <repo-url>
```

**Linux:**
```bash
# Fix ownership
sudo chown -R $USER:$USER .

# Fix Docker socket permissions (if needed)
sudo chmod 666 /var/run/docker.sock
```

---

### Slow Performance on Windows/Mac

**Symptom:** Extremely slow file operations in Docker.

**Solution: Use volume mounts carefully**
```yaml
# docker-compose.yml
services:
  api:
    volumes:
      # ❌ Slow: Bind mount entire directory
      - .:/app
      
      # ✅ Faster: Use named volume for dependencies
      - .:/app
      - /app/node_modules  # Exclude node_modules
      - /app/__pycache__   # Exclude Python cache
```

**Alternative: Use Docker Sync or Mutagen**

---

## Database Issues

### Connection Refused

**Symptom:**
```
psycopg.OperationalError: connection refused
```

**Solution 1: Check PostgreSQL is running**
```bash
docker-compose ps postgres

# Should show "Up (healthy)"
```

**Solution 2: Verify connection string**
```bash
# Check .env
cat .env | grep DATABASE_URL

# Should be:
DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/smartvault

# NOT:
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/smartvault
```

**Solution 3: Wait for health check**
```bash
# API depends on PostgreSQL being healthy
# Wait 30 seconds and check again
docker-compose ps
```

---

### "Too Many Connections"

**Symptom:**
```
psycopg.OperationalError: FATAL: too many connections
```

**Solution: Reduce connection pool size**
```python
# app/infrastructure/db/session.py
engine = create_engine(
    DATABASE_URL,
    pool_size=5,        # Reduce from 20
    max_overflow=5,     # Reduce from 10
)
```

**Or scale PostgreSQL:**
```sql
-- Increase max_connections
ALTER SYSTEM SET max_connections = 200;
-- Restart PostgreSQL
```

---

### Migration Conflicts

**Symptom:**
```
alembic.util.exc.CommandError: Target database is not up to date.
```

**Solution 1: Check current revision**
```bash
make current
```

**Solution 2: Apply all migrations**
```bash
make migrate
```

**Solution 3: Resolve conflicts**
```bash
# If multiple heads exist
make history

# Merge heads
docker-compose exec api alembic merge heads -m "merge heads"

# Apply merge
make migrate
```

---

### Database Locked (SQLite development)

**Note:** SmartVault uses PostgreSQL. If you see SQLite errors, check your `DATABASE_URL`.

---

## Redis Issues

### Redis Connection Failed

**Symptom:**
```
redis.exceptions.ConnectionError: Connection refused
```

**Solution 1: Check Redis is running**
```bash
docker-compose ps redis

# Should show "Up (healthy)"
```

**Solution 2: Verify REDIS_URL**
```bash
cat .env | grep REDIS_URL

# Should be:
REDIS_URL=redis://redis:6379/0

# NOT:
REDIS_URL=redis://localhost:6379/0
```

---

### Redis Out of Memory

**Symptom:**
```
redis.exceptions.ResponseError: OOM command not allowed when used memory > 'maxmemory'
```

**Solution 1: Flush Redis (⚠️ DEV ONLY)**
```bash
make redis-flush
```

**Solution 2: Configure maxmemory policy**
```yaml
# docker-compose.yml
services:
  redis:
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
```

---

### Rate Limiting Not Working

**Symptom:** Can exceed rate limits without being blocked.

**Check:**
```bash
# Open Redis CLI
make redis

# Check if rate limit keys exist
KEYS attempts:*
KEYS lockout:*

# If empty, rate limiter is not writing to Redis
```

**Solution: Verify Redis connection in code**
```python
# Test Redis connectivity
from app.infrastructure.cache.redis_client import redis_client

redis_client.ping()  # Should return True
```

---

## Migration Issues

### "Can't Locate Revision"

**Symptom:**
```
alembic.util.exc.CommandError: Can't locate revision identified by 'abc123'
```

**Cause:** Migration file was deleted or database is out of sync.

**Solution 1: Check migration files exist**
```bash
ls app/alembic/versions/
```

**Solution 2: Reset database (⚠️ DEV ONLY)**
```bash
make db-reset
```

**Solution 3: Manual stamp (if you know the correct revision)**
```bash
docker-compose exec api alembic stamp head
```

---

### Migration Creates Wrong Tables

**Symptom:** Auto-generated migration adds/removes unexpected columns.

**Cause:** Alembic compares database schema to SQLAlchemy models.

**Solution 1: Review migration before applying**
```bash
# Generate migration
make migration msg="add user role"

# Review generated file
cat app/alembic/versions/<revision>_add_user_role.py

# Edit if needed, then apply
make migrate
```

**Solution 2: Specify target metadata**
```python
# app/alembic/env.py
from app.infrastructure.db.models import Base

target_metadata = Base.metadata
```

---

### Migration Fails Midway

**Symptom:** Migration partially applied, database in inconsistent state.

**Solution: Rollback and fix**
```bash
# Rollback failed migration
make rollback

# Fix migration file
# Re-apply
make migrate
```

---

## Authentication Issues

### "Invalid Token" Error

**Symptom:**
```json
{
  "error": {
    "code": "INVALID_TOKEN",
    "message": "Token is invalid or expired"
  }
}
```

**Cause 1: Token expired**
- Access tokens expire after 30 minutes
- **Solution:** Use refresh token to get new access token

**Cause 2: Wrong SECRET_KEY**
- Token was signed with different key
- **Solution:** Ensure `SECRET_KEY` is consistent across restarts

**Cause 3: Malformed token**
```bash
# Test token manually
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/users/me

# Should return user data or clear error
```

---

### "Unauthorized" on Public Endpoint

**Symptom:** Health check or login endpoint returns 401.

**Cause:** Endpoint was accidentally marked as protected.

**Check:**
```python
# app/api/v1/health.py

# ✅ CORRECT: No Depends(get_current_user)
@router.get("/health")
def health():
    return {"status": "healthy"}

# ❌ WRONG: Requires authentication
@router.get("/health")
def health(user = Depends(get_current_user)):
    return {"status": "healthy"}
```

---

### Can't Login After Restart

**Cause:** `SECRET_KEY` changed or missing.

**Solution:**
```bash
# Check SECRET_KEY is set
cat .env | grep SECRET_KEY

# If missing or changed, set it
echo "SECRET_KEY=$(openssl rand -hex 32)" >> .env

# Restart
make restart

# Re-login (old tokens won't work)
```

---

## Observability Issues

### Prometheus Not Scraping Metrics

**Symptom:** Grafana shows "No data" for all metrics.

**Solution 1: Check Prometheus targets**
- Go to http://localhost:9090/targets
- Verify `smartvault-api` target is **UP**

**Solution 2: Check /metrics endpoint**
```bash
curl http://localhost:8000/metrics

# Should return Prometheus metrics format
# HELP http_requests_total ...
# TYPE http_requests_total counter
```

**Solution 3: Verify prometheus.yml**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'smartvault'
    static_configs:
      - targets: ['api:8000']  # Use service name, not localhost
```

---

### Grafana Can't Connect to Prometheus

**Symptom:** Grafana datasource shows "HTTP Error Bad Gateway".

**Solution 1: Check Prometheus is running**
```bash
docker-compose ps prometheus
```

**Solution 2: Test Prometheus from Grafana container**
```bash
docker-compose exec grafana curl http://prometheus:9090/api/v1/query?query=up
```

**Solution 3: Fix datasource URL**
- Go to http://localhost:3000/datasources
- Edit Prometheus datasource
- URL should be: `http://prometheus:9090` (not `http://localhost:9090`)
- Click "Save & Test"

---

### Sentry Not Receiving Errors

**Symptom:** No errors appear in Sentry dashboard.

**Solution 1: Check DSN is set**
```bash
cat .env | grep SENTRY_DSN

# Should be a valid Sentry DSN
SENTRY_DSN=https://key@o123456.ingest.sentry.io/7654321
```

**Solution 2: Test Sentry manually**
```python
# In Python shell or endpoint
import sentry_sdk
sentry_sdk.capture_message("Test error from SmartVault")

# Check Sentry dashboard
```

**Solution 3: Check sample rate**
```bash
# If SENTRY_TRACES_SAMPLE_RATE=0, nothing is sent
cat .env | grep SENTRY_TRACES_SAMPLE_RATE

# Set to 1.0 for testing
SENTRY_TRACES_SAMPLE_RATE=1.0
```

---

### Logs Missing Request ID

**Symptom:** Logs don't include `request_id` field.

**Cause:** `RequestIDMiddleware` not registered.

**Solution:**
```python
# app/main.py
from app.api.middleware.request_id import RequestIDMiddleware

app.add_middleware(RequestIDMiddleware)  # Must be added
```

**Verify:**
```bash
curl -v http://localhost:8000/api | grep X-Request-ID

# Should return:
# X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

---

### Sensitive Data in Logs

**Symptom:** Passwords/PINs appear in logs.

**Cause:** Logger redaction not working.

**Solution:**
```python
# app/core/logging.py

# Verify SENSITIVE_FIELDS includes all sensitive keys
SENSITIVE_FIELDS = [
    "password",
    "pin",
    "token",
    "secret",
    "api_key",
]

# Ensure processor is in chain
processors=[
    # ...
    redact_sensitive_fields,
    # ...
]
```

---

## Performance Issues

### Slow API Responses

**Symptom:** API latency > 1 second.

**Diagnosis:**
```bash
# Check Prometheus metrics
curl http://localhost:8000/metrics | grep http_request_duration

# Identify slow endpoints
# Check Grafana dashboard for p95/p99 latency
```

**Solution 1: Database query optimization**
```python
# Add indexes for frequently queried columns
# app/alembic/versions/xxx_add_indexes.py
def upgrade():
    op.create_index('idx_vault_owner', 'vaults', ['owner_id'])
    op.create_index('idx_membership_vault', 'vault_memberships', ['vault_id'])
```

**Solution 2: Add caching**
```python
# Cache vault status in Redis
def get_vault_status(vault_id: str):
    cached = redis.get(f"vault_status:{vault_id}")
    if cached:
        return json.loads(cached)
    
    status = vault_repo.get_status(vault_id)
    redis.setex(f"vault_status:{vault_id}", 60, json.dumps(status))
    return status
```

**Solution 3: Increase connection pool**
```python
# app/infrastructure/db/session.py
engine = create_engine(
    DATABASE_URL,
    pool_size=20,       # Increase from 5
    max_overflow=10,
)
```

---

### High Memory Usage

**Symptom:** Container uses > 2GB RAM.

**Diagnosis:**
```bash
docker stats smartvault-api

# Check memory usage
```

**Solution 1: Reduce connection pools**
```python
# Database
pool_size=5  # Reduce from 20

# Redis
max_connections=10  # Reduce from 50
```

**Solution 2: Configure Uvicorn workers**
```bash
# Limit workers (each uses ~100-200MB)
uvicorn app.main:app --workers 2
```

---

## WebSocket Issues

### WebSocket Connection Fails

**Symptom:**
```javascript
WebSocket connection to 'ws://localhost:8000/api/ws/device-1' failed
```

**Solution 1: Check WebSocket route exists**
```bash
curl http://localhost:8000/api

# Should return websocket_stats
```

**Solution 2: Check firewall/proxy**
- Ensure WebSocket traffic is allowed
- Some proxies block WebSocket upgrades

**Solution 3: Use correct protocol**
```javascript
// ✅ CORRECT
const ws = new WebSocket('ws://localhost:8000/api/ws/device-1');

// ❌ WRONG
const ws = new WebSocket('http://localhost:8000/api/ws/device-1');
```

---

### WebSocket Disconnects Immediately

**Symptom:** Connection opens then closes within seconds.

**Check server logs:**
```bash
make logs

# Look for WebSocket errors
```

**Cause 1: Client ID already connected**
- Each client_id can only have one active connection
- **Solution:** Use unique client IDs

**Cause 2: Authentication failure (if implemented)**
- **Solution:** Send valid token in initial message

---

## Getting More Help

If your issue isn't covered here:

1. **Check logs:**
   ```bash
   make logs
   docker-compose logs -f api
   docker-compose logs -f postgres
   docker-compose logs -f redis
   ```

2. **Check Docker status:**
   ```bash
   docker-compose ps
   docker stats
   ```

3. **Check health endpoints:**
   ```bash
   curl http://localhost:8000/api/v1/health/detailed
   ```

4. **Search GitHub Issues:**
   - Check if someone else has encountered this issue

5. **Open a GitHub Issue:**
   - Include logs, environment details, and steps to reproduce

---

## Related Documentation

- [Development Guide](DEVELOPMENT.md)
- [Architecture](ARCHITECTURE.md)
- [Deployment](DEPLOYMENT.md)
- [Observability](OBSERVABILITY.md)