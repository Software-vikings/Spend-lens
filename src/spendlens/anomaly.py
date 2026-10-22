"""Explainable peer-group anomaly screening with configurable evaluation settings."""
from __future__ import annotations
from collections import defaultdict
from statistics import median, mean, pstdev

MIN_PEER_COUNT = 8
ROBUST_Z_THRESHOLD = 3.5
MAD_SCALE = 1.4826

def score_transactions(rows: list[dict], min_peer_count: int = MIN_PEER_COUNT,
                       threshold: float = ROBUST_Z_THRESHOLD,
                       method: str = "mad") -> list[dict]:
    """Score each row against same-merchant/category peers, excluding itself.

    method='mad' uses median/MAD. method='zscore' is a non-robust comparator
    using mean/population standard deviation; it is included for ablation only.
    """
    if min_peer_count < 1:
        raise ValueError("min_peer_count must be >= 1")
    if threshold <= 0:
        raise ValueError("threshold must be > 0")
    if method not in {"mad", "zscore"}:
        raise ValueError("method must be 'mad' or 'zscore'")
    groups = defaultdict(list)
    for row in rows:
        groups[(row["merchant_id"], row["category"])].append(row)

    output = []
    for row in rows:
        peers = [peer for peer in groups[(row["merchant_id"], row["category"])]
                 if peer["transaction_id"] != row["transaction_id"]]
        values = [float(peer["amount"]) for peer in peers]
        if len(values) < min_peer_count:
            output.append({**row, "peer_count": len(values), "peer_median": None,
                           "robust_z": None, "is_flagged": 0,
                           "scoring_method": method,
                           "explanation": "Insufficient peer history for reliable screening."})
            continue
        if method == "mad":
            centre = median(values)
            mad = median([abs(x-centre) for x in values])
            scale = MAD_SCALE * mad if mad > 0 else max(abs(centre)*0.05, 1.0)
            score = (float(row["amount"])-centre)/scale
            score_name = "robust z-score"
        else:
            centre = mean(values)
            scale = pstdev(values)
            scale = scale if scale > 0 else max(abs(centre)*0.05, 1.0)
            score = (float(row["amount"])-centre)/scale
            score_name = "z-score"
        flagged = int(score >= threshold)
        output.append({**row, "peer_count": len(values),
                       "peer_median": round(median(values),2),
                       "robust_z": round(score,3), "is_flagged": flagged,
                       "scoring_method": method,
                       "explanation": f"Amount is {float(row['amount']):.2f}, versus peer median {median(values):.2f}; {score_name} {score:.2f}."})
    return output
