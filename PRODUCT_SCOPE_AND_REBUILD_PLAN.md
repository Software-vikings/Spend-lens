# SpendLens — Product Scope and Rebuild Plan

**Plan date:** 22 October 2026  
**Baseline:** 24/100 product completion (see scoring rubric below).

## Product objective

SpendLens is intended to be an expense decision system—not merely a transaction anomaly viewer. For each submitted expense, it should evaluate transaction data and supporting evidence against an explicit, configurable, versioned company expense policy; produce a decision with rule-level explanations; persist the result and audit history; and expose the same records consistently across an interactive dashboard.

The system must never invent a company's policy. Where policy or evidence is missing or ambiguous, return an exception/insufficient-evidence outcome rather than guessing.

## Codebase audit: what exists versus what the product needs

- `generate.py` creates synthetic transactions with injected labels. It does not model expense claims, receipt/invoice evidence, business purpose, policy versions, budgets or approval requirements.
- `anomaly.py` scores amounts against merchant/category cohorts. This is anomaly detection, not policy evaluation. The cohort is in-sample and can include later-dated records.
- `insights.py` creates recurring-payment, merchant-drift, duplicate and fragmented-purchase signals. These heuristics do not establish reimbursability or policy compliance.
- `phase4.py` persists generic findings and analyst review events. Findings are not consistently linked to a first-class claim and final decision.
- `api.py` exposes summaries, transactions, findings and review updates. There is no policy evaluation or expense-decision endpoint.
- `frontend/app.js` is one imperative script that fetches data, owns UI state, creates HTML strings and attaches event listeners during rendering. State is spread across DOM values and JS state; filter updates trigger broad reloads; the app has no single route/state model. This makes cross-view consistency and drill-through fragile.
- `frontend/index.html` exposes only overview, findings and transactions. It has no expense submission, decision workbench, policy view or audit workflow.
- Current tests cover APIs and synthetic signals, not policy correctness, end-to-end expense decisions or browser-level cross-filter/drill-through.

The former 73% estimate measured repository/showcase completeness, not achievement of the intended product. It is withdrawn as the product-completion score.

## Target decision contract

Each evaluation returns exactly one outcome:
1. **APPROVE** — required evidence is present and all configured hard policy checks pass.
2. **REJECT** — an explicit deterministic hard-stop rule is conclusively violated; cite the exact rule and evidence.
3. **REVIEW** — an exception, ambiguous context or risk signal requires an authorised decision.
4. **INSUFFICIENT_DATA** — required input is missing, unreadable or not reliable enough to evaluate.

An anomaly score alone must never reject an expense. A statistical outlier is a risk signal, not proof of policy violation.

Persist claim/source transaction IDs, decision and timestamp, engine version, policy ID/version, every rule result and evidence value, exception reasons, re-evaluation history and authorised overrides. Identical inputs + policy version + engine version must yield deterministic results.

## Configurable policy and evidence

Initial rule families: eligible/ineligible categories; transaction and period caps; receipt/invoice requirements; required business purpose/date; duplicate claims; merchant/category restrictions; budget availability when explicitly configured; approval thresholds and exception routing; currency conversion policy if multi-currency is added.

No numeric threshold is universal. Synthetic demo limits must be labelled as example policy, not real employer policy. Initial scope is synthetic claims and receipt metadata. OCR, bank/card/accounting integrations, SSO, multi-tenant SaaS and payment execution are outside this rebuild.

## Dashboard acceptance criteria

- One shared filter state for date/month, department, category, decision and status.
- A chart selection updates every compatible KPI, chart, table and count.
- Selecting a claim opens its detail and exact rule-level decision explanation.
- Selecting a decision outcome opens a filtered decision queue.
- Navigation between overview, claims ledger, decision queue, claim detail, policy and audit views preserves applicable filters/selection.
- Filter controls always reflect the shared state; clear/reset is predictable.
- Charts are keyboard accessible and expose selected state.
- Loading, empty and error states are explicit; no stale or contradictory data.
- Aggregate and ledger API filters have identical semantics; tests reconcile counts and totals.

## Architecture direction

