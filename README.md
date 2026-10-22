# SpendLens

**An explainable business-spending intelligence prototype.**

SpendLens analyses synthetic company expenses to surface unusual transactions and potential cost inefficiencies for human review. It is an independent portfolio project; it is not connected to Pleo, a bank or any real financial institution.

## Local implementation status

The complete Phase 7 application has been implemented and tested locally. The full application source, dashboard, tests, SQL, reports and Power BI guidance have **not yet been synced to this GitHub repository**. Until that sync and a clean-clone verification are complete, this repository must not be represented as a runnable release.

## Capabilities implemented locally

- Deterministic synthetic transaction generation and SQLite persistence.
- Peer-group anomaly screening using median absolute deviation (MAD).
- Recurring-payment, merchant-price-drift, duplicate and fragmented-purchase screens.
- Department spend-per-employee analysis.
- FastAPI analytics endpoints, API-key authentication and role-based review permissions.
- Persistent findings, review notes and review-event history.
- Browser-based analyst dashboard and searchable transaction explorer.
- SQL analytics, Power BI-ready exports and multi-seed synthetic validation.

## Local verification

The latest local verification recorded 30 passing automated tests, successful Python compilation and a successful JavaScript syntax check. These results apply to the local project, not to the incomplete GitHub copy. Docker build/runtime and hosted GitHub Actions are not yet verified.

## Employer showcase readiness

**Current estimated completion: 61%.** This is a weighted estimate of work completed toward an employer-showcaseable project, not production readiness. The immediate blockers are the complete GitHub source sync, fresh-clone installation/run, green hosted CI, authentic dashboard screenshots and deployment verification.

See [EMPLOYER_SHOWCASE_READINESS.md](EMPLOYER_SHOWCASE_READINESS.md) for the scoring rubric, evidence, outstanding tasks and acceptance criteria.

## Analytical and responsible-use caveats

All data is synthetic and denominated in EUR. The detector's evaluation metrics measure recovery of injected synthetic scenarios only; they do not estimate real-world fraud performance. A finding is a screening signal, not proof of fraud, policy violation, waste or supplier overcharging. The current peer baseline also has a documented temporal-leakage limitation.

Do not use this prototype for automated employment, credit, disciplinary or payment decisions. It is not production-certified and must not be exposed publicly or loaded with real employee/financial data without further privacy, security, operational and legal review.

See [SECURITY.md](SECURITY.md) and [PHASE7_RELEASE_NOTES.md](PHASE7_RELEASE_NOTES.md).
