from spendlens.generate import generate_transactions
from spendlens.insights import (recurring_payment_findings, merchant_price_drift_findings,
    department_spend_per_employee, duplicate_candidates, fragmented_purchase_candidates)

def test_recurring_payment_price_change_is_found():
    rows = generate_transactions()
    findings = recurring_payment_findings(rows)
    assert any(x["subscription_id"] == "SUB-001" for x in findings)

def test_duplicate_scenario_is_found():
    rows = generate_transactions()
    findings = duplicate_candidates(rows)
    assert any(x["duplicate_count"] == 2 for x in findings)

def test_fragmented_purchase_scenario_is_found():
    rows = generate_transactions()
    findings = fragmented_purchase_candidates(rows, {"Office Supplies": 500})
    assert any(x["employee_id"] == "E0012" for x in findings)

def test_department_spend_has_per_employee_metric():
    rows = generate_transactions(100)
    result = department_spend_per_employee(rows, {"Engineering": 10, "Sales": 10,
        "Marketing": 10, "Operations": 10, "Finance": 10})
    assert result and all(x["spend_per_employee"] is not None for x in result)

def test_price_drift_function_returns_valid_structure():
    rows = generate_transactions()
    findings = merchant_price_drift_findings(rows)
    assert isinstance(findings, list)
    assert all("increase_pct" in x for x in findings)

def test_isolated_merchant_price_drift_is_found():
    rows = generate_transactions()
    findings = merchant_price_drift_findings(rows)
    assert any(x["merchant_id"] == "M011" and x["increase_pct"] >= 20 for x in findings)