Retain Python/FastAPI and SQLite for the local synthetic prototype, but separate:
- Domain models: claims, transactions, evidence, policy versions, rule results, decisions, audit events.
- Pure deterministic policy engine with rule-level explanations.
- Application services for submission, evaluation, re-evaluation, authorised override and audit persistence.
- API/repository layer with validated endpoints and shared query/filter semantics.
- Modular, state-driven frontend with one source of truth for filters, selection and route/view. Avoid duplicate listeners during re-render.
- Analytics derived from the same persisted domain records as detail views.

Existing anomaly/insight modules can remain supplementary signals. They are not the decision engine.

## Implementation phases and exit gates

### Phase 0 — Baseline and documentation (before code)
Audit code, withdraw misleading score, publish product scope and rebuild plan, add private-log ignore rule, record starting commit.  
**Exit:** target decisions, dashboard behaviour, scoring rubric and gaps documented before implementation.

### Phase 1 — Claim/evidence domain and synthetic policy
Define claim, transaction, receipt metadata, policy version, rule result, decision and audit schemas. Generate complete, missing, invalid, duplicate and exception evidence fixtures. Create clearly labelled synthetic example policy.  
**Exit:** fixtures cover compliant, hard-stop, exception and insufficient-data cases.

### Phase 2 — Deterministic decision engine
Implement pure rule evaluation and APPROVE/REJECT/REVIEW/INSUFFICIENT_DATA results with reasons. Keep anomaly scores non-determinative. Persist versions and audit events; implement re-evaluation and controlled overrides.  
**Exit:** tests cover every outcome, determinism, policy versioning and audit.

### Phase 3 — API/workflow
Add claim submission/list/detail, evaluate/re-evaluate, policy, decision and audit endpoints; common filters and pagination.  
**Exit:** integration tests prove the lifecycle and consistent filtered totals.

### Phase 4 — Dashboard rebuild
Replace the monolithic script with modular state-driven UI. Build overview, claims ledger, decision queue, claim detail, policy and audit views. Add cross-filtering, drill-through, URL/view state and accessible chart controls.  
**Exit:** browser tests cover chart -> filtered KPIs/charts/table -> claim detail -> rule explanation -> audit history.

### Phase 5 — Validation and release
Use hand-authored expected outcomes, edge/adversarial tests and synthetic scenario coverage. Verify clean clone, API and browser walkthrough, security/dependencies. README claims only verified features.  
**Exit:** automated checks green, clean-clone and browser evidence captured, limitations stated.

## Honest product-completion rubric

| Workstream | Weight |
|---|---:|
| Expense and evidence domain model | 10 |
| Configurable policy model/versioning | 15 |
| Deterministic decision engine/explanations | 25 |
| Persistence, audit and exception/override lifecycle | 10 |
| API/workflow integration | 10 |
| Connected dashboard/drill-through | 15 |
| Tests, validation and reproducibility | 10 |
| Product documentation/safe demo packaging | 5 |
| **Total** | **100** |

Credit requires implemented code and relevant passing tests. Plans/stubs earn no implementation credit. Synthetic results do not establish real-world efficacy. Browser/deployment work needs its own evidence.

**Baseline: 24/100.** The claim/evidence model (10) and policy model/versioning (15) are absent; the deterministic decision engine (25) is absent. Existing persistence/review, API, dashboard, tests and packaging earn only partial credit as reusable foundations. This is a product-scope estimate, not production readiness. Re-score only against evidence after each phase.

## Definition of done

A synthetic expense can be submitted, automatically evaluated against a versioned policy, receive a defensible outcome and rule-level explanation, persist its decision/audit history, and appear consistently in the dashboard. A reviewer can click from an aggregate to the exact claim and see why the system decided as it did. SpendLens remains a synthetic prototype, not a production financial control system or proof of real-world fraud detection.


## Execution status — 22 October 2026

