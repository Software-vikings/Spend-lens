from spendlens.anomaly import score_transactions
from spendlens.generate import generate_transactions
from spendlens.validation import confusion, scenario_breakdown, run_validation

def test_detector_accepts_parameterised_threshold_and_method():
    rows=generate_transactions(300,seed=9)
    assert len(score_transactions(rows,threshold=4.0))==len(rows)
    assert len(score_transactions(rows,method="zscore"))==len(rows)

def test_detector_rejects_invalid_configuration():
    rows=generate_transactions(20,seed=9)
    try:
        score_transactions(rows,threshold=0)
        assert False,"Expected invalid threshold"
    except ValueError:
        pass

def test_evaluation_scope_excludes_non_target_scenarios():
    rows=generate_transactions()
    scored=score_transactions(rows)
    target=confusion(scored,{"high_value_outlier"})
    all_scenarios=confusion(scored)
    assert target["n"] < all_scenarios["n"]
    assert target["n"] == sum(r["scenario_type"]=="high_value_outlier" or r["scenario_label"]==0 for r in rows)

def test_scenario_breakdown_reports_each_injected_type():
    result=scenario_breakdown(score_transactions(generate_transactions()))
    names={r["scenario_type"] for r in result}
    assert {"high_value_outlier","duplicate_purchase","fragmented_purchase",
            "merchant_price_drift","subscription_price_increase"} <= names

def test_phase5_validation_writes_reproducible_outputs(tmp_path):
    result=run_validation(tmp_path,transaction_count=300)
    assert len(result["seed_results"])==4
    assert len(result["threshold_sensitivity"])==6
    assert (tmp_path/"phase5_validation.json").exists()
