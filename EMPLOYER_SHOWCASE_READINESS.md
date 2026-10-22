# SpendLens — Employer Showcase Readiness Assessment

**Assessment date:** 22 October 2026  
**Current estimate: 67% complete**  
**Scope:** Readiness to demonstrate the project credibly to an employer or technical interviewer. This is not a production-readiness or regulatory certification score.

## What the percentage measures

The score estimates how much work is complete toward making SpendLens independently inspectable, installable, runnable, demonstrable and defensible in an interview. It is weighted by employer-facing requirements, not by phase count or code volume. Credit is awarded only where there is evidence.

## Weighted score

| Workstream | Weight | Credit | Evidence and remaining gap |
|---|---:|---:|---|
| Core product functionality | 20 | 18 | Data pipeline, SQLite, spend screens, authenticated API, review workflow and browser dashboard are present in GitHub. Full clean-clone end-to-end execution remains unverified. |
| Analytical validity | 15 | 9 | Multi-seed synthetic evaluation, threshold sensitivity, ablation and limitations report exist. Historical-only temporal validation and independent benchmark data remain. |
| Reproducible setup | 15 | 9 | README setup, requirements, package metadata, environment example and Docker configuration are in GitHub. Fresh-clone installation/run has not yet been confirmed. |
| Tests and CI | 15 | 9 | Five test modules are in GitHub; 30 tests passed locally in the latest recorded run. GitHub Actions has been triggered, but a green hosted run is not yet confirmed. |
| UX and demo evidence | 10 | 6 | Dashboard HTML/CSS/JS and interaction logic are in GitHub. Genuine screenshots, walkthrough and hosted demo remain. |
| SQL and Power BI | 10 | 7 | SQL schema/analytics and Power BI build guide are in GitHub. Pipeline-generated exports are reproducible; no native PBIX or report screenshots are included. |
| Deployment and operations | 5 | 1 | Dockerfile, Compose and entrypoint are in GitHub. Docker build/runtime and public deployment are unverified. |
| Security | 5 | 3 | API-key authentication, viewer/analyst roles, validation, security headers and security notes exist. No tenant isolation, SSO/MFA, formal penetration test or external security review. |
| Employer-facing documentation | 5 | 5 | README, release notes, security documentation, analytical validation report and this assessment are present. |
| **Total** | **100** | **67** | **67% estimated employer-showcase completion** |

## Repository delivery — updated

The GitHub repository now contains **34 tracked files** at the latest inspected tree, including:
- All eight Python application modules.
- Browser dashboard HTML, CSS and JavaScript.
- Five automated test modules.
- SQL schema and analytical queries.
- GitHub Actions workflow.
- Dockerfile, Compose file, entrypoint and environment example.
- Power BI build guide.
- README, release notes, security documentation and analytical validation report.
- This employer-readiness assessment.

Runtime SQLite database, local caches, credentials and generated transaction/export files are intentionally excluded. The pipeline recreates synthetic data and report exports.

## Verified evidence

- Latest recorded local automated test result: **30 passed**.
- Python source/test compilation passed.
- Dashboard JavaScript syntax check passed.
- Local project ZIP integrity passed in the previous verification.
- GitHub tree inspection confirmed the 34 tracked paths listed above.
- GitHub Actions was triggered by the latest commits; its final conclusion remains pending at the time of this assessment.

Local test results are not proof that the GitHub copy passes. Hosted CI and fresh-clone verification must be confirmed separately.

## Remaining work and acceptance criteria

### P0 — required before presenting as a finished portfolio project

1. Confirm a green GitHub Actions run on the latest main commit. Fix any failures and rerun.
2. Clone the GitHub repository into a clean directory; install dependencies in a new virtual environment; run the synthetic pipeline, validation and tests; start the API; exercise the dashboard and review workflow.
3. Capture genuine screenshots of the overview, findings queue/detail and transaction explorer. Add them to the repository and README.
4. Verify the project works with the documented startup steps from a fresh clone and that all README links resolve.

### P1 — strongly recommended

5. Build and run the Docker image; verify health check and persistent data volume.
6. Add a time-ordered historical-only backtest to remove future-data leakage from peer baselines.
7. Build a Power BI Desktop report and save the PBIX if that environment is available; otherwise continue to label the current deliverable as Power BI-ready exports and guidance.
8. Run dependency vulnerability scanning and basic security checks.
9. Publish a demo only with synthetic data, TLS and appropriate access restrictions.

### P2 — interview polish

10. Add an architecture diagram and 2–3 minute walkthrough.
11. Add one worked finding example from peer baseline through analyst decision and audit history.
12. Prepare interview notes on design trade-offs, false positives, synthetic-data limitations and security boundaries.

## Scoring rules

A configuration file is not equivalent to a verified deployment; a workflow file is not equivalent to a passing hosted CI run; Power BI-ready CSVs are not a completed PBIX. The score is a reasoned project-management estimate, not an externally audited metric. Increase it only when acceptance criteria are evidenced.

## Claims boundary

SpendLens is an independent prototype using synthetic EUR transactions. Findings are human-review signals, not proof of fraud, policy violation, waste or supplier overcharging. Synthetic precision/recall must not be presented as expected real-world performance. The peer baseline currently uses in-sample peers and may include future-dated transactions. The project is not connected to Pleo, a bank or real employer data, and is not production-certified.

**Current decision:** The full source and documentation are now present in GitHub, so the earlier source-sync blocker is resolved. SpendLens is not yet ready to be described as a fully verified employer showcase until hosted CI, fresh-clone execution and demo evidence are completed.
