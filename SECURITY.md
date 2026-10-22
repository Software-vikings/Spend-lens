# Security baseline and limitations

SpendLens is a local portfolio prototype using synthetic data.

## Controls implemented in the Phase 6/7 build

- API-key authentication for protected API routes.
- Viewer and analyst roles; viewers are read-only.
- Constant-time API-key comparison.
- Parameterized SQL queries and input validation.
- Per-process/per-IP in-memory request throttling.
- Security response headers and structured request logging.
- SQLite WAL mode, foreign-key enforcement, busy timeout and restrictive file permissions where supported.
- Non-root Docker image and hardened Compose defaults.

## Important limitations

- Static API keys are not a substitute for enterprise identity, MFA, key rotation or revocation.
- The in-memory rate limiter is not shared across workers and resets on restart.
- No tenant isolation or row-level authorization.
- No formal penetration test, dependency audit, backup/restore validation or cloud deployment verification.
- Dashboard API keys are held in browser session storage for the current tab; users can inspect their own key with browser developer tools.
- Docker build and runtime were not verified in the development environment.

Do not expose publicly or use real personal or financial data without TLS, stronger identity management, tenant isolation, secret management, monitoring, privacy/legal review and independent security testing.
