# Deployment Guide

This document covers deploying SmartVault to production environments, including staging, production, and disaster recovery procedures.

---

## Table of Contents

1. [Environment Strategy](#environment-strategy)
2. [Production Checklist](#production-checklist)
3. [Docker Deployment](#docker-deployment)
4. [Environment Configuration](#environment-configuration)
5. [Database Migrations](#database-migrations)
6. [Health Checks & Monitoring](#health-checks--monitoring)
7. [Scaling Considerations](#scaling-considerations)
8. [Rollback Procedures](#rollback-procedures)
9. [Disaster Recovery](#disaster-recovery)

---

## Environment Strategy

### Environment Types

| Environment | Purpose | Branch | URL Pattern |
|-------------|---------|--------|-------------|
| **Development** | Local development | `dev` | `localhost:8000` |
| **Staging** | Pre-production testing | `release/vX.Y.Z` | `staging.smartvault.com` |
| **Production** | Live system | `main` | `api.smartvault.com` |

### Environment Variables

Each environment should have its own `.env` file with appropriate values:

```bash
# Development
environment=development
DATABASE_URL=postgresql+psycopg://postgres:postgres@postgres:5432/smartvault
SENTRY_DSN=  # Optional in dev
SENTRY_ENVIRONMENT=development

# Staging
environment=staging
DATABASE_URL=postgresql+psycopg://user:pass@staging-db.internal:5432/smartvault
SENTRY_DSN=https://key@sentry.io/project
SENTRY_ENVIRONMENT=staging
SENTRY_TRACES_SAMPLE_RATE=1.0  # 100% in staging

# Production
environment=production
DATABASE_URL=postgresql+psycopg://user:pass@prod-db.internal:5432/smartvault
SENTRY_DSN=https://key@sentry.io/project
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1  # 10% in prod
```

---

## Production Checklist

### Pre-Deployment

**Security:**
- [ ] `SECRET_KEY` is unique and cryptographically random
- [ ] `SENTRY_SEND_DEFAULT_PII=false` (verify PII protection)
- [ ] Database credentials use strong passwords
- [ ] Redis is password-protected (if exposed)
- [ ] HTTPS/TLS enabled
- [ ] CORS configured appropriately
- [ ] Rate limiting enabled

**Configuration:**
- [ ] All required environment variables set
- [ ] Database connection tested
- [ ] Redis connection tested
- [ ] SMTP credentials configured (if using email)
- [ ] Sentry DSN configured
- [ ] Log aggregation configured

**Database:**
- [ ] Migrations reviewed and tested
- [ ] Database backup strategy in place
- [ ] Connection pooling configured
- [ ] Indexes reviewed for performance

**Observability:**
- [ ] Prometheus accessible to monitoring system
- [ ] Grafana dashboards configured
- [ ] Sentry alerts configured
- [ ] Log aggregation working
- [ ] Health check endpoints responding

**Performance:**
- [ ] Database queries optimized
- [ ] Connection pool sized appropriately
- [ ] Redis caching configured
- [ ] Static assets served efficiently

**Testing:**
- [ ] All tests passing
- [ ] Load testing completed
- [ ] Smoke tests prepared
- [ ] Rollback plan documented

---

## Docker Deployment

### Build Production Image

**1. Create production Dockerfile (if not exists):**
```dockerfile
# Dockerfile.prod
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app/ ./app/
COPY alembic.ini .

# Create non-root user
RUN useradd -m -u 1000 smartvault && \
    chown -R smartvault:smartvault /app

USER smartvault

# Run migrations and start server
CMD alembic upgrade head && \
    uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**2. Build image:**
```bash
docker build -f Dockerfile.prod -t smartvault-api:v1.0.0 .
```

**3. Tag for registry:**
```bash
docker tag smartvault-api:v1.0.0 registry.example.com/smartvault-api:v1.0.0
docker tag smartvault-api:v1.0.0 registry.example.com/smartvault-api:latest
```

**4. Push to registry:**
```bash
docker push registry.example.com/smartvault-api:v1.0.0
docker push registry.example.com/smartvault-api:latest
```

### Docker Compose (Production)

**docker-compose.prod.yml:**
```yaml
version: '3.8'

services:
  api:
    image: registry.example.com/smartvault-api:v1.0.0
    restart: unless-stopped
    env_file:
      - .env.production
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: smartvault
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d smartvault"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  prometheus:
    image: prom/prometheus:v2.48.0
    restart: unless-stopped
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'

  grafana:
    image: grafana/grafana:10.2.2
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
      - GF_ANALYTICS_REPORTING_ENABLED=false
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning:ro

volumes:
  postgres-data:
  redis-data:
  prometheus-data:
  grafana-data:
```

**Deploy:**
```bash
docker-compose -f docker-compose.prod.yml up -d
```

---

## Environment Configuration

### Required Environment Variables

**Application:**
```bash
# Core
environment=production
SECRET_KEY=<generate-with-openssl-rand-hex-32>
DATABASE_URL=postgresql+psycopg://user:pass@host:5432/smartvault
REDIS_URL=redis://:password@host:6379/0

# Security
ACCESS_TOKEN_EXPIRE_MINUTES=30
RATE_LIMIT_OTP_REQ_PER_MIN=3
RATE_LIMIT_LOGIN_REQ_PER_MIN=5
```

**Observability:**
```bash
# Sentry
SENTRY_DSN=https://key@o123456.ingest.sentry.io/7654321
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1
SENTRY_SEND_DEFAULT_PII=false  # CRITICAL: Always false
```

**Email (if applicable):**
```bash
EMAIL_BACKEND=smtp
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=<sendgrid-api-key>
SMTP_FROM_EMAIL=noreply@smartvault.com
SMTP_FROM_NAME=SmartVault
```

### Secrets Management

**Option 1: Environment files (simple)**
```bash
# .env.production (never commit!)
SECRET_KEY=abc123...
DATABASE_URL=postgresql://...
```

**Option 2: Docker Secrets (recommended)**
```yaml
# docker-compose.prod.yml
services:
  api:
    secrets:
      - db_password
      - secret_key
    environment:
      DATABASE_URL: postgresql://user:${DB_PASSWORD}@host/db
      SECRET_KEY_FILE: /run/secrets/secret_key

secrets:
  db_password:
    file: ./secrets/db_password.txt
  secret_key:
    file: ./secrets/secret_key.txt
```

**Option 3: Cloud provider secrets (production)**
- AWS Secrets Manager
- Azure Key Vault
- GCP Secret Manager
- HashiCorp Vault

---

## Database Migrations

### Migration Strategy

**Zero-Downtime Migration Pattern:**

**1. Additive changes** (safe):
```python
# Add nullable column
def upgrade():
    op.add_column('vaults', sa.Column('shared_with', sa.JSON(), nullable=True))
```

**2. Breaking changes** (requires coordination):
```python
# Step 1: Add new column
def upgrade_step_1():
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=True))

# Step 2: Deploy code that writes to both old and new
# (Deploy application code)

# Step 3: Backfill data
def upgrade_step_2():
    op.execute("UPDATE users SET email_verified = true WHERE confirmed_at IS NOT NULL")

# Step 4: Make column non-nullable
def upgrade_step_3():
    op.alter_column('users', 'email_verified', nullable=False)

# Step 5: Remove old column
def upgrade_step_4():
    op.drop_column('users', 'confirmed_at')
```

### Running Migrations in Production

**Manual migration (recommended for production):**

**1. Backup database:**
```bash
pg_dump -h prod-db.internal -U user smartvault > backup_$(date +%Y%m%d_%H%M%S).sql
```

**2. Test migration on staging:**
```bash
# Restore prod backup to staging
psql -h staging-db -U user smartvault < backup.sql

# Run migration on staging
docker-compose exec api alembic upgrade head

# Test application on staging
curl https://staging.smartvault.com/api/v1/health/detailed
```

**3. Run migration in production (during maintenance window):**
```bash
# Connect to production
docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

# Verify
docker-compose -f docker-compose.prod.yml exec api alembic current
```

**4. Verify application health:**
```bash
curl https://api.smartvault.com/api/v1/health/detailed
```

**Automatic migration (container startup):**
```dockerfile
# Dockerfile.prod
CMD alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

⚠️ **WARNING:** Automatic migrations risk downtime if migration fails. Use only for non-critical environments.

---

## Health Checks & Monitoring

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: smartvault-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: smartvault-api
  template:
    metadata:
      labels:
        app: smartvault-api
    spec:
      containers:
      - name: api
        image: registry.example.com/smartvault-api:v1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: smartvault-secrets
              key: database-url
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: smartvault-secrets
              key: secret-key
        
        # Liveness probe - restart if unhealthy
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 30
          timeoutSeconds: 5
          failureThreshold: 3
        
        # Readiness probe - remove from load balancer if not ready
        readinessProbe:
          httpGet:
            path: /api/v1/health/detailed
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
```

### Load Balancer Health Checks

**AWS ALB:**
```json
{
  "HealthCheckProtocol": "HTTP",
  "HealthCheckPath": "/api/v1/health/detailed",
  "HealthCheckIntervalSeconds": 30,
  "HealthCheckTimeoutSeconds": 5,
  "HealthyThresholdCount": 2,
  "UnhealthyThresholdCount": 3
}
```

**NGINX:**
```nginx
upstream smartvault_api {
    server api1.internal:8000 max_fails=3 fail_timeout=30s;
    server api2.internal:8000 max_fails=3 fail_timeout=30s;
    server api3.internal:8000 max_fails=3 fail_timeout=30s;
}

server {
    location /api {
        proxy_pass http://smartvault_api;
        
        # Health check
        health_check uri=/api/v1/health/detailed interval=10s fails=3 passes=2;
    }
}
```

---

## Scaling Considerations

### Horizontal Scaling

SmartVault is **stateless** and can scale horizontally:

**1. Run multiple API containers:**
```yaml
# docker-compose.prod.yml
services:
  api:
    deploy:
      replicas: 3
```

**2. Use load balancer:**
- AWS ALB
- NGINX
- Traefik
- Kubernetes Service

**3. Shared state:**
- Database: Single PostgreSQL instance (or read replicas)
- Cache: Single Redis instance (or Redis Cluster)
- Sessions: Stateless JWT tokens (no session storage)

### Vertical Scaling

**Database:**
- Monitor connection pool usage
- Scale database instance size
- Add read replicas for read-heavy workloads

**Redis:**
- Monitor memory usage
- Scale instance size
- Use Redis Cluster for large datasets

**API:**
- Monitor CPU/memory usage
- Increase container resources
- Tune uvicorn workers:
  ```bash
  uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000
  ```

### Performance Optimization

**Database connection pooling:**
```python
# app/infrastructure/db/session.py
engine = create_engine(
    DATABASE_URL,
    pool_size=20,           # Connections per instance
    max_overflow=10,        # Additional connections
    pool_pre_ping=True,     # Verify connections
    pool_recycle=3600,      # Recycle after 1 hour
)
```

**Redis connection pooling:**
```python
# app/infrastructure/cache/redis_client.py
redis_client = Redis.from_url(
    REDIS_URL,
    max_connections=50,
    decode_responses=True,
)
```

---

## Rollback Procedures

### Application Rollback

**Docker:**
```bash
# Rollback to previous version
docker-compose -f docker-compose.prod.yml pull smartvault-api:v0.9.0
docker-compose -f docker-compose.prod.yml up -d api

# Verify
curl https://api.smartvault.com/api/v1/health
```

**Kubernetes:**
```bash
# Rollback deployment
kubectl rollout undo deployment/smartvault-api

# Check status
kubectl rollout status deployment/smartvault-api
```

**Git-based:**
```bash
# Checkout previous release tag
git checkout v0.9.0

# Rebuild and deploy
docker build -t smartvault-api:rollback .
docker-compose -f docker-compose.prod.yml up -d api
```

### Database Rollback

**Rollback last migration:**
```bash
# Backup first!
pg_dump -h prod-db -U user smartvault > backup_before_rollback.sql

# Rollback one migration
docker-compose exec api alembic downgrade -1

# Verify
docker-compose exec api alembic current
```

**Rollback to specific version:**
```bash
# Rollback to specific revision
docker-compose exec api alembic downgrade abc123

# Verify
docker-compose exec api alembic current
```

**Full database restore:**
```bash
# Stop application
docker-compose -f docker-compose.prod.yml stop api

# Restore database
psql -h prod-db -U user smartvault < backup_20260212.sql

# Start application
docker-compose -f docker-compose.prod.yml start api
```

---

## Disaster Recovery

### Backup Strategy

**Database backups:**
```bash
# Daily automated backup
0 2 * * * pg_dump -h prod-db -U user smartvault | gzip > /backups/smartvault_$(date +\%Y\%m\%d).sql.gz

# Retention: Keep 7 daily, 4 weekly, 12 monthly
```

**Redis backups:**
```bash
# Redis RDB snapshot
docker-compose exec redis redis-cli BGSAVE

# Copy RDB file
docker cp smartvault-redis:/data/dump.rdb ./backups/redis_$(date +%Y%m%d).rdb
```

**Application state:**
- Docker images versioned and pushed to registry
- Git tags for all releases
- Infrastructure as Code (Terraform/CloudFormation)

### Recovery Procedures

**Scenario 1: Database corruption**
```bash
# 1. Stop API
docker-compose -f docker-compose.prod.yml stop api

# 2. Restore latest backup
gunzip -c /backups/smartvault_20260212.sql.gz | psql -h prod-db -U user smartvault

# 3. Verify data integrity
psql -h prod-db -U user smartvault -c "SELECT COUNT(*) FROM users;"

# 4. Start API
docker-compose -f docker-compose.prod.yml start api

# 5. Verify health
curl https://api.smartvault.com/api/v1/health/detailed
```

**Scenario 2: Complete infrastructure failure**
```bash
# 1. Provision new infrastructure (Terraform/CloudFormation)
terraform apply

# 2. Restore database
psql -h new-db -U user smartvault < backup_20260212.sql

# 3. Deploy application
docker-compose -f docker-compose.prod.yml up -d

# 4. Update DNS to point to new infrastructure
# 5. Verify health
```

### RTO/RPO Targets

| Scenario | RTO (Recovery Time) | RPO (Data Loss) |
|----------|---------------------|-----------------|
| API container failure | < 5 minutes | 0 (stateless) |
| Database failover | < 15 minutes | 0 (replicas) |
| Complete region failure | < 2 hours | < 1 hour |

---

## Monitoring & Alerting

### Critical Alerts

**Application:**
- API error rate > 5%
- API latency p95 > 1s
- Health check failing

**Database:**
- Connection pool exhausted
- Query latency > 500ms
- Replication lag > 10s

**Infrastructure:**
- CPU > 80%
- Memory > 85%
- Disk > 90%

**Security:**
- PIN lockout rate spike
- Auth failure rate spike
- Unusual traffic patterns

### Alert Configuration

**Grafana alert example:**
```yaml
# grafana/provisioning/alerting/alerts.yml
groups:
  - name: smartvault_alerts
    interval: 1m
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} (threshold: 0.05)"
```

---

## Next Steps

- Review [SECURITY.md](SECURITY.md) for security best practices
- Check [OBSERVABILITY.md](OBSERVABILITY.md) for monitoring setup
- See [releases.md](releases.md) for release process