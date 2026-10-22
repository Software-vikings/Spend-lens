# SpendLens — Employer Showcase Readiness Assessment

**Assessment date:** 22 October 2026  
**Withdrawn: prior 73% score was not a product-completion measure.**

**Current product completion baseline: 24/100** (weighted against the intended automated expense-decision system; see [PRODUCT_SCOPE_AND_REBUILD_PLAN.md](PRODUCT_SCOPE_AND_REBUILD_PLAN.md)).  
**Scope:** Readiness to demonstrate the project credibly to an employer or technical interviewer. This is not a production-readiness or regulatory certification score.

## What the former percentage measured

The old score measured repository/demo completeness, not whether SpendLens met the intended requirement to decide expense approvals automatically. It must not be quoted as product completion. The old weighted scorecard below is retained only as a historical record and is superseded by the 24/100 product rubric in the rebuild plan.

## What the former percentage measured

The score estimates how much work is complete toward making SpendLens independently inspectable, installable, runnable, demonstrable and defensible in an interview. It is weighted by employer-facing requirements, not by phase count or code volume. Credit is awarded only where there is evidence.

## Weighted score

| Workstream | Weight | Credit | Evidence and remaining gap |
|---|---:|---:|---|
| Core product functionality | 20 | 18 | Data pipeline, SQLite, spend screens, authenticated API, review workflow and browser dashboard are present in GitHub. Manual browser walkthrough from a fresh clone remains. |
| Analytical validity | 15 | 9 | Multi-seed synthetic evaluation, threshold sensitivity, ablation and limitations report exist. Historical-only temporal validation and independent benchmark data remain. |
| Reproducible setup | 15 | 11 | README setup, dependencies and package metadata are present. Hosted clean checkout installed dependencies and ran pipeline, validation and tests. Manual API/browser startup from a fresh clone remains. |
| Tests and CI | 15 | 13 | Five test modules are in GitHub; 30 tests passed locally. Hosted GitHub Actions run for source commit 2900258 passed checkout, dependency install, pytest, pipeline, validation and compilation. |
| UX and demo evidence | 10 | 6 | Dashboard now includes month/department/category cross-filtering, KPI-to-ledger navigation, clickable chart selections and transaction detail drill-through; API tests verify matching filtered aggregates. Genuine browser walkthrough, screenshots and hosted demo remain. |
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
- GitHub Actions source commit **2900258** completed successfully, including the dashboard CSP correction and optimised cohort scoring. The later dashboard cross-filtering PR (#2) also passed hosted checks: dependency installation, pytest, synthetic pipeline, multi-seed validation and Python compilation. The PR was merged to `main` as commit `8305a4e`.
- GitHub tree inspection confirmed the 34 tracked paths listed above.
- The latest source commit includes the complete app modules, dashboard, tests, CI, SQL, Docker configuration, Power BI guide and updated documentation.

The successful hosted workflow verifies a clean GitHub checkout can install and execute the automated checks. The detector now computes cohort statistics once per group, reducing the local full validation run to about 1.7 seconds; the cohort includes the focal row, so this remains an in-sample screen rather than a historical-only backtest. The CSP now permits same-origin dashboard assets while retaining restrictive defaults. Hosted CI does not replace a manual browser walkthrough or Docker runtime test.

## Remaining work and acceptance criteria

### P0 — required before presenting as a finished portfolio project

1. Clone the GitHub repository into a separate clean directory; start the API using the documented steps; open the dashboard; verify sign-in, summary charts, findings detail, review updates and transaction search. Also click month, department and category values and confirm the spend metrics, other transaction charts and ledger update together; click the transaction KPI and a transaction row to verify drill-through.
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

**Current decision (22 October 2026):** The repository has a working synthetic-data foundation and API/dashboard scaffolding, but it does not implement the core automated expense-policy decision product. No claim/evidence domain model, versioned policy engine or deterministic approve/reject/review decision lifecycle exists. The prior 73% figure is withdrawn. Product completion starts at **24/100** under the new rubric. See [PRODUCT_SCOPE_AND_REBUILD_PLAN.md](PRODUCT_SCOPE_AND_REBUILD_PLAN.md).

## Execution tracker — 22 October 2026

This tracker records the remaining work as open until the stated acceptance evidence is available. Automated CI success is not a substitute for these manual/runtime checks.

| ID | Priority | Task | Acceptance evidence | Status |
|---|---|---|---|---|
| SHOW-01 | P0 | Fresh-clone application walkthrough | Clean clone starts successfully; sign-in, month/department/category cross-filtering, KPI-to-ledger navigation, transaction-row detail, findings detail, analyst review update and transaction search work in a browser | Open |
| SHOW-02 | P0 | Capture dashboard evidence | Genuine screenshots for overview, findings queue/detail and transaction explorer committed and linked from README | Open |
| SHOW-03 | P0 | Verify setup documentation | README commands and links verified from a separate clean clone | Open |
| SHOW-04 | P1 | Docker runtime verification | Image builds; container starts; health check passes; persisted data survives container recreation | Open |
| SHOW-05 | P1 | Historical-only validation | Time-ordered evaluation uses only information available at each scoring timestamp; leakage limitations documented | Open |
| SHOW-06 | P1 | Power BI report | Native PBIX created and opened successfully, or environment limitation documented and CSV/guide scope retained | Open |
| SHOW-07 | P1 | Dependency/security checks | Dependency vulnerability scan and documented API/security review completed; findings triaged | Open |
| SHOW-08 | P1 | Demo deployment decision | Either verified synthetic-only deployment with TLS/access controls, or an explicit decision to keep the project local | Open |
| SHOW-09 | P2 | Architecture and investigation walkthrough | Architecture diagram and one end-to-end finding case added to the repository | Open |
| SHOW-10 | P2 | Interview preparation | Trade-offs, false positives, synthetic data and security boundaries documented for discussion | Open |

### Execution notes

- The repository's latest recorded hosted CI run is green; the CI workflow covers dependency installation, automated tests, the synthetic pipeline, multi-seed validation and Python compilation.
- The dashboard cross-filter/drill-through feature is implemented and its API tests pass, but manual browser behavior is still unverified. Docker runtime, historical-only backtesting and native PBIX creation have not been verified. Do not mark these complete based solely on configuration files or automated unit tests.
- Update each row only after its acceptance evidence is committed or linked.


## Product-scope reassessment — 22 October 2026

The previous 73% estimate is withdrawn for product completion. It reflected repository completeness, CI and documentation, not the actual product requirement. Current evidence-based product baseline is **24/100**. The missing critical path is: first-class claim/evidence model, configurable versioned policy, deterministic rule engine, persisted decisions/audit lifecycle, API integration and a coherent state-driven dashboard.

The existing anomaly detector and insight heuristics are supplementary risk signals. They do not decide whether an expense is eligible or reimbursable. The current findings/review workflow is not an automated approval workflow. The current frontend is a monolithic imperative script and has no claim/decision/policy workflow.

The product acceptance criteria and rebuild sequence are now defined in [PRODUCT_SCOPE_AND_REBUILD_PLAN.md](PRODUCT_SCOPE_AND_REBUILD_PLAN.md). Do not describe the system as automatically approving or rejecting expenses until the Phase 2 engine and Phase 3 workflow exit gates pass.

## Rebuild execution status — 22 October 2026

- Phase 0 documentation reset is complete on branch rebuild/decision-engine-and-dashboard.
- A first decision-engine vertical slice has been added in draft PR #3: deterministic four-outcome policy evaluation, synthetic versioned policy, SQLite decision persistence, authenticated evaluation/list/detail endpoints and tests.
- This implementation is not yet accepted as complete: hosted CI status is not verified, the claim/evidence domain model remains incomplete, and the frontend remains the old monolithic dashboard.
- No new completion percentage is awarded yet. Retain 24/100 as the pre-implementation baseline until CI and rubric evidence are available.
- Private prompt/decision/change history is not stored in this public repository. The .spendlens-private/ directory is ignored by Git. The private worklog is maintained separately.
- Draft PR: https://github.com/Software-vikings/Spend-lens/pull/3


- Initial decision workbench added in the rebuild branch: synthetic expense form, API evaluation, persisted decision queue and rule-by-rule explanation. This is not a full dashboard rebuild; the old monolithic UI state architecture and manual browser verification remain open.


## CI verification update — 22 October 2026

- GitHub Actions SpendLens CI run #65 (ID 39757279432) passed on the current PR head.
- Pytest result: 44 passed, 1 deprecation warning, 1.51 seconds.
- Synthetic pipeline, multi-seed validation, Python compilation and dashboard JavaScript syntax checks also passed.
- The first deterministic decision-engine/API/workbench slice is now verified by hosted CI. This does not establish browser correctness or production suitability.
- Product completion is re-scored at **49/100**, using the rubric in PRODUCT_SCOPE_AND_REBUILD_PLAN.md. The earlier 24/100 remains the pre-implementation baseline; 73% remains withdrawn.
- Still open: first-class claim/evidence model, policy administration, full decision audit/override/re-evaluation lifecycle, complete state-driven dashboard and chart drill-through, browser tests, clean-clone walkthrough, Docker and security/dependency verification.
- Draft PR #3 remains open and unmerged: https://github.com/Software-vikings/Spend-lens/pull/3


- Latest PR-head CI verification: SpendLens CI run #71 (ID 39769318304) passed on 22 October 2026. Pytest: 44 passed, one Starlette/httpx deprecation warning; synthetic pipeline, multi-seed validation, Python compilation and JavaScript syntax checks passed. https://github.com/Software-vikings/Spend-lens/actions/runs/39769318304


## Micro-detail dashboard and claim-intake changes — verification pending

- Added faceted chart queries so month, department and category charts retain alternative choices while compatible filters remain active.
- Fixed structured decision explanation rendering; the previous UI displayed `[object Object]`.
- Replaced hard-coded demo form values with explicit employee, merchant, department, date, amount, currency, category, purpose and receipt metadata fields.
- Clearly disclosed that receipt images/OCR are not implemented and duplicate-risk is simulated input.
- Improved transaction drill-through, keyboard opening, amount precision/currency formatting and selected chart states.
- Engine now treats zero amounts, future dates, malformed currency codes and missing employee/merchant/department details as insufficient data.
- Latest changes are not yet CI-verified or browser-verified. Product score remains 49/100 until evidence is available.
