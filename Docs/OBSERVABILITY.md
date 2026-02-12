# Observability Guide

This document explains SmartVault's **Tier 1 Observability** implementation: metrics, logging, error tracking, and health monitoring.

---

## Table of Contents

1. [Overview](#overview)
2. [Metrics (Prometheus + Grafana)](#metrics-prometheus--grafana)
3. [Error Tracking (Sentry)](#error-tracking-sentry)
4. [Structured Logging](#structured-logging)
5. [Health Checks](#health-checks)
6. [Request Correlation](#request-correlation)
7. [Common Queries](#common-queries)
8. [Troubleshooting](#troubleshooting)

---

## Overview

SmartVault uses a **multi-layer observability stack** for production monitoring:

| Component | Purpose | Access |
|-----------|---------|--------|
| **Prometheus** | Metrics collection and storage | http://localhost:9090 |
| **Grafana** | Metrics visualization and dashboards | http://localhost:3000 |
| **Sentry** | Error tracking and alerting | Configure via `SENTRY_DSN` |
| **Structlog** | Structured JSON logging | Container logs |
| **Health Endpoints** | Readiness and liveness probes | `/api/v1/health` |

**Design Principles:**
- **Zero PII in metrics or logs** — Sensitive data is redacted
- **Request correlation** — Every request gets a unique ID
- **Low overhead** — Metrics add <1ms per request
- **Production-ready** — Suitable for Kubernetes/ECS deployments

---

## Metrics (Prometheus + Grafana)

### Quick Start

**1. Start services:**
```bash
make dev
```

**2. Access Grafana:**
- URL: http://localhost:3000
- Default credentials: `admin` / `admin`
- Change password on first login

**3. Access Prometheus:**
- URL: http://localhost:9090
- No authentication required (local dev only)

### Available Metrics

SmartVault exposes metrics at **`http://localhost:8000/metrics`** in Prometheus format.

#### HTTP Metrics (Auto-Instrumented)

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total HTTP requests by method, status, endpoint |
| `http_request_duration_seconds` | Histogram | Request latency distribution |
| `http_requests_inprogress` | Gauge | Current number of requests being processed |

**Example:**
```promql
# Average request duration over 5 minutes
rate(http_request_duration_seconds_sum[5m]) 
  / rate(http_request_duration_seconds_count[5m])

# Request rate by endpoint
rate(http_requests_total[1m])

# 95th percentile latency
histogram_quantile(0.95, http_request_duration_seconds_bucket)
```

#### Business Metrics (Custom)

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `vault_unlocks_total` | Counter | `vault_id`, `user_id`, `result` | Vault unlock attempts |
| `vault_unlock_duration_seconds` | Histogram | `vault_id` | Time to unlock vault |
| `vault_pins_set_total` | Counter | `vault_id` | PIN creation events |
| `vault_members_added_total` | Counter | `vault_id`, `role` | Member additions |
| `pin_lockouts_total` | Counter | `vault_id` | PIN lockout events |
| `auth_failures_total` | Counter | `reason` | Authentication failures |
| `smartvault_app_info` | Gauge | `version`, `environment` | Application metadata |

**Example:**
```promql
# Unlock success rate
sum(rate(vault_unlocks_total{result="success"}[5m])) 
  / sum(rate(vault_unlocks_total[5m]))

# Lockout rate
rate(pin_lockouts_total[1h])

# Unlock latency by vault
histogram_quantile(0.95, vault_unlock_duration_seconds_bucket)
```

### Grafana Dashboards

**Pre-configured dashboards** are available in `grafana/provisioning/dashboards/`.

**To add custom dashboards:**
1. Go to Grafana (http://localhost:3000)
2. Click **+** → **Import Dashboard**
3. Paste dashboard JSON or use dashboard ID from grafana.com

**Recommended Community Dashboards:**
- **FastAPI Metrics**: Dashboard ID `14280`
- **Prometheus Stats**: Dashboard ID `3662`

### Setting Up Alerts

**Example: Alert on high unlock failure rate**

**1. Create alert rule in Grafana:**
- Navigate to **Alerting** → **Alert Rules** → **New Alert Rule**
- Name: `High Unlock Failure Rate`
- Query:
  ```promql
  sum(rate(vault_unlocks_total{result="failure"}[5m])) 
    / sum(rate(vault_unlocks_total[5m])) > 0.2
  ```
- Condition: Alert when query returns value > 0.2 (20% failure rate)
- Notification: Configure email/Slack/PagerDuty

**2. Create notification channel:**
- Go to **Alerting** → **Contact Points**
- Add your email or webhook URL

---

## Error Tracking (Sentry)

### Configuration

**1. Get Sentry DSN:**
- Sign up at https://sentry.io
- Create a new project
- Copy the DSN

**2. Configure environment:**
```bash
# .env
SENTRY_DSN=https://your-key@o123456.ingest.sentry.io/7654321
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1    # 10% of transactions
SENTRY_PROFILES_SAMPLE_RATE=0.1  # 10% profiling
SENTRY_SEND_DEFAULT_PII=false     # NEVER set to true
```

**3. Restart services:**
```bash
make restart
```

### What Gets Tracked

**Automatic:**
- Unhandled exceptions
- HTTP 5xx errors
- Request context (method, URL, headers)
- User context (user ID, email — **no passwords or PINs**)
- Server context (environment, release)

**Manual tracking:**
```python
import sentry_sdk

# Capture custom exception
try:
    risky_operation()
except Exception as e:
    sentry_sdk.capture_exception(e)

# Add breadcrumb
sentry_sdk.add_breadcrumb(
    category="vault",
    message="Unlock attempt started",
    level="info",
)

# Set context
sentry_sdk.set_context("vault", {
    "vault_id": vault.id,
    "status": vault.status,
})
```

### PII Protection

**Enforced scrubbing:**
- Password fields
- PIN values
- Token values
- Authorization headers
- Cookies

**Configuration:**
```python
# app/core/sentry.py
sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    send_default_pii=False,  # CRITICAL: Always False
    before_send=scrub_sensitive_data,
)
```

**Never log or send:**
- Raw passwords
- PIN values
- Session tokens
- API keys
- Biometric data

---

## Structured Logging

### Format

**Development (console):**
```
2025-02-12 10:30:45 [info     ] User login successful       user_id=123 request_id=abc-123
```

**Production (JSON):**
```json
{
  "event": "User login successful",
  "level": "info",
  "timestamp": "2025-02-12T10:30:45.123456Z",
  "user_id": 123,
  "request_id": "abc-123",
  "logger": "app.api.v1.auth"
}
```

### Usage

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

# Basic logging
logger.info("vault_unlocked", vault_id=vault.id, user_id=user.id)

# Request context is automatically bound
logger.debug("processing_unlock", vault_status=vault.status)

# Error logging
logger.error("unlock_failed", vault_id=vault.id, error=str(e))
```

### Automatic Context Binding

**Request ID:**
Every HTTP request automatically binds `request_id` to all logs:
```python
# No need to pass request_id manually
logger.info("processing_request")  
# Output includes: request_id=abc-123
```

### Sensitive Field Redaction

**Automatically redacted fields:**
- `password`
- `pin`
- `token`
- `secret`
- `api_key`
- `authorization`

**Example:**
```python
logger.info("user_created", email="user@example.com", password="secret123")
# Output: email="user@example.com" password="[REDACTED]"
```

### Querying Logs

**Docker:**
```bash
# Tail logs
docker compose logs -f api

# Filter by level
docker compose logs api | grep '"level":"error"'

# Filter by request ID
docker compose logs api | grep '"request_id":"abc-123"'
```

**Production (e.g., CloudWatch, Datadog):**
```
# Find all errors for a specific user
level:error user_id:123

# Find slow requests
duration_ms:>1000

# Find vault unlock failures
event:"vault_unlock_failed"
```

---

## Health Checks

### Endpoints

#### Liveness Probe: `/api/v1/health`

**Purpose:** Determine if the application is running.

**Response:**
```json
{
  "status": "healthy"
}
```

**Use Case:** Kubernetes `livenessProbe`, Docker healthcheck

**Example:**
```yaml
# Kubernetes
livenessProbe:
  httpGet:
    path: /api/v1/health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 30
```

---

#### Readiness Probe: `/api/v1/health/detailed`

**Purpose:** Determine if the application is ready to serve traffic.

**Response (healthy):**
```json
{
  "status": "healthy",
  "checks": {
    "database": {
      "status": "healthy",
      "latency_ms": 12.3
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 2.1
    }
  }
}
```

**Response (unhealthy):**
```json
{
  "status": "unhealthy",
  "checks": {
    "database": {
      "status": "unhealthy",
      "error": "Connection refused"
    },
    "redis": {
      "status": "healthy",
      "latency_ms": 1.8
    }
  }
}
```

**Use Case:** Kubernetes `readinessProbe`, load balancer health checks

**Example:**
```yaml
# Kubernetes
readinessProbe:
  httpGet:
    path: /api/v1/health/detailed
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
  failureThreshold: 3
```

---

## Request Correlation

Every HTTP request receives a **unique request ID** for distributed tracing.

### How It Works

**1. Client makes request:**
```bash
curl http://localhost:8000/api/v1/users
```

**2. Server generates request ID:**
```
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

**3. Response includes request ID:**
```
HTTP/1.1 200 OK
X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
```

**4. All logs include request ID:**
```json
{
  "event": "User fetched",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 123
}
```

### Client-Provided Request IDs

Clients can provide their own request ID:
```bash
curl -H "X-Request-ID: my-custom-id" http://localhost:8000/api/users
```

This enables **end-to-end tracing** across multiple services.

---

## Common Queries

### Prometheus

**Request rate:**
```promql
rate(http_requests_total[5m])
```

**Error rate:**
```promql
rate(http_requests_total{status=~"5.."}[5m])
```

**Latency percentiles:**
```promql
histogram_quantile(0.95, http_request_duration_seconds_bucket)
histogram_quantile(0.99, http_request_duration_seconds_bucket)
```

**Unlock success rate:**
```promql
sum(rate(vault_unlocks_total{result="success"}[5m])) 
  / sum(rate(vault_unlocks_total[5m]))
```

**Active lockouts:**
```promql
increase(pin_lockouts_total[1h])
```

### Grafana

**Dashboard panels:**
- **Request Rate**: `rate(http_requests_total[5m])`
- **Error Rate**: `rate(http_requests_total{status=~"5.."}[5m])`
- **Latency (p95)**: `histogram_quantile(0.95, http_request_duration_seconds_bucket)`
- **Unlock Duration (p95)**: `histogram_quantile(0.95, vault_unlock_duration_seconds_bucket)`

---

## Troubleshooting

### Metrics Not Appearing

**1. Check `/metrics` endpoint:**
```bash
curl http://localhost:8000/metrics
```

**2. Verify Prometheus is scraping:**
- Go to http://localhost:9090/targets
- Check if `smartvault-api` target is **UP**

**3. Check Prometheus config:**
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'smartvault'
    static_configs:
      - targets: ['api:8000']
```

**4. Restart Prometheus:**
```bash
docker compose restart prometheus
```

---

### Grafana Can't Connect to Prometheus

**1. Check Prometheus health:**
```bash
curl http://localhost:9090/-/healthy
```

**2. Verify Grafana datasource:**
- Go to http://localhost:3000/datasources
- Check Prometheus URL: `http://prometheus:9090`
- Click **Save & Test**

**3. Check Docker network:**
```bash
docker compose exec grafana ping prometheus
```

---

### Sentry Not Receiving Errors

**1. Verify DSN is set:**
```bash
docker compose exec api env | grep SENTRY_DSN
```

**2. Test error tracking:**
```python
# In Python shell or endpoint
import sentry_sdk
sentry_sdk.capture_message("Test error")
```

**3. Check Sentry project settings:**
- Verify DSN is correct
- Check rate limits
- Review IP allowlists

**4. Check application logs:**
```bash
docker compose logs api | grep -i sentry
```

---

### Request ID Not in Logs

**1. Verify middleware is active:**
```python
# app/main.py
app.add_middleware(RequestIDMiddleware)
```

**2. Check log configuration:**
```python
# app/core/logging.py
setup_logging()  # Must be called on startup
```

**3. Test manually:**
```bash
curl -v http://localhost:8000/api | grep X-Request-ID
```

---

### Logs Missing Context

**1. Ensure logger is bound:**
```python
from app.core.logging import get_logger

logger = get_logger(__name__)  # Correct
# NOT: import logging; logger = logging.getLogger()
```

**2. Check log processor chain:**
```python
# app/core/logging.py
processors=[
    structlog.contextvars.merge_contextvars,  # Required
    # ...
]
```

---

## Next Steps

**Tier 2 Observability (Planned):**
- Custom business dashboards
- SLO/SLI tracking
- Advanced alerting rules
- Distributed tracing (OpenTelemetry)
- Log aggregation (ELK/Datadog)

**Related Documentation:**
- [Architecture](ARCHITECTURE.md) — System design
- [Deployment](DEPLOYMENT.md) — Production deployment
- [Troubleshooting](TROUBLESHOOTING.md) — Common issues