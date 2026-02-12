# API Reference

This document provides a comprehensive reference for the SmartVault API, including authentication, endpoints, request/response formats, and conventions.

---

## Table of Contents

1. [API Overview](#api-overview)
2. [Authentication](#authentication)
3. [Versioning](#versioning)
4. [Base URLs](#base-urls)
5. [Common Headers](#common-headers)
6. [Response Formats](#response-formats)
7. [Error Handling](#error-handling)
8. [Endpoints](#endpoints)
9. [Rate Limiting](#rate-limiting)
10. [WebSocket API](#websocket-api)

---

## API Overview

SmartVault provides a **RESTful JSON API** with the following characteristics:

- **Protocol:** HTTPS only (HTTP redirects to HTTPS in production)
- **Format:** JSON for all requests and responses
- **Authentication:** JWT Bearer tokens
- **Versioning:** URL-based (e.g., `/api/v1/...`)
- **Rate Limiting:** Redis-based with standard HTTP headers
- **CORS:** Configured per environment

**Design Principles:**
- RESTful resource naming
- Consistent error responses
- Idempotent operations where possible
- Clear HTTP status codes
- Request correlation via `X-Request-ID`

---

## Authentication

### JWT Bearer Token

**All protected endpoints require authentication via JWT Bearer token.**

**Authentication Flow:**

**1. User Registration**
```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "user_id": 123,
  "email": "user@example.com",
  "created_at": "2026-02-12T10:30:00Z"
}
```

**2. User Login**
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**3. Use Access Token**
```http
GET /api/v1/users/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**4. Refresh Access Token**
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### Token Expiration

| Token Type | Lifetime | Renewable |
|------------|----------|-----------|
| **Access Token** | 30 minutes | No (use refresh token) |
| **Refresh Token** | 7 days | Yes (on refresh) |

---

## Versioning

**Strategy:** URL-based versioning

**Current Version:** `v1`

**URL Pattern:**
```
https://api.smartvault.com/api/v1/{resource}
```

**Version Lifecycle:**
- `v1` — Current stable version
- `v2` — Future version (when introduced)
- `v1` will be supported for at least 12 months after `v2` release

**Breaking Changes:**
- New API version required
- Documented in `CHANGELOG.md`
- Migration guide provided

**Non-Breaking Changes:**
- Added optional fields
- New endpoints
- Deprecated (but not removed) fields

---

## Base URLs

| Environment | Base URL |
|-------------|----------|
| **Development** | `http://localhost:8000/api/v1` |
| **Staging** | `https://staging-api.smartvault.com/api/v1` |
| **Production** | `https://api.smartvault.com/api/v1` |

---

## Common Headers

### Request Headers

| Header | Required | Description |
|--------|----------|-------------|
| `Authorization` | Yes* | Bearer token for authentication (`Bearer <token>`) |
| `Content-Type` | Yes** | Must be `application/json` for POST/PUT/PATCH |
| `X-Request-ID` | No | Client-provided request ID for tracing |

\* Required for authenticated endpoints  
\** Required for requests with body

### Response Headers

| Header | Always Present | Description |
|--------|----------------|-------------|
| `Content-Type` | Yes | `application/json` |
| `X-Request-ID` | Yes | Request correlation ID |
| `X-RateLimit-Limit` | On limited endpoints | Maximum requests allowed |
| `X-RateLimit-Remaining` | On limited endpoints | Remaining requests |
| `X-RateLimit-Reset` | On limited endpoints | Unix timestamp when limit resets |

---

## Response Formats

### Success Response

**Single Resource:**
```json
{
  "id": "vault-123",
  "status": "locked",
  "owner_id": 456,
  "created_at": "2026-02-12T10:30:00Z"
}
```

**Collection:**
```json
{
  "items": [
    {"id": "vault-1", "status": "locked"},
    {"id": "vault-2", "status": "unlocked"}
  ],
  "total": 2,
  "page": 1,
  "per_page": 20
}
```

**Action Result:**
```json
{
  "status": "success",
  "message": "Vault unlocked successfully",
  "vault_id": "vault-123"
}
```

### Pagination

**Request:**
```http
GET /api/v1/vaults?page=2&per_page=20
```

**Response:**
```json
{
  "items": [...],
  "total": 45,
  "page": 2,
  "per_page": 20,
  "pages": 3
}
```

---

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "VAULT_NOT_FOUND",
    "message": "Vault with ID 'vault-123' not found",
    "details": {
      "vault_id": "vault-123"
    }
  },
  "request_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

### HTTP Status Codes

| Code | Meaning | Usage |
|------|---------|-------|
| `200` | OK | Successful GET/PUT/PATCH |
| `201` | Created | Successful POST (resource created) |
| `204` | No Content | Successful DELETE |
| `400` | Bad Request | Invalid input, validation error |
| `401` | Unauthorized | Missing or invalid authentication |
| `403` | Forbidden | Authenticated but not authorized |
| `404` | Not Found | Resource doesn't exist |
| `409` | Conflict | Duplicate resource, conflicting state |
| `422` | Unprocessable Entity | Semantic validation error |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server error (reported to Sentry) |
| `503` | Service Unavailable | Temporary downtime |

### Error Codes

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `UNAUTHORIZED` | 401 | Authentication required |
| `INVALID_TOKEN` | 401 | Token is invalid or expired |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `VAULT_NOT_FOUND` | 404 | Vault doesn't exist |
| `USER_NOT_FOUND` | 404 | User doesn't exist |
| `DUPLICATE_EMAIL` | 409 | Email already registered |
| `INVALID_PIN` | 401 | PIN is incorrect |
| `VAULT_LOCKED_OUT` | 429 | Too many unlock attempts |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

### Validation Errors

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": {
      "fields": {
        "email": ["Invalid email format"],
        "password": ["Password must be at least 8 characters"]
      }
    }
  }
}
```

---

## Endpoints

### Health & Monitoring

#### Get Liveness Status

**Endpoint:** `GET /api/v1/health`  
**Authentication:** None  
**Description:** Check if API is running (for load balancer / liveness probe)

**Response:**
```json
{
  "status": "healthy"
}
```

---

#### Get Detailed Health Status

**Endpoint:** `GET /api/v1/health/detailed`  
**Authentication:** None  
**Description:** Check API readiness with dependency health (for readiness probe)

**Response (Healthy):**
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

**Response (Unhealthy):**
```json
{
  "status": "unhealthy",
  "checks": {
    "database": {
      "status": "unhealthy",
      "error": "Connection refused"
    }
  }
}
```

---

### Authentication

#### Register User

**Endpoint:** `POST /api/v1/auth/register`  
**Authentication:** None

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (201 Created):**
```json
{
  "user_id": 123,
  "email": "user@example.com",
  "created_at": "2026-02-12T10:30:00Z"
}
```

**Errors:**
- `409 DUPLICATE_EMAIL` — Email already registered
- `400 VALIDATION_ERROR` — Invalid input

---

#### Login

**Endpoint:** `POST /api/v1/auth/login`  
**Authentication:** None

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Errors:**
- `401 UNAUTHORIZED` — Invalid credentials
- `429 RATE_LIMIT_EXCEEDED` — Too many login attempts

---

#### Refresh Token

**Endpoint:** `POST /api/v1/auth/refresh`  
**Authentication:** None

**Request:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Errors:**
- `401 INVALID_TOKEN` — Refresh token is invalid or expired

---

### Users

#### Get Current User

**Endpoint:** `GET /api/v1/users/me`  
**Authentication:** Required

**Response (200 OK):**
```json
{
  "id": 123,
  "email": "user@example.com",
  "created_at": "2026-01-15T08:20:00Z"
}
```

---

### Vaults

#### Provision Vault

**Endpoint:** `POST /api/v1/vaults`  
**Authentication:** Required

**Request:**
```json
{
  "vault_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Home Safe"
}
```

**Response (201 Created):**
```json
{
  "vault_id": "vault-123",
  "vault_uuid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Home Safe",
  "owner_id": 123,
  "status": "locked",
  "created_at": "2026-02-12T10:30:00Z"
}
```

**Errors:**
- `409 CONFLICT` — Vault UUID already registered

---

#### Get Vault Status

**Endpoint:** `GET /api/v1/vaults/{vault_id}`  
**Authentication:** Required

**Response (200 OK):**
```json
{
  "vault_id": "vault-123",
  "name": "Home Safe",
  "status": "locked",
  "owner_id": 123,
  "members": [
    {"user_id": 456, "role": "MEMBER"},
    {"user_id": 789, "role": "VIEWER"}
  ],
  "created_at": "2026-02-12T10:30:00Z"
}
```

**Errors:**
- `404 VAULT_NOT_FOUND` — Vault doesn't exist or user has no access
- `403 FORBIDDEN` — User is not a member of this vault

---

#### List User's Vaults

**Endpoint:** `GET /api/v1/vaults`  
**Authentication:** Required

**Response (200 OK):**
```json
{
  "items": [
    {
      "vault_id": "vault-123",
      "name": "Home Safe",
      "status": "locked",
      "role": "OWNER"
    },
    {
      "vault_id": "vault-456",
      "name": "Shared Vault",
      "status": "unlocked",
      "role": "MEMBER"
    }
  ],
  "total": 2
}
```

---

### Vault PIN Management

#### Set Vault PIN

**Endpoint:** `POST /api/v1/vaults/{vault_id}/pin`  
**Authentication:** Required  
**Authorization:** Owner only

**Request:**
```json
{
  "pin": "1234"
}
```

**Response (201 Created):**
```json
{
  "vault_id": "vault-123",
  "status": "pin_set",
  "message": "PIN set successfully"
}
```

**Errors:**
- `403 FORBIDDEN` — Only vault owner can set PIN
- `400 VALIDATION_ERROR` — PIN must be 4-8 digits

---

#### Unlock Vault with PIN

**Endpoint:** `POST /api/v1/vaults/{vault_id}/unlock`  
**Authentication:** Required  
**Authorization:** Owner, Admin, or Member

**Request:**
```json
{
  "pin": "1234"
}
```

**Response (200 OK):**
```json
{
  "vault_id": "vault-123",
  "status": "unlocked",
  "unlocked_at": "2026-02-12T10:35:00Z",
  "unlocked_by": 123
}
```

**Errors:**
- `401 INVALID_PIN` — PIN is incorrect
- `429 VAULT_LOCKED_OUT` — Too many failed attempts (locked for 15 minutes)
- `403 FORBIDDEN` — User role cannot unlock (e.g., VIEWER)

---

#### Remove Vault PIN

**Endpoint:** `DELETE /api/v1/vaults/{vault_id}/pin`  
**Authentication:** Required  
**Authorization:** Owner only

**Response (204 No Content):**
No body

**Errors:**
- `403 FORBIDDEN` — Only vault owner can remove PIN

---

### Vault Membership

#### Add Vault Member

**Endpoint:** `POST /api/v1/vaults/{vault_id}/members`  
**Authentication:** Required  
**Authorization:** Owner or Admin

**Request:**
```json
{
  "user_id": 456,
  "role": "MEMBER"
}
```

**Valid Roles:** `ADMIN`, `MEMBER`, `VIEWER`

**Response (201 Created):**
```json
{
  "vault_id": "vault-123",
  "user_id": 456,
  "role": "MEMBER",
  "added_by": 123,
  "added_at": "2026-02-12T10:40:00Z"
}
```

**Errors:**
- `403 FORBIDDEN` — User cannot manage members
- `404 USER_NOT_FOUND` — User doesn't exist
- `409 CONFLICT` — User is already a member

---

#### Remove Vault Member

**Endpoint:** `DELETE /api/v1/vaults/{vault_id}/members/{user_id}`  
**Authentication:** Required  
**Authorization:** Owner or Admin

**Response (204 No Content):**
No body

**Errors:**
- `403 FORBIDDEN` — User cannot manage members
- `404 NOT_FOUND` — User is not a member

---

#### List Vault Members

**Endpoint:** `GET /api/v1/vaults/{vault_id}/members`  
**Authentication:** Required

**Response (200 OK):**
```json
{
  "items": [
    {
      "user_id": 123,
      "email": "owner@example.com",
      "role": "OWNER",
      "added_at": "2026-02-12T10:00:00Z"
    },
    {
      "user_id": 456,
      "email": "member@example.com",
      "role": "MEMBER",
      "added_at": "2026-02-12T10:40:00Z"
    }
  ],
  "total": 2
}
```

---

## Rate Limiting

### Rate Limit Headers

When rate limits are applied, responses include:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1676203200
```

### Rate Limit Exceeded

**Response (429 Too Many Requests):**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests. Try again in 45 seconds.",
    "details": {
      "retry_after": 45
    }
  }
}
```

**Headers:**
```http
Retry-After: 45
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1676203245
```

### Rate Limits by Endpoint

| Endpoint | Limit | Window |
|----------|-------|--------|
| `POST /api/v1/auth/login` | 5 requests | 1 minute |
| `POST /api/v1/vaults/{id}/unlock` | 5 attempts | 15 minutes |
| All other endpoints | 100 requests | 1 minute |

---

## WebSocket API

### Connection

**URL:** `ws://localhost:8000/api/ws/{client_id}`

**Example:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws/device-abc-123');

ws.onopen = () => {
  console.log('WebSocket connected');
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Received:', message);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('WebSocket disconnected');
};
```

### Message Format

**Unlock Command (Server → Client):**
```json
{
  "type": "unlock_command",
  "vault_id": "vault-123",
  "user_id": 456,
  "timestamp": "2026-02-12T10:45:00Z",
  "signature": "hmac-sha256-signature"
}
```

**Acknowledgment (Client → Server):**
```json
{
  "type": "ack",
  "command_id": "cmd-789",
  "status": "success"
}
```

---

## API Conventions

### Resource Naming

- Use **plural nouns** for collections: `/api/v1/vaults`
- Use **singular IDs** for specific resources: `/api/v1/vaults/{vault_id}`
- Use **nested resources** for relationships: `/api/v1/vaults/{vault_id}/members`

### HTTP Methods

| Method | Purpose | Example |
|--------|---------|---------|
| `GET` | Retrieve resource(s) | `GET /api/v1/vaults` |
| `POST` | Create resource | `POST /api/v1/vaults` |
| `PUT` | Replace resource (full update) | `PUT /api/v1/vaults/{id}` |
| `PATCH` | Update resource (partial) | `PATCH /api/v1/vaults/{id}` |
| `DELETE` | Remove resource | `DELETE /api/v1/vaults/{id}` |

### Idempotency

- `GET`, `PUT`, `DELETE` are **idempotent** (safe to retry)
- `POST` is **not idempotent** (may create duplicates)
- Use idempotency keys for critical POST operations (future enhancement)

### Date/Time Format

**ISO 8601 UTC:**
```json
{
  "created_at": "2026-02-12T10:30:00Z"
}
```

---

## Interactive Documentation

**Swagger UI:** http://localhost:8000/docs  
**ReDoc:** http://localhost:8000/redoc

FastAPI automatically generates interactive API documentation with:
- All endpoints
- Request/response schemas
- Try-it-out functionality
- Authentication support

---

## Client Libraries

### Python

```python
import requests

# Login
response = requests.post(
    "http://localhost:8000/api/v1/auth/login",
    json={"email": "user@example.com", "password": "password123"}
)
tokens = response.json()

# Use access token
headers = {"Authorization": f"Bearer {tokens['access_token']}"}
response = requests.get(
    "http://localhost:8000/api/v1/users/me",
    headers=headers
)
user = response.json()
```

### JavaScript

```javascript
// Login
const loginResponse = await fetch('http://localhost:8000/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'password123'
  })
});
const tokens = await loginResponse.json();

// Use access token
const userResponse = await fetch('http://localhost:8000/api/v1/users/me', {
  headers: {
    'Authorization': `Bearer ${tokens.access_token}`
  }
});
const user = await userResponse.json();
```

---

## Related Documentation

- [Authentication & Security](SECURITY.md)
- [Architecture](ARCHITECTURE.md)
- [Deployment](DEPLOYMENT.md)