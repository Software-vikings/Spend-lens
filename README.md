# SpendLens

**An explainable business-spending intelligence prototype.**

SpendLens analyses synthetic company expense transactions to surface unusual patterns and potential cost inefficiencies for human review. It is an independent portfolio project and is not connected to Pleo, a bank or any real financial institution.

> **Demo data only:** all transactions are synthetic and denominated in EUR. Findings are screening signals, not fraud verdicts, policy determinations or proof of savings.

## What it does

- Generates reproducible synthetic company expense records and stores them in SQLite.
- Screens unusually high transactions against merchant/category peers using median absolute deviation (MAD).
- Identifies recurring-payment changes, merchant amount drift, duplicate candidates and fragmented-purchase patterns.
- Analyses monthly department spend and spend per employee using explicit headcount inputs.
- Exposes authenticated FastAPI endpoints for summary, analytics, transactions, findings and analyst review.
- Provides a browser dashboard with spend overview, findings queue, transaction explorer and review history.
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
- `GET /v1/summary` — spend and finding summary
- `GET /v1/analytics/overview` — monthly, department and category aggregates
- `GET /v1/transactions` — searchable and paginated transactions
- `GET /v1/findings` — findings queue
- `GET /v1/findings/{finding_id}` — finding detail and review history
- `PATCH /v1/findings/{finding_id}/review` — analyst review update

All `/v1/*` endpoints require an API key. Viewer role is read-only; analyst role can update review state. The admin role currently has the same application permissions as analyst.

## Tests and CI

Run locally with `PYTHONPATH=src pytest -q`. GitHub Actions checks out the repository, installs dependencies, runs the tests, executes the synthetic pipeline and validation, and compiles Python source. **The hosted CI run for source commit `2900258` passed all steps**, including tests, pipeline and validation. Subsequent documentation updates were also checked by CI. [View GitHub Actions](https://github.com/Software-vikings/Spend-lens/actions).

## Power BI

The pipeline generates Power BI-ready CSV exports under `reports/`. See [Power BI build guide](powerbi/POWER_BI_BUILD_GUIDE.md) for the recommended semantic model, DAX measures and report pages. A native `.pbix` file is not included.

## Employer showcase readiness

**Current weighted estimate: 73%.** The complete application source, dashboard, tests, SQL, CI configuration, Docker configuration and project documentation are now present in this GitHub repository. Hosted CI has passed on the source commit. Remaining showcase work is tracked in [the execution tracker](EMPLOYER_SHOWCASE_READINESS.md#execution-tracker--22-october-2026): manual fresh-clone/API/dashboard verification, genuine screenshots, setup-instruction verification, Docker runtime, historical-only validation, Power BI and security checks.

See [EMPLOYER_SHOWCASE_READINESS.md](EMPLOYER_SHOWCASE_READINESS.md) for the scoring rubric, evidence and acceptance criteria.

## Evaluation limitations

The validation dataset is synthetic and includes injected scenarios authored alongside the detector. Precision/recall figures measure recovery of those synthetic high-value outlier scenarios only; they do not estimate real-world fraud performance. The current peer baseline is in-sample and can use later-dated peer transactions, creating temporal leakage. A flag is not proof of fraud, policy violation, waste or supplier overcharging.

## Security boundaries

This is a portfolio prototype, not a production-certified financial control platform. API keys are static configuration values, rate limiting is in-memory and per process, and there is no tenant isolation, SSO/MFA, formal penetration test or verified cloud deployment. Do not expose publicly or load real financial data without additional security, privacy, operational and legal review. See [SECURITY.md](SECURITY.md).
