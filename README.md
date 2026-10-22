# SpendLens

**Policy-based expense decision and exception-operations prototype.**

SpendLens evaluates submitted expense claims against a versioned, configurable **synthetic demonstration policy**. It returns one of four outcomes—`APPROVE`, `REJECT`, `REVIEW` or `INSUFFICIENT_DATA`—with rule-level explanations, persists decisions, and routes exceptions through an assignment and human-resolution workflow.

This is an independent portfolio project. It is **not** connected to Pleo, a bank, an accounting platform or any real financial institution.

> **Demo-data boundary:** the transaction ledger and example policy are synthetic. Findings and duplicate candidates are screening signals, not proof of fraud, policy violations or savings. Do not use real employee or financial data.

## Implemented capabilities

- Deterministic expense evaluation against versioned policy documents, with explicit rule results and explanations.
- Four distinct decision outcomes; missing or unreliable required information is not silently approved.
- Persisted decisions, claims, submission history and receipt/evidence metadata.
- Decision history with policy and engine version references.
- Policy version creation and activation, with admin-only controls and audit events.
- Exception queue with assignment/reassignment, priority, SLA deadlines, queue-wide metrics, sorting, filtering and pagination.
- Human exception actions: request information, approve or reject. Human resolution history is preserved separately from the original automated outcome; terminal resolutions cannot be overwritten.
- Transaction dashboard with month, department and category filtering; spend charts, ledger search, pagination and transaction detail.
- Findings review workspace and audit trail for policy administration, claim assignment/resolution and finding review actions.
- Exact transaction-to-finding drill-through only where the source finding carries the matching transaction ID.
- API-key roles, input validation, parameterised SQL, request throttling, security headers and database-backed idempotency for expense evaluation.
- Automated tests for decision rules, role access, audit atomicity, exception lifecycle, dashboard aggregates, pagination and concurrent idempotent submissions.

## Decision semantics

| Outcome | Meaning |
|---|---|
| `APPROVE` | Required inputs/evidence are present and the configured policy checks pass. |
| `REJECT` | A configured deterministic hard-stop rule is conclusively violated. |
| `REVIEW` | An exception or ambiguous/risk signal requires human assessment. |
| `INSUFFICIENT_DATA` | Required information is missing or not reliable enough to evaluate. |

An anomaly or duplicate-candidate signal does not, by itself, cause automatic rejection. The included policy is illustrative and must not be represented as any employer's actual policy.

## Run locally

Requires Python 3.10+.

```bash
git clone https://github.com/Software-vikings/Spend-lens.git
cd Spend-lens

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt

PYTHONPATH=src python -m spendlens.pipeline
PYTHONPATH=src python -m spendlens.validation
PYTHONPATH=src pytest -q
```

Configure at least one long random API key (24+ characters) and start the API:

```bash
export SPENDLENS_API_KEYS="YOUR_LONG_RANDOM_KEY:analyst,ANOTHER_LONG_RANDOM_KEY:viewer"
PYTHONPATH=src uvicorn spendlens.api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 and enter the API key. The dashboard retains it in the current browser tab's session storage. Never commit real keys.

## Roles and key API areas

- **Viewer:** read-only access to permitted dashboard, transaction, claim, decision and queue data.
- **Analyst:** expense evaluation, finding review and exception assignment/resolution.
- **Admin:** policy administration and audit-event access, in addition to permitted operational actions.

Key API routes include:

- `GET /health`
- `GET /v1/summary`, `GET /v1/analytics/overview`
- `GET /v1/transactions`, `GET /v1/transactions/{transaction_id}`
- `POST /v1/expenses/evaluate` (supports `Idempotency-Key`)
- `GET /v1/decisions`, `GET /v1/decisions/{decision_id}`
- `GET /v1/claims`, `GET /v1/claims/{claim_id}`
- `GET /v1/exception-queue`
- `POST /v1/claims/{claim_id}/assignment`
- `POST /v1/claims/{claim_id}/resolution`
- `GET /v1/policies`, `POST /v1/policies`, `POST /v1/policies/{policy_id}/{version}/activate`
- `GET /v1/audit-events` (admin-only)
- `GET /v1/findings`, `PATCH /v1/findings/{finding_id}/review`

Consult the route definitions in `src/spendlens/api.py` for request schemas and supported query parameters.

## Verification

The rebuild branch has automated coverage for the API, policy engine, exception workflow, audit history, dashboard aggregates, role permissions, idempotency and concurrent submissions. CI runs tests, the synthetic data pipeline, multi-seed validation, Python compilation and dashboard JavaScript syntax checks.

Automated CI does **not** establish visual/browser acceptance, production security, deployment correctness or real-world policy effectiveness. Browser-based end-to-end verification has not been performed.

## Explicit limitations and production gaps

- Synthetic transactions and a synthetic example policy only; no employer policy discovery or real-world policy validation.
- Receipt handling stores user-entered metadata only. No file upload, OCR, authenticity checks or independent evidence verification.
- Reviewer/assignee names are self-reported; API-key roles are not an enterprise identity system.
- No Pleo, bank, card, ERP or accounting integrations; no payment execution.
- No tenant isolation, SSO/MFA, distributed rate limiting, managed secrets, formal penetration test or independent security review.
- No verified production deployment, Docker runtime validation, backup/restore exercise or operational monitoring.
- Findings are workspace-wide where a trustworthy transaction-level relationship is unavailable; related records are not inferred from matching amounts/dates.
- The audit trail is transactionally written for supported audited actions, but is not cryptographically tamper-evident and does not prove the identity of the named human actor.
- No browser interaction suite or visual regression evidence is claimed.

See [SECURITY.md](SECURITY.md) before running outside a local demo environment. This repository is a portfolio prototype, **not a production-certified financial control platform**.
