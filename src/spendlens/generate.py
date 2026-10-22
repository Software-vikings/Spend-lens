"""Create reproducible synthetic company-spend transactions and labelled test scenarios."""
from __future__ import annotations
import random
from datetime import date, timedelta
from pathlib import Path
import csv

DEPARTMENTS = ["Engineering", "Sales", "Marketing", "Operations", "Finance"]
MERCHANTS = [
    ("M001", "CloudNorth", "Software"), ("M002", "OfficeHub", "Office Supplies"),
    ("M003", "RailConnect", "Travel"), ("M004", "StayWell", "Travel"),
    ("M005", "DataWorks", "Software"), ("M006", "FreshTable", "Meals"),
    ("M007", "DesignCloud", "Software"), ("M008", "CityCab", "Travel"),
    ("M009", "PrintHouse", "Office Supplies"), ("M010", "LearnNow", "Training"),
]
BASE = {"Software": (115, 35), "Office Supplies": (48, 18), "Travel": (185, 90),
        "Meals": (32, 12), "Training": (145, 55), "Specialist Supplies": (100, 8)}

def generate_transactions(n: int = 5000, seed: int = 42) -> list[dict]:
    rng = random.Random(seed)
    start = date(2026, 1, 1)
    employee_dept = {f"E{i:04d}": rng.choice(DEPARTMENTS) for i in range(1, 151)}
    rows = []
    for i in range(n):
        mid, merchant, category = rng.choice(MERCHANTS)
        mean, sd = BASE[category]
        amount = max(5.0, rng.gauss(mean, sd))
        label, scenario = 0, "ordinary"
        if i % 173 == 0:
            amount, label, scenario = rng.uniform(650, 1200), 1, "high_value_outlier"
        tx_date = start + timedelta(days=rng.randrange(180))
        employee = f"E{rng.randrange(1, 151):04d}"
        rows.append({
            "transaction_id": f"TX{i+1:06d}", "transaction_date": tx_date.isoformat(),
            "employee_id": employee, "department": employee_dept[employee],
            "merchant_id": mid, "merchant_name": merchant, "category": category,
            "amount": round(amount, 2), "currency": "EUR",
            "payment_method": rng.choice(["Company Card", "Virtual Card"]),
            "scenario_label": label, "scenario_type": scenario,
            "subscription_id": "", "invoice_reference": f"INV-{i+1:06d}",
        })
    for j in range(18):
        employee = f"E{j+1:04d}"
        merchant = "CloudNorth" if j % 2 == 0 else "DataWorks"
        mid = "M001" if j % 2 == 0 else "M005"
        base_amount = 75 + j * 3
        for month in range(6):
            amount = base_amount
            label, scenario = 0, "recurring_payment"
            if j == 0 and month == 5:
                amount, label, scenario = base_amount * 1.35, 1, "subscription_price_increase"
            rows.append({
                "transaction_id": f"SUB{j+1:03d}-{month+1:02d}",
                "transaction_date": date(2026, month+1, 5).isoformat(),
                "employee_id": employee, "department": employee_dept[employee],
                "merchant_id": mid, "merchant_name": merchant, "category": "Software",
                "amount": round(amount, 2), "currency": "EUR", "payment_method": "Company Card",
                "scenario_label": label, "scenario_type": scenario,
                "subscription_id": f"SUB-{j+1:03d}", "invoice_reference": f"SUBINV-{j+1:03d}-{month+1:02d}",
            })
    template = dict(rows[100])
    template.update(transaction_id="DUP-001", transaction_date="2026-05-14",
                    employee_id="E0007", merchant_id="M002", merchant_name="OfficeHub",
                    category="Office Supplies", amount=89.90, invoice_reference="INV-DUP-77",
                    scenario_label=1, scenario_type="duplicate_purchase", subscription_id="")
    rows.append(template)
    duplicate = dict(template); duplicate["transaction_id"] = "DUP-002"
    rows.append(duplicate)
    for k, amount in enumerate([220.0, 190.0, 175.0], start=1):
        rows.append({
            "transaction_id": f"SPLIT-{k:03d}", "transaction_date": "2026-06-10",
            "employee_id": "E0012", "department": employee_dept["E0012"],
            "merchant_id": "M009", "merchant_name": "PrintHouse", "category": "Office Supplies",
            "amount": amount, "currency": "EUR", "payment_method": "Company Card",
            "scenario_label": 1, "scenario_type": "fragmented_purchase",
            "subscription_id": "", "invoice_reference": f"SPLIT-INV-{k:03d}",
        })
    for month in range(1, 7):
        unit_amount = 100.0 if month <= 4 else 140.0
        for k in range(3):
            rows.append({
                "transaction_id": f"DRIFT-{month:02d}-{k+1:02d}",
                "transaction_date": date(2026, month, 12 + k).isoformat(),
                "employee_id": f"E{20+k:04d}",
                "department": employee_dept[f"E{20+k:04d}"],
                "merchant_id": "M011", "merchant_name": "PaperTrail Supplies",
                "category": "Specialist Supplies", "amount": round(unit_amount, 2),
                "currency": "EUR", "payment_method": "Company Card",
                "scenario_label": 1 if month >= 5 else 0,
                "scenario_type": "merchant_price_drift" if month >= 5 else "ordinary",
                "subscription_id": "", "invoice_reference": f"DRIFT-INV-{month:02d}-{k+1:02d}",
            })
    return rows

def write_csv(rows: list[dict], path: str | Path) -> None:
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)
