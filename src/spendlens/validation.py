"""Reproducible robustness, sensitivity and ablation evaluation."""
from __future__ import annotations
import csv, json
from pathlib import Path
from .generate import generate_transactions
from .anomaly import score_transactions

ROOT = Path(__file__).resolve().parents[2]
SEEDS = [7, 42, 101, 2026]
THRESHOLDS = [2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
TARGET = {"high_value_outlier"}

def confusion(scored, positive_types: set[str] | None = None):
    selected = [r for r in scored if positive_types is None or
                r["scenario_type"] in positive_types or int(r["scenario_label"]) == 0]
    tp=sum(int(r["is_flagged"])==1 and int(r["scenario_label"])==1 for r in selected)
    fp=sum(int(r["is_flagged"])==1 and int(r["scenario_label"])==0 for r in selected)
    fn=sum(int(r["is_flagged"])==0 and int(r["scenario_label"])==1 for r in selected)
    tn=sum(int(r["is_flagged"])==0 and int(r["scenario_label"])==0 for r in selected)
    precision=tp/(tp+fp) if tp+fp else 0.0
    recall=tp/(tp+fn) if tp+fn else 0.0
    specificity=tn/(tn+fp) if tn+fp else 0.0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0.0
    return {"n":len(selected),"tp":tp,"fp":fp,"tn":tn,"fn":fn,
      "precision":round(precision,4),"recall":round(recall,4),
      "specificity":round(specificity,4),"f1":round(f1,4)}

def scenario_breakdown(scored):
    types=sorted({r["scenario_type"] for r in scored if int(r["scenario_label"])==1})
    out=[]
    for kind in types:
        subset=[r for r in scored if r["scenario_type"]==kind]
        tp=sum(int(r["is_flagged"])==1 and int(r["scenario_label"])==1 for r in subset)
        fn=sum(int(r["is_flagged"])==0 and int(r["scenario_label"])==1 for r in subset)
        out.append({"scenario_type":kind,"positive_cases":tp+fn,"detected":tp,
                    "missed":fn,"detection_rate":round(tp/(tp+fn),4) if tp+fn else 0})
    return out

def write_csv(path: Path, rows):
    rows=list(rows)
    if not rows:
        path.write_text("",encoding="utf-8"); return
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

def run_validation(output_dir: str | Path | None = None, transaction_count: int = 5000):
    outdir=Path(output_dir) if output_dir else ROOT/"reports"
    outdir.mkdir(parents=True,exist_ok=True)
    sensitivity=[]; seed_metrics=[]; ablation=[]; coverage=[]; scenario_rows=[]
    for seed in SEEDS:
        rows=generate_transactions(n=transaction_count,seed=seed)
        scored=score_transactions(rows)
        seed_metrics.append({"seed":seed,**confusion(scored,TARGET)})
        scenario_rows.extend([{"seed":seed,**r} for r in scenario_breakdown(scored)])
        adequate=sum(1 for r in scored if r["peer_count"]>=8)
        coverage.append({"seed":seed,"transactions":len(rows),"adequate_peer_history":adequate,
                         "coverage_pct":round(adequate/len(rows)*100,2)})
        for threshold in THRESHOLDS:
            candidate=score_transactions(rows,threshold=threshold)
            sensitivity.append({"seed":seed,"threshold":threshold,**confusion(candidate,TARGET)})
        for method in ("mad","zscore"):
            candidate=score_transactions(rows,method=method)
            ablation.append({"seed":seed,"method":method,**confusion(candidate,TARGET)})
    def avg(rows,key):
        return round(sum(r[key] for r in rows)/len(rows),4) if rows else 0
    grouped=[]
    for t in THRESHOLDS:
        group=[r for r in sensitivity if r["threshold"]==t]
        grouped.append({"threshold":t,"mean_precision":avg(group,"precision"),
                        "mean_recall":avg(group,"recall"),"mean_f1":avg(group,"f1"),
                        "mean_false_positives":round(avg(group,"fp"),2),
                        "mean_false_negatives":round(avg(group,"fn"),2)})
    summary={"evaluation_target":"high_value_outlier only",
      "why":"The peer-group amount detector is evaluated only on high-value outlier scenarios. Subscription changes, duplicate candidates, fragmented purchases and merchant drift are separate detectors and are not counted as misses by this model.",
      "seeds":SEEDS,"thresholds":THRESHOLDS,"transactions_per_seed_requested":transaction_count,
      "mean_across_seeds":{"precision":avg(seed_metrics,"precision"),"recall":avg(seed_metrics,"recall"),
                           "specificity":avg(seed_metrics,"specificity"),"f1":avg(seed_metrics,"f1"),
                           "false_positives":avg(seed_metrics,"fp"),"false_negatives":avg(seed_metrics,"fn")},
      "seed_results":seed_metrics,"threshold_sensitivity":grouped,"method_ablation":ablation,
      "peer_coverage":coverage,"scenario_detection":scenario_rows,
      "limitations":["All records are synthetic and scenario construction is known to the evaluation author.",
        "Peer groups are evaluated in-sample: transactions from the same full dataset, including later dates, can contribute to the comparison baseline.",
        "Threshold sensitivity and multi-seed stability do not establish real-world generalisation.",
        "The z-score comparator is an exploratory ablation, not a production alternative.",
        "The detector is one-sided and targets unusually high amounts, not low-value anomalies."]}
    (outdir/"phase5_validation.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    write_csv(outdir/"phase5_seed_metrics.csv",seed_metrics)
    write_csv(outdir/"phase5_threshold_sensitivity.csv",grouped)
    write_csv(outdir/"phase5_scenario_detection.csv",scenario_rows)
    write_csv(outdir/"phase5_method_ablation.csv",ablation)
    write_csv(outdir/"phase5_peer_coverage.csv",coverage)
    return summary

def main():
    result=run_validation()
    print(json.dumps(result["mean_across_seeds"],indent=2))
    print("thresholds:",json.dumps(result["threshold_sensitivity"]))
    print("peer coverage:",json.dumps(result["peer_coverage"]))

if __name__=="__main__": main()
