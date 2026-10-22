# SpendLens

**An early-stage automated expense-decision prototype under rebuild.**

SpendLens is being rebuilt to evaluate synthetic expense claims against explicit, configurable company policy and return explainable approval, rejection, review or insufficient-evidence outcomes. The current codebase is a foundation—not yet that complete decision system. It is an independent portfolio project and is not connected to Pleo, a bank or any real financial institution.

> **Demo data only:** all transactions are synthetic and denominated in EUR. Findings are screening signals, not fraud verdicts, policy determinations or proof of savings.

## Current implementation status

The repository's main-branch foundation generates synthetic transactions, screens statistical/heuristic signals and serves a basic overview/findings/transactions dashboard. The rebuild branch now adds an initial deterministic policy evaluator, a synthetic versioned policy, persisted decision APIs and an expense-decision workbench. **This is a first vertical slice, not a complete product:** claim/evidence domain modelling, policy management, authorised overrides, end-to-end lifecycle and the full state-driven dashboard rebuild remain open. Existing findings are not approval decisions.

The product scope, code audit, target decision contract, dashboard acceptance criteria and phased rebuild are documented in [PRODUCT_SCOPE_AND_REBUILD_PLAN.md](PRODUCT_SCOPE_AND_REBUILD_PLAN.md). The former 73% showcase score has been withdrawn because it measured repository completeness rather than the intended product outcome. Current evidence-based product completion baseline: **24/100**.

## Existing foundation (not the finished product)

- Generates reproducible synthetic company expense records and stores them in SQLite.
- Screens unusually high transactions against merchant/category peers using median absolute deviation (MAD); this is a risk signal, not a policy decision.
- Identifies recurring-payment changes, merchant amount drift, duplicate candidates and fragmented-purchase patterns.
- Analyses monthly department spend and spend per employee using explicit headcount inputs.
- Exposes authenticated FastAPI endpoints for summary, analytics, transactions, findings and analyst review.
- Provides a basic browser dashboard with spend overview, findings queue, transaction explorer and review history.
- Includes an initial month/department/category cross-filter implementation; browser-level behaviour is not yet verified and the UI is scheduled for a state-driven rebuild.
- Produces SQL analytics, Power BI-ready CSV exports and a multi-seed validation report.

## Architecture

```text
Synthetic generator
       |
       v
Validation -> SQLite database -> Detection / insight screens
                                      |
                                      v
                                Persistent findings
                                      |
                         +------------+------------+
                         |                         |
                      FastAPI                 Power BI exports
                         |
                         v
                 Browser analyst dashboard
```

## Run locally

Requires Python 3.10+.

```bash
git clone https://github.com/Software-vikings/Spend-lens.git
cd Spend-lens

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

PYTHONPATH=src python -m spendlens.pipeline
PYTHONPATH=src python -m spendlens.validation
PYTHONPATH=src pytest -q
```

Create a long random API key (at least 24 characters), then start the API:

```bash
export SPENDLENS_API_KEYS="YOUR_LONG_RANDOM_KEY:analyst"
PYTHONPATH=src uvicorn spendlens.api:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 and enter the API key. The dashboard stores it in the current browser tab's session storage. Do not commit real keys or use real employee/financial records.

## API

- `GET /health` — health check
- `GET /v1/summary` — spend and finding summary; accepts `month`, `department` and `category` filters
- `GET /v1/analytics/overview` — monthly, department and category aggregates; accepts the same filters
- `GET /v1/transactions` — searchable and paginated transactions; accepts the same filters
- `POST /v1/expenses/evaluate` — analyst-only evaluation against the versioned synthetic demo policy; persists the decision
- `GET /v1/decisions` — persisted decision history, filterable by outcome
- `GET /v1/decisions/{decision_id}` — decision, input and rule-level explanation
- `GET /v1/findings` — findings queue
- `GET /v1/findings/{finding_id}` — finding detail and review history
- `PATCH /v1/findings/{finding_id}/review` — analyst review update

All `/v1/*` endpoints require an API key. Viewer role is read-only; analyst role can evaluate expenses and update finding review state. Expense evaluation is an initial vertical slice using the example policy; there is not yet a policy-management UI or complete claim lifecycle. The admin role currently has the same application permissions as analyst. The current cross-filtering applies to transaction spend, analytics and the transaction ledger. Finding counts and the findings list remain workspace-wide until every finding type has a reliable transaction-level relationship.

## Tests and CI

Run locally with `PYTHONPATH=src pytest -q`. GitHub Actions checks out the repository, installs dependencies, runs the tests, executes the synthetic pipeline and validation, compiles Python source, and checks dashboard JavaScript syntax. **The hosted CI run for source commit `2900258` passed all steps**, including tests, pipeline and validation. Subsequent documentation updates were also checked by CI. [View GitHub Actions](https://github.com/Software-vikings/Spend-lens/actions).

## Power BI

The pipeline generates Power BI-ready CSV exports under `reports/`. See [Power BI build guide](powerbi/POWER_BI_BUILD_GUIDE.md) for the recommended semantic model, DAX measures and report pages. A native `.pbix` file is not included.

## Product completion status

**Baseline: 24/100 against the intended automated expense-decision product.** The policy model, first-class claim/evidence model and deterministic decision engine are not implemented. Existing charts and anomaly screens do not meet the product objective. See [PRODUCT_SCOPE_AND_REBUILD_PLAN.md](PRODUCT_SCOPE_AND_REBUILD_PLAN.md) for the weighted rubric and phased exit criteria. This score is not production readiness.

## Evaluation limitations

The validation dataset is synthetic and includes injected scenarios authored alongside the detector. Precision/recall figures measure recovery of those synthetic high-value outlier scenarios only; they do not estimate real-world fraud performance. The current peer baseline is in-sample and can use later-dated peer transactions, creating temporal leakage. A flag is not proof of fraud, policy violation, waste or supplier overcharging.

## Security boundaries

This is a portfolio prototype, not a production-certified financial control platform. API keys are static configuration values, rate limiting is in-memory and per process, and there is no tenant isolation, SSO/MFA, formal penetration test or verified cloud deployment. Do not expose publicly or load real financial data without additional security, privacy, operational and legal review. See [SECURITY.md](SECURITY.md).
