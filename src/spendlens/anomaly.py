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
    """Score rows against merchant/category cohort distributions.

    Group statistics are computed once per cohort, rather than re-sorting the
    same peer amounts for every transaction. The focal row is included in its
    cohort baseline; peer_count reports the other observations. This is an
    in-sample screening baseline, not a historical-only backtest.
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

    stats = {}
    for key, members in groups.items():
        values = [float(member["amount"]) for member in members]
        peer_count = len(values) - 1
        if peer_count < min_peer_count:
            stats[key] = (peer_count, None, None)
            continue
        if method == "mad":
            centre = median(values)
            mad = median([abs(value - centre) for value in values])
            scale = MAD_SCALE * mad if mad > 0 else max(abs(centre) * 0.05, 1.0)
        else:
            centre = mean(values)
            scale = pstdev(values)
            scale = scale if scale > 0 else max(abs(centre) * 0.05, 1.0)
        stats[key] = (peer_count, centre, scale)

    output = []
    score_name = "robust z-score" if method == "mad" else "z-score"
    for row in rows:
        peer_count, centre, scale = stats[(row["merchant_id"], row["category"])]
        if centre is None:
            output.append({**row, "peer_count": peer_count, "peer_median": None,
                           "robust_z": None, "is_flagged": 0,
                           "scoring_method": method,
                           "explanation": "Insufficient peer history for reliable screening."})
            continue
        score = (float(row["amount"]) - centre) / scale
        flagged = int(score >= threshold)
        output.append({**row, "peer_count": peer_count,
                       "peer_median": round(centre, 2),
                       "robust_z": round(score, 3), "is_flagged": flagged,
                       "scoring_method": method,
                       "explanation": f"Amount is {float(row['amount']):.2f}, versus cohort median {centre:.2f}; {score_name} {score:.2f}."})
    return output
