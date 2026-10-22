from spendlens.generate import generate_transactions
from spendlens.anomaly import score_transactions
from spendlens.pipeline import evaluate

def test_generator_is_reproducible():
    assert generate_transactions(20, 7) == generate_transactions(20, 7)

def test_generator_has_unique_ids():
    rows = generate_transactions(500)
    assert len({r["transaction_id"] for r in rows}) == len(rows)

def test_scorer_returns_explanation_and_flag():
    rows = generate_transactions(1000)
    scored = score_transactions(rows)
    assert len(scored) == len(rows)
    assert all("explanation" in r and "is_flagged" in r for r in scored)

def test_evaluation_counts_reconcile():
    rows = generate_transactions(1000)
    metrics = evaluate(score_transactions(rows))
    expected = sum(r["scenario_type"] == "high_value_outlier" or r["scenario_label"] == 0 for r in rows)
    assert (metrics["true_positive"] + metrics["false_positive"] +
            metrics["true_negative"] + metrics["false_negative"]) == expected
    assert metrics["evaluation_target"] == "high_value_outlier"
