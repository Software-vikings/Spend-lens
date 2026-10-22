# SpendLens — Release Readiness

**Review date:** 22 October 2026  
**Branch:** `rebuild/decision-engine-and-dashboard`  
**Pull request:** [#3](https://github.com/Software-vikings/Spend-lens/pull/3)  
**Disposition:** Portfolio/demo candidate after local walkthrough; not production-ready. Latest CI rerun is pending after a concurrency fix.

## Verified in CI

The earlier implementation commit `a0b550c192c5203f8e36898817bb176bc533a4d2` passed CI runs #257 and #258 (68 tests). A later run (#262) exposed a second concurrency race in policy-registry initialisation: concurrent expense requests could both seed the same `(policy_id, version)`, causing `sqlite3.IntegrityError: UNIQUE constraint failed`. Commit `654d2c382ab53d58fa68642ad51622ecb51ce088` fixes this by serialising schema creation and seed checks in a `BEGIN IMMEDIATE` transaction. CI runs #263 and #264 for that fix are queued; do not mark final CI green until they complete.

The workflow runs:

- Pytest suite, including the concurrent idempotent expense-submission regression test.
- Synthetic data pipeline.
- Multi-seed validation.
- Python source compilation.
- Dashboard JavaScript syntax validation.

The CI test run reported 68 passing tests. CI does not verify visual rendering or real browser interactions.

## Implemented workflow

1. Analyst submits an expense claim with claim context and receipt metadata.
2. The deterministic evaluator applies the active versioned synthetic policy.
3. The system persists the decision, policy/engine references, rule explanations and submission history.
4. Exceptions appear in the exception queue.
5. An analyst can assign/reassign an exception with priority and SLA.
6. A reviewer can request information, approve or reject an eligible exception.
7. Assignment, resolution and supported policy/finding actions write audit events transactionally with the corresponding mutation.
8. Decision, claim, assignment, resolution and audit histories can be inspected through the API and dashboard workspaces.

## Known limitations

- Synthetic ledger and example policy; no real employer policy configuration or policy validation.
- Receipt data is metadata only. No receipt-file storage, OCR, authenticity verification or external evidence validation.
- Reviewer and assignee names are self-reported; they are not authenticated human identities.
- Audit events are transactionally recorded for supported operations, but are not cryptographically tamper-evident.
- No bank/card/ERP/accounting integration, payment execution or tenant isolation.
- Static API keys; no SSO/MFA, managed secret rotation, distributed rate limiting or formal penetration test.
- No browser end-to-end or visual regression tests have been run.
- Docker build/runtime, cloud deployment, backup/restore and operational monitoring have not been verified.
- This is not production-certified and must not be used for live financial decisions.

## Before presenting a demo

- [ ] Clone the branch into a clean local directory and follow README setup exactly.
- [ ] Run the pipeline, validation and full pytest suite.
- [ ] Start the API locally with synthetic data and test viewer, analyst and admin journeys.
- [ ] Walk through a compliant claim, a hard-stop claim, a missing-receipt exception and a duplicate-candidate review.
- [ ] Demonstrate assignment, request-information and final human resolution, including the audit history.
- [ ] Exercise dashboard cross-filters, clear filters, pagination, transaction drill-through and empty states in a real browser.
- [ ] Confirm the API key is a disposable demo key and no real employee/financial data is loaded.

## Release recommendation

**Suitable for:** a clearly labelled local portfolio demonstration of a policy-based expense decision prototype and exception-operations workflow, after the demo checklist is completed.

**Not suitable for:** production deployment, autonomous real-world reimbursement, compliance certification, fraud adjudication or claims about measured savings/real-world detection accuracy.

Keep PR #3 in draft until browser walkthrough and clean-clone checks are completed. Do not merge or deploy as a production system based on CI alone.
