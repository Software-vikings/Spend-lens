"""Phase 2 financial intelligence analyses.

These are screening signals for human review, not automated accusations or
proof of fraud, waste, or policy violations.
"""
from __future__ import annotations
from collections import defaultdict
from statistics import median

def _month(value: str) -> str:
    return value[:7]

def recurring_payment_findings(rows: list[dict], change_threshold: float = 0.20) -> list[dict]:
    groups = defaultdict(list)
    for r in rows:
        if r.get("subscription_id"):
            groups[r["subscription_id"]].append(r)
    findings = []
    for sid, items in groups.items():
        items = sorted(items, key=lambda x: x["transaction_date"])
        if len(items) < 4:
            continue
        prior = [float(x["amount"]) for x in items[:-1]]
        baseline = median(prior)
        latest = float(items[-1]["amount"])
        change = (latest - baseline) / baseline if baseline else 0
        if abs(change) >= change_threshold:
            findings.append({"subscription_id": sid, "employee_id": items[-1]["employee_id"],
                "merchant_name": items[-1]["merchant_name"], "baseline_amount": round(baseline, 2),
                "latest_amount": round(latest, 2), "change_pct": round(change * 100, 2),
                "observations": len(items),
                "explanation": f"Latest payment changed {change:+.1%} versus the historical median."})
    return sorted(findings, key=lambda x: abs(x["change_pct"]), reverse=True)

def merchant_price_drift_findings(rows: list[dict], min_per_period: int = 3,
                                  increase_threshold: float = 0.20) -> list[dict]:
    monthly = defaultdict(list)
    for r in rows:
        monthly[(r["merchant_id"], r["merchant_name"], r["category"], _month(r["transaction_date"]))].append(float(r["amount"]))
    merchants = defaultdict(dict)
    for (mid, name, category, month), amounts in monthly.items():
        merchants[(mid, name, category)][month] = amounts
    findings = []
    for (mid, name, category), by_month in merchants.items():
        months = sorted(by_month)
        if len(months) < 4:
            continue
        earlier, recent = months[-4:-2], months[-2:]
        if any(len(by_month[m]) < min_per_period for m in earlier + recent):
            continue
        old_values = [x for m in earlier for x in by_month[m]]
        new_values = [x for m in recent for x in by_month[m]]
        old_med, new_med = median(old_values), median(new_values)
        change = (new_med - old_med) / old_med if old_med else 0
        if change >= increase_threshold:
            findings.append({"merchant_id": mid, "merchant_name": name, "category": category,
                "baseline_median": round(old_med, 2), "recent_median": round(new_med, 2),
                "increase_pct": round(change * 100, 2), "baseline_transactions": len(old_values),
                "recent_transactions": len(new_values),
                "explanation": f"Recent median transaction amount is {change:.1%} above the earlier comparison period."})
    return sorted(findings, key=lambda x: x["increase_pct"], reverse=True)

def department_spend_per_employee(rows: list[dict], headcount: dict[str, int]) -> list[dict]:
    totals = defaultdict(float)
    for r in rows:
        totals[(_month(r["transaction_date"]), r["department"])] += float(r["amount"])
    output = []
    for (month, department), spend in sorted(totals.items()):
        count = headcount.get(department)
        output.append({"month": month, "department": department, "total_spend": round(spend, 2),
            "headcount": count, "spend_per_employee": round(spend / count, 2) if count else None})
    return output

def duplicate_candidates(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for r in rows:
        key = (r["employee_id"], r["merchant_id"], r["transaction_date"], round(float(r["amount"]), 2))
        groups[key].append(r)
    findings = []
    for key, items in groups.items():
        if len(items) > 1:
            findings.append({"employee_id": key[0], "merchant_id": key[1], "transaction_date": key[2],
                "amount": key[3], "transaction_ids": [x["transaction_id"] for x in items],
                "duplicate_count": len(items),
                "explanation": "Same employee, merchant, date and amount appear more than once."})
    return findings

def fragmented_purchase_candidates(rows: list[dict], thresholds: dict[str, float]) -> list[dict]:
    groups = defaultdict(list)
    for r in rows:
        groups[(r["employee_id"], r["merchant_id"], r["transaction_date"], r["category"])].append(r)
    findings = []
    for (employee, merchant, tx_date, category), items in groups.items():
        threshold = thresholds.get(category)
        if threshold is None or len(items) < 2:
            continue
        amounts = [float(x["amount"]) for x in items]
        total = sum(amounts)
        if total > threshold and all(x < threshold for x in amounts):
            findings.append({"employee_id": employee, "merchant_id": merchant, "transaction_date": tx_date,
                "category": category, "transaction_ids": [x["transaction_id"] for x in items],
                "transaction_count": len(items), "combined_amount": round(total, 2), "threshold": threshold,
                "explanation": f"{len(items)} individually sub-threshold purchases total {total:.2f}, above {threshold:.2f}."})
    return findings
