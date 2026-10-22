# SpendLens

SpendLens is a portfolio project for analysing synthetic company expense transactions and surfacing unusual patterns for human review.

> **Demo data only:** all transaction data is synthetic and denominated in EUR. Findings are screening signals, not fraud verdicts, policy determinations, or proof of savings.

## Planned capabilities in the complete local release

- Robust peer-group outlier screening using median absolute deviation (MAD).
- Recurring-payment change and merchant price-drift screens.
- Duplicate transaction candidates and fragmented-purchase patterns.
- Department spend-per-employee analysis.
- SQLite analytics and Power BI-ready exports / guidance.
- FastAPI endpoints for summary, transactions, findings and human review.
- API-key authentication, viewer/analyst roles, request throttling and security headers.
- Browser-based analyst dashboard.
- Multi-seed validation, threshold sensitivity and method ablation.

## Repository status

This GitHub repository has been initialized with the project overview, dependency list, security notes, release notes and Python package metadata. **The complete application source, frontend assets, SQL files, tests and data exports from the Phase 7 release bundle have not yet been synced to this repository.** The complete local source archive remains available in the ChatGPT conversation.

## Security and evaluation caveats

All evaluation metrics are based on injected synthetic scenarios and do not estimate production fraud-detection performance. The current local prototype also has temporal leakage risk in peer baselines.

The project is not production-ready: static API keys, in-memory rate limiting, no tenant isolation, no formal penetration test, and no verified cloud deployment remain material limitations. Do not expose publicly or load real financial data without further security, privacy, operational and legal review.

See [SECURITY.md](SECURITY.md) and [PHASE7_RELEASE_NOTES.md](PHASE7_RELEASE_NOTES.md).
