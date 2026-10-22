# SpendLens — Employer Showcase Readiness Assessment

**Assessment date:** 22 October 2026  
**Current estimate: 73% complete**  
**Scope:** Readiness to demonstrate the project credibly to an employer or technical interviewer. This is not a production-readiness or regulatory certification score.

## What the percentage measures

The score estimates how much work is complete toward making SpendLens independently inspectable, installable, runnable, demonstrable and defensible in an interview. It is weighted by employer-facing requirements, not by phase count or code volume. Credit is awarded only where there is evidence.

## Weighted score

| Workstream | Weight | Credit | Evidence and remaining gap |
|---|---:|---:|---|
| Core product functionality | 20 | 18 | Data pipeline, SQLite, spend screens, authenticated API, review workflow and browser dashboard are present in GitHub. Manual browser walkthrough from a fresh clone remains. |
| Analytical validity | 15 | 9 | Multi-seed synthetic evaluation, threshold sensitivity, ablation and limitations report exist. Historical-only temporal validation and independent benchmark data remain. |
| Reproducible setup | 15 | 11 | README setup, dependencies and package metadata are present. Hosted clean checkout installed dependencies and ran pipeline, validation and tests. Manual API/browser startup from a fresh clone remains. |
| Tests and CI | 15 | 13 | Five test modules are in GitHub; 30 tests passed locally. Hosted GitHub Actions run for latest main commit 95e3bb8 passed checkout, dependency install, pytest, pipeline, validation and compilation. |
| UX and demo evidence | 10 | 6 | Dashboard HTML/CSS/JS and interactions are in GitHub; API tests verify dashboard and asset routes. Genuine screenshots, walkthrough and hosted demo remain. |
| SQL and Power BI | 10 | 7 | SQL schema/analytics and Power BI build guide are in GitHub. Pipeline-generated exports are reproducible; no native PBIX or report screenshots are included. |
| Deployment and operations | 5 | 1 | Dockerfile, Compose and entrypoint are in GitHub. Docker build/runtime and public deployment are unverified. |
| Security | 5 | 3 | API-key authentication, viewer/analyst roles, validation, security headers and security notes exist. No tenant isolation, SSO/MFA, formal penetration test or external security review. |
| Employer-facing documentation | 5 | 5 | README, release notes, security documentation, analytical validation report and this assessment are present. |
| **Total** | **100** | **73** | **73% estimated employer-showcase completion** |

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
- GitHub Actions source commit **218ebf8** completed successfully. Steps verified: checkout, Python setup, dependency installation, pytest, synthetic pipeline, multi-seed validation and Python compilation.
- GitHub tree inspection confirmed the 34 tracked paths listed above.
- The latest main commit includes the complete app modules, dashboard, tests, CI, SQL, Docker configuration, Power BI guide and updated documentation.

The successful hosted workflow verifies a clean GitHub checkout can install and execute the automated checks. It does not replace a manual browser walkthrough or Docker runtime test.

## Remaining work and acceptance criteria

### P0 — required before presenting as a finished portfolio project

1. Clone the GitHub repository into a separate clean directory; start the API using the documented steps; open the dashboard; verify sign-in, summary charts, findings detail, review updates and transaction search.
2. Capture genuine screenshots of the overview, findings queue/detail and transaction explorer. Add them to the repository and README.
3. Verify all README links and startup instructions from a clean clone.

### P1 — strongly recommended

4. Build and run the Docker image; verify health check and persistent data volume.
5. Add a time-ordered historical-only backtest to remove future-data leakage from peer baselines.
6. Build a Power BI Desktop report and save the PBIX if that environment is available; otherwise continue to label the current deliverable as Power BI-ready exports and guidance.
7. Run dependency vulnerability scanning and basic security checks.
8. Publish a demo only with synthetic data, TLS and appropriate access restrictions.

### P2 — interview polish

9. Add an architecture diagram and 2–3 minute walkthrough.
10. Add one worked finding example from peer baseline through analyst decision and audit history.
11. Prepare interview notes on design trade-offs, false positives, synthetic-data limitations and security boundaries.

## Scoring rules

A configuration file is not equivalent to a verified deployment; a workflow file is not equivalent to a passing hosted CI run; Power BI-ready CSVs are not a completed PBIX. The score is a reasoned project-management estimate, not an externally audited metric. Increase it only when acceptance criteria are evidenced.

## Claims boundary

SpendLens is an independent prototype using synthetic EUR transactions. Findings are human-review signals, not proof of fraud, policy violation, waste or supplier overcharging. Synthetic precision/recall must not be presented as expected real-world performance. The peer baseline currently uses in-sample peers and may include future-dated transactions. The project is not connected to Pleo, a bank or real employer data, and is not production-certified.

**Current decision:** The full source and documentation are now present in GitHub, and hosted CI has passed for the source commit. SpendLens is close to being a credible employer demo, but manual fresh-clone/browser evidence, screenshots and Docker verification remain.
