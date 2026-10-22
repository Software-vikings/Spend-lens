# SpendLens — Employer Showcase Readiness Assessment

**Assessment date:** 22 October 2026  
**Scope:** Readiness to demonstrate the project credibly to an employer or technical interviewer. This is not a production-readiness or regulatory certification score.

## Current score: 61% complete

The percentage estimates how much of the work required to make SpendLens independently inspectable, installable, runnable, demonstrable and defensible in an interview has been completed. It is not based on phase count or code volume.

| Workstream | Weight | Credit | Evidence and remaining gap |
|---|---:|---:|---|
| Core product functionality | 20 | 18 | Data pipeline, SQLite, explainable spend screens, API, review workflow and dashboard exist locally. Fresh-clone end-to-end verification remains. |
| Analytical validity | 15 | 9 | Multi-seed synthetic evaluation, threshold sweep, ablation and caveats exist. Historical-only temporal validation and independent benchmark data remain. |
| Reproducible setup | 15 | 5 | Setup instructions and packaging metadata exist. Clean-environment installation and fresh-clone run remain unverified. |
| Tests and CI | 15 | 8 | 30 tests passed locally; compilation and JS syntax checks passed. Hosted GitHub Actions is not verified; integration/edge-case coverage can improve. |
| UX and demo evidence | 10 | 6 | Responsive dashboard and analyst workflows exist locally. Genuine screenshots, walkthrough and hosted demo are absent. |
| SQL and Power BI | 10 | 7 | SQL, Power BI-ready CSVs, model guidance and DAX examples exist. No native PBIX or final report screenshots. |
| Deployment and operations | 5 | 1 | Dockerfile and Compose exist. Docker build/runtime and public deployment are unverified. |
| Security | 5 | 3 | API keys, role checks, validation, security headers and caveats exist. No tenant isolation, SSO/MFA, formal penetration test or external security review. |
| Employer-facing documentation | 5 | 4 | README, release notes, security and analytical guides exist; consistency and evidence capture remain. |
| **Total** | **100** | **61** | **61% estimated employer-showcase completion** |

## Verified locally

- Automated test suite: **30 passed** in the latest recorded run.
- Python source/test compilation passed.
- frontend/app.js passed Node.js syntax validation.
- The Phase 7 ZIP archive passed an integrity check in the prior verification.
- Local project contains application modules, dashboard assets, tests, SQL, Power BI guide, reports and container configuration.

These results are local-only; they do not prove the GitHub copy works.

## Not yet verified or delivered

- Last inspected GitHub tree contained only the initial documentation/configuration subset; application modules, frontend, tests and most supporting files were absent.
- No fresh clone has been installed and run end-to-end.
- No green GitHub Actions run has been confirmed on the target repository.
- Docker build/runtime has not been tested; Docker was unavailable in the last execution environment.
- No public demo deployment is verified.
- No native Power BI PBIX is included.
- No formal security assessment or real-world model validation has been performed.

## Remaining work and acceptance criteria

### P0 — required before sharing as a finished portfolio repository

1. Sync all application modules, frontend, tests, SQL, reports, Power BI guide, CI workflow, Docker files, environment example and documentation. Exclude credentials, local caches, virtual environments and runtime databases.
2. Inspect the main branch tree and confirm all required paths and README links.
3. Clone into a clean directory; create a new virtual environment; install dependencies; run the pipeline and all tests; start the API; exercise the dashboard. Record exact results.
4. Confirm a green GitHub Actions run on main after source sync.
5. Capture genuine screenshots of the overview, findings detail/review and transaction explorer using synthetic data.

### P1 — strongly recommended

6. Build and run the Docker image; verify startup, health check and persistent data volume.
7. Publish a demo only with synthetic data, TLS and appropriate access restrictions.
8. Build a Power BI Desktop report and save the PBIX if that environment is available; otherwise label the current material accurately as Power BI-ready exports and guidance.
9. Add a time-ordered historical-only backtest to address future-data leakage.
10. Run dependency vulnerability scanning and basic security checks.

### P2 — interview polish

11. Add an architecture diagram and 2–3 minute walkthrough.
12. Add one worked finding example from peer baseline through reviewer decision and audit history.
13. Prepare interview notes on design trade-offs, false positives, synthetic-data limitations and security boundaries.

## Scoring rules

Credit is awarded only where work exists and evidence supports it. A configuration file is not equivalent to a verified deployment; a workflow file is not equivalent to a passing hosted CI run; Power BI-ready CSVs are not a completed PBIX. The percentage is a reasoned project-management estimate, not an externally audited metric. Update it only when acceptance criteria are evidenced.

## Claims boundary

SpendLens is an independent prototype using synthetic EUR transactions. Findings are human-review signals, not proof of fraud, policy violation, waste or supplier overcharging. Synthetic precision/recall must not be presented as expected real-world performance. The project is not connected to Pleo, a bank or real employer data, and is not production-certified.

**Current decision:** Not yet ready to present as a completed employer-facing repository. The immediate blocker is the complete GitHub source sync, followed by clean-clone and hosted-CI verification.