| Phase | Status | Evidence / remaining gate |
|---|---|---|
| Phase 0 — Baseline and documentation | Complete on rebuild branch | Product audit, target outcomes, acceptance criteria, architecture, scoring rubric, README correction and private-log ignore rule committed. |
| Phase 1 — Claim/evidence domain and synthetic policy | Partial | Versioned synthetic example policy and expense input payload exist. Persisted claim/evidence entities, evidence lifecycle and broader fixture set remain. |
| Phase 2 — Decision engine | Initial engine/API slice CI-verified; phase exit gate still open | Deterministic four-outcome evaluator, rule explanations, SQLite decision persistence and authenticated evaluate/list/detail routes. GitHub Actions run #65 passed all 44 tests, synthetic pipeline, multi-seed validation, Python compilation and JS syntax. Full policy coverage, audit lifecycle, re-evaluation and override tests remain. |
| Phase 3 — API/workflow | Partial | Evaluate/list/detail endpoints exist. Submission lifecycle, policy management, overrides, re-evaluation and complete audit lifecycle remain. |
| Phase 4 — Dashboard rebuild | Initial decision workbench added; full rebuild remains | Added a decision page, expense evaluation form, persisted decision queue and rule-level result display. Existing monolithic UI/state model remains; shared-state architecture and browser-level cross-filter/drill-through are still required. |
| Phase 5 — Validation/release | Automated CI slice passed; release validation not started | GitHub Actions run #65 is green. Clean-clone/browser walkthrough, browser interaction tests, security/dependency checks and deployment verification remain. |

**Current evidence-based product score: 49/100 (22 October 2026).** The 24/100 figure below is retained as the pre-implementation baseline. The score is provisional and reflects passing CI for the initial evaluator/API/workbench slice; it does not imply full phase completion, browser verification or production readiness. The updated workstream breakdown is recorded below.

**Current draft implementation:** [PR #3 — Rebuild SpendLens around policy-based expense decisions](https://github.com/Software-vikings/Spend-lens/pull/3). The branch is not merged into the default branch. The frontend/dashboard rebuild is not included in this first vertical slice.


## Re-scored progress after CI verification — 22 October 2026

| Workstream | Weight | Awarded | Evidence / remaining gap |
|---|---:|---:|---|
| Expense and evidence domain model | 10 | 1 | Expense payload contract exists; no first-class persisted claim/evidence entities or lifecycle. |
| Configurable policy model/versioning | 15 | 7 | Versioned JSON policy and basic validation; no policy administration, approval workflow or full rule-family coverage. |
| Deterministic decision engine/explanations | 25 | 17 | Four outcomes, deterministic evaluation, rule evidence and tests pass; coverage remains limited to the implemented rule set. |
| Persistence, audit and exception/override lifecycle | 10 | 3 | Evaluation snapshots persist and can be listed/read; no event-sourced audit trail, authorised override or re-evaluation lifecycle. |
| API/workflow integration | 10 | 5 | Authenticated evaluate/list/detail endpoints pass; no full claim submission workflow or common decision/claim filter semantics. |
| Connected dashboard/drill-through | 15 | 4 | Decision workbench and decision queue added; frontend remains monolithic and cross-view selection/filter propagation is incomplete. |
| Tests, validation and reproducibility | 10 | 7 | CI run #65: 44 tests passed; pipeline, validation, compile and JS syntax passed. Browser, Docker and security checks remain. |
| Product documentation/safe demo packaging | 5 | 5 | Product reset, limitations, synthetic-policy warning and private-log ignore rule documented. |
| **Total** | **100** | **49** | **Provisional implementation score, not production readiness.** |

### Verified CI evidence

- Workflow: SpendLens CI, run #71 (latest PR head) and run #65 (implementation head)
- Latest run ID: 39769318304 — success
- Latest pytest: 44 passed, 1 deprecation warning, 1.53 seconds
- Additional successful steps: synthetic pipeline, multi-seed validation, Python compileall and dashboard JavaScript syntax check.
- Latest run URL: https://github.com/Software-vikings/Spend-lens/actions/runs/39769318304
- Earlier implementation run #65 also passed all steps.

The phase 2 engine/API slice is now CI-verified, but Phase 2 is not fully complete because override, re-evaluation and audit lifecycle acceptance tests are not present. The dashboard is not browser-verified. The PR remains a draft and has not been merged.
