"""Run the reproducible SpendLens Phase 1 + Phase 2 pipeline."""
import csv, json, sqlite3, uuid
from pathlib import Path
from .generate import generate_transactions, write_csv
from .anomaly import score_transactions
from .insights import (recurring_payment_findings, merchant_price_drift_findings,
                       department_spend_per_employee, duplicate_candidates,
                       fragmented_purchase_candidates)
from .storage import create_database, load_transactions
from .phase4 import init_phase4, persist_findings, record_run
ROOT = Path(__file__).resolve().parents[2]

def evaluate(scored):
    selected = [r for r in scored if r.get("scenario_type") == "high_value_outlier"
                or int(r.get("scenario_label", 0)) == 0]
    tp = sum(r["is_flagged"] == 1 and r["scenario_type"] == "high_value_outlier" for r in selected)
    fp = sum(r["is_flagged"] == 1 and int(r["scenario_label"]) == 0 for r in selected)
    fn = sum(r["is_flagged"] == 0 and r["scenario_type"] == "high_value_outlier" for r in selected)
    tn = sum(r["is_flagged"] == 0 and int(r["scenario_label"]) == 0 for r in selected)
    precision = tp/(tp+fp) if tp+fp else 0
    recall = tp/(tp+fn) if tp+fn else 0
    specificity = tn/(tn+fp) if tn+fp else 0
    return {"evaluation_target":"high_value_outlier","n_evaluated":len(selected),
            "true_positive":tp,"false_positive":fp,"true_negative":tn,"false_negative":fn,
            "precision":round(precision,4),"recall":round(recall,4),"specificity":round(specificity,4),
            "f1":round(2*precision*recall/(precision+recall),4) if precision+recall else 0,
            "note":"Synthetic scenario evaluation only; the peer anomaly detector is evaluated only against high_value_outlier cases. Other scenario types are handled by separate screens."}

def write_report(name, rows):
    path = ROOT / "reports" / name
    rows = list(rows)
    if not rows:
        path.write_text("No findings in this run.\n", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader(); writer.writerows(rows)

def export_powerbi_tables(rows, scored):
    """Write tidy CSV tables for a Power BI semantic model."""
    reports = ROOT / "reports"
    def export(name, records):
        records = list(records)
        if not records:
            (reports/name).write_text("", encoding="utf-8")
            return
        with (reports/name).open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
            writer.writeheader(); writer.writerows(records)
    clean = [{k:v for k,v in r.items() if k not in ("scenario_label","scenario_type")} for r in rows]
    export("pbi_transactions.csv", clean)
    dates = sorted({r["transaction_date"] for r in rows})
    export("pbi_date.csv", [{"date": d, "year": int(d[:4]), "month_number": int(d[5:7]), "month": d[:7]} for d in dates])
    headcount = [{"department":"Engineering","headcount":42},{"department":"Sales","headcount":31},
        {"department":"Marketing","headcount":18},{"department":"Operations","headcount":35},
        {"department":"Finance","headcount":12}]
    export("pbi_department_headcount.csv", headcount)
    export("pbi_anomaly_findings.csv", [{k:v for k,v in r.items() if k not in ("scenario_label","scenario_type")} for r in scored if r["is_flagged"]])
    from .insights import (recurring_payment_findings, merchant_price_drift_findings,
                           duplicate_candidates, fragmented_purchase_candidates)
    export("pbi_recurring_findings.csv", recurring_payment_findings(rows))
    export("pbi_merchant_drift.csv", merchant_price_drift_findings(rows))
    export("pbi_duplicate_candidates.csv", duplicate_candidates(rows))
    export("pbi_fragmented_candidates.csv", fragmented_purchase_candidates(rows, {"Office Supplies":500,"Software":1000,"Travel":1200}))

def main():
    data, reports = ROOT/"data", ROOT/"reports"
    data.mkdir(exist_ok=True); reports.mkdir(exist_ok=True)
    rows = generate_transactions()
    csv_path, db_path = data/"transactions.csv", data/"spendlens.db"
    write_csv(rows, csv_path)
    create_database(db_path)
    init_phase4(db_path)
    with sqlite3.connect(db_path) as conn: conn.execute("DELETE FROM transactions")
    load_transactions(csv_path, db_path)
    scored = score_transactions(rows)
    export_powerbi_tables(rows, scored)
    write_report("anomaly_findings.csv", [r for r in scored if r["is_flagged"]])
    write_report("recurring_payment_findings.csv", recurring_payment_findings(rows))
    write_report("merchant_price_drift.csv", merchant_price_drift_findings(rows))
    headcount = {"Engineering": 42, "Sales": 31, "Marketing": 18, "Operations": 35, "Finance": 12}
    write_report("department_spend_per_employee.csv", department_spend_per_employee(rows, headcount))
    write_report("duplicate_candidates.csv", duplicate_candidates(rows))
    write_report("fragmented_purchase_candidates.csv", fragmented_purchase_candidates(rows, {"Office Supplies": 500, "Software": 1000, "Travel": 1200}))
    metrics = evaluate(scored)
    run_id = str(uuid.uuid4())
    finding_groups = {"anomaly":[r for r in scored if r["is_flagged"]],
        "recurring_payment_change":recurring_payment_findings(rows),
        "merchant_price_drift":merchant_price_drift_findings(rows),
        "duplicate_candidate":duplicate_candidates(rows),
        "fragmented_purchase":fragmented_purchase_candidates(rows, {"Office Supplies":500,"Software":1000,"Travel":1200})}
    finding_count = persist_findings(db_path, finding_groups, run_id)
    record_run(db_path, run_id, len(rows), finding_count)
    (reports/"evaluation.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(f"Transactions processed: {len(rows)}")
    print(f"Anomaly flags: {sum(r['is_flagged'] for r in scored)}")
    print(f"Recurring payment changes: {len(recurring_payment_findings(rows))}")
    print(f"Merchant price drift findings: {len(merchant_price_drift_findings(rows))}")
    print(f"Duplicate groups: {len(duplicate_candidates(rows))}")
    print(f"Fragmented purchase groups: {len(fragmented_purchase_candidates(rows, {'Office Supplies':500,'Software':1000,'Travel':1200}))}")
    print(f"Historical finding records upserted: {finding_count}")
    print(f"Run ID: {run_id}")
    print(f"Evaluation: {json.dumps(metrics)}")

if __name__ == "__main__": main()
