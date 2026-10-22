# SpendLens Power BI build guide

This release supplies Power BI-ready CSV exports, a star-schema recommendation, DAX measures and a report specification. A native .pbix file is not generated because Power BI Desktop is a Windows application and is not available in this execution environment.

## Import

Use Get Data → Text/CSV and import:
- ../reports/pbi_transactions.csv
- ../reports/pbi_date.csv
- ../reports/pbi_department_headcount.csv
- ../reports/pbi_anomaly_findings.csv
- ../reports/pbi_recurring_findings.csv
- ../reports/pbi_merchant_drift.csv
- ../reports/pbi_duplicate_candidates.csv
- ../reports/pbi_fragmented_candidates.csv

Set transaction_date and date to Date; amount fields to Decimal Number; IDs to Text. Do not load scenario_label or scenario_type into production-facing report pages. They exist only for internal synthetic evaluation.

## Model

Recommended relationships:
- Date[Date] 1 → * Transactions[transaction_date]
- Department[department] 1 → * Transactions[department]
- Merchant[merchant_id] 1 → * Transactions[merchant_id]

Use single-direction filtering from dimensions to facts. Keep findings as separate fact-like tables; relate by transaction/merchant/date keys only where unambiguous. Avoid many-to-many relationships simply to make a visual work.

## Core DAX measures

```DAX
Total Spend = SUM(Transactions[amount])
Transaction Count = DISTINCTCOUNT(Transactions[transaction_id])
Average Transaction = DIVIDE([Total Spend], [Transaction Count])
Spend per Employee = DIVIDE([Total Spend], SUM(DepartmentHeadcount[headcount]))
Flagged Findings = COUNTROWS(AnomalyFindings)
Recurring Payment Changes = COUNTROWS(RecurringFindings)
Merchant Drift Findings = COUNTROWS(MerchantDriftFindings)
Duplicate Candidate Groups = COUNTROWS(DuplicateCandidates)
Fragmented Purchase Groups = COUNTROWS(FragmentedCandidates)
```

Spend per Employee is valid only when the headcount table is filtered to the same month and department grain as spend. Supplied headcounts are illustrative placeholders; replace them with validated monthly snapshots before drawing business conclusions.

## Suggested report pages

### Executive overview
- KPI cards: Total Spend, Transaction Count, Average Transaction
- Monthly spend trend
- Spend by department
- Top merchants by spend share
- Finding counts by signal type

### Merchant intelligence
- Merchant spend and share
- Monthly median/average transaction amount
- Merchant drift candidates with baseline and recent medians
- Drill-through to transactions

### Recurring payments
- Subscription ID, merchant, owner, payment count
- Historical median vs latest amount
- Percentage change and date history

### Review queue
- Duplicate candidates
- Fragmented-purchase candidates
- Anomaly findings and explanation
- Explicit status field for human review

## Design and governance

- Label findings as candidates for review, not confirmed misconduct.
- Keep synthetic evaluation fields out of user-facing pages.
- Include a data-as-of date and source/provenance note.
- Show sample size alongside medians and percentages.
- Do not rank departments by raw spend without considering headcount, business activity and approved budgets.
- Merchant drift compares transaction amount medians; without quantities/SKUs it cannot establish a true unit-price increase.
