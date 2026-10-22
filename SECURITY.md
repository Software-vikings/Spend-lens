# Security and data handling

SpendLens is an upload-first transaction-screening prototype. This document distinguishes the controls present in the current code from the controls needed before handling confidential corporate financial data in a production service.

## Upload processing

- POST /v1/imports/analyze accepts CSV and XLSX uploads, with a 10 MB file-size limit and 10,000-row limit.
- The route reads and analyses the file during the request and returns a screening result. Multipart upload handling may temporarily spool request data to server-managed temporary storage before the route reads it; the uploaded file is closed after processing.
- Uploaded records are not inserted into the application database and no import history is retained by this workflow. Do not interpret that as a guarantee that bytes never touch disk: the multipart framework or operating system may use temporary storage during request handling.
- The server receives the file contents and can access them during processing. "Not persisted" does not mean "never transmitted to or visible to the hosting server."
- The endpoint is currently available without a user login. It has a per-IP upload request budget, but there is no organisation identity or tenant-level access control on the upload workflow.

## API controls

- API-key role checks remain on the legacy policy, decision, claim, finding and audit routes.
- Constant-time API-key comparison, parameterised SQL and Pydantic input validation are used on the protected API routes.
- Responses include security headers and request IDs.
- Request limits are separated by request type: upload analysis (10/minute), state-changing API requests (60/minute), and read-only API requests (600/minute). Static assets and /health are not throttled by the API limiter.
- A 429 response includes Retry-After seconds.
- Rate limiting is in-memory and process-local. It is not shared across workers or instances and is not a substitute for an edge/WAF limit.

## Known production gaps

- No user login, SSO/MFA, organisation membership or tenant isolation for uploaded datasets.
- No persistent upload storage, user data-retention controls, deletion workflow or export-access controls because uploads are currently transient.
- No managed secret rotation/revocation for the legacy API keys.
- No distributed rate limiting, WAF, formal penetration test, dependency audit, backup/restore exercise or independent security review.
- No verified production deployment, operational monitoring or incident-response process.
- No source integration to verify bank/card settlement, merchant identity or receipt authenticity.

## Deployment guidance

The upload interface is functional as a portfolio demonstration, but do not expose it as a production financial-data service until the organisation has approved its hosting and privacy model and implemented authentication, tenant isolation, transport security, monitoring and a security review. For any real deployment, use an approved private environment and test with authorised data only.
