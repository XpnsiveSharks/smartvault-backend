# Internal API Surfaces

Two non-public surfaces live under `/api/internal`:

- `internal/ops`: runtime health, safety, abuse signals. Audience: engineers/on-call/automation.
- `internal/admin`: analytics, KPIs, security views, exports. Audience: privileged human admins/compliance.

Boundary rules (enforced):
- API handlers stay thin: routing + guards only. No direct DB/Redis/Sentry calls here.
- Authorization is centralized in `app/api/internal/dependencies.py` using authenticators from `app/infrastructure/security/internal_auth.py`.
- Rate limiting is centralized via `RateLimiter`; stricter defaults for admin.
- Admin surface is always authenticated; DEV_AUTH_BYPASS does **not** bypass admin.
- Audit logging is mandatory for admin; emitted via `AdminAuditMiddleware` to the structured logger in `app/infrastructure/logging/audit.py`. Sensitive headers are redacted.

Adding new endpoints:
- Put ops routes under `app/api/internal/ops/` and admin routes under `app/api/internal/admin/`.
- Reuse shared guards via router-level `dependencies=[Depends(admin_guard)]` (admin) or `dependencies=[Depends(_ops_guard)]` (ops).
- Keep business logic in application layer; import application services instead of hitting infrastructure directly.
