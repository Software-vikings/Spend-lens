# SpendLens Phase 5 — Analytical Validation Report

**Status: Share with caveats.** The validation code is reproducible and the test suite passes, but this is synthetic-data validation, not evidence of production fraud-detection performance.

## Scope and correction

The peer-group anomaly detector screens unusually high individual transaction amounts. Cohort statistics are now computed once per merchant/category group for efficient scoring; the scored transaction itself is included in its cohort baseline, while peer_count reports the other observations. Earlier aggregate evaluation counted subscription price changes, duplicate purchases, fragmented purchases and merchant drift as if the peer detector were expected to detect them. That target-definition error is corrected: only high_value_outlier records are positive cases; ordinary records are negatives. Other injected scenario types are reported separately.

## Multi-seed results

Four deterministic runs used 5,131 transactions each (seeds 7, 42, 101 and 2026). Averaged across runs: precision 96.72%, recall 100.00%, specificity 99.98%, F1 98.32%, mean false positives 1.00 and mean false negatives 0.00.

These unusually strong values result from conspicuously high outliers against relatively stable synthetic merchant/category distributions. They should not be projected onto real corporate-spend data.

## Threshold sensitivity

| Robust-score threshold | Mean precision | Mean recall | Mean F1 | Mean false positives |
|---:|---:|---:|---:|---:|
| 2.5 | 49.30% | 100.00% | 66.01% | 30.00 |
| 3.0 | 85.01% | 100.00% | 91.66% | 5.50 |
| 3.5 | 96.72% | 100.00% | 98.32% | 1.00 |
| 4.0 | 100.00% | 100.00% | 100.00% | 0.00 |
| 4.5 | 100.00% | 100.00% | 100.00% | 0.00 |
| 5.0 | 100.00% | 99.14% | 99.56% | 0.00 |

The default threshold is 3.5. Threshold 4.0 eliminated observed false positives in these four runs, but selecting a threshold on the same synthetic design is not independent validation.

## Method ablation

MAD was compared with a mean/population-standard-deviation z-score baseline. The comparator performed similarly and sometimes better. Current evidence does not demonstrate MAD superiority; its rationale is robustness to skew and extreme values, which requires testing on representative distributions.

## Scenario-specific findings

The peer detector detected injected high-value outliers in these runs. Duplicate and subscription-price-change cases require separate logic. Merchant drift and fragmented-purchase rows were flagged in this generator, which does not establish general reliability.

## Limitations and next requirements

1. Temporal leakage: each transaction is compared with peers from the complete dataset, so future-dated transactions can influence the baseline.
2. Synthetic-only evidence: no external or independently labelled benchmark has been used.
3. Scenario imbalance: real spend distributions can be heavy-tailed, seasonal, department-specific and contract-driven.
4. One-sided detector: unusually high amounts only.
5. A flag is a review signal, not evidence of fraud, policy violation, waste or supplier overcharging.
6. No threshold is production-calibrated from these experiments.

Run `PYTHONPATH=src python -m spendlens.validation` and `PYTHONPATH=src pytest -q` to reproduce.
