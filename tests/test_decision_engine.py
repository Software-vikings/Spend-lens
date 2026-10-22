import json
from pathlib import Path
import pytest

from spendlens.decision_engine import evaluate_expense, validate_policy

POLICY = json.loads((Path(__file__).parents[1] / "policies" / "demo_policy.json").read_text())

def expense(**changes):
    value = {
        "expense_id": "EXP-001", "employee_id": "EMP-1001", "merchant_name": "City Cafe", "department": "Sales", "amount": "85.00", "currency": "EUR",
        "category": "Meals", "transaction_date": "2026-05-14",
        "business_purpose": "Client project working lunch",
        "receipt": {"provided": True, "readable": True, "receipt_id": "R-001", "total": "85.00"},
        "duplicate_suspected": False,
    }
    value.update(changes)
    return value

def test_compliant_expense_is_approved_with_rule_explanations():
    result = evaluate_expense(expense(), POLICY)
    assert result["outcome"] == "APPROVE"
    assert result["policy_version"] == "1.0.0"
    assert result["engine_version"]
    assert all("rule_id" in rule and "explanation" in rule for rule in result["evaluated_rules"])

def test_explicitly_blocked_category_is_rejected():
    result = evaluate_expense(expense(category="Personal Entertainment"), POLICY)
    assert result["outcome"] == "REJECT"
    assert any(rule["rule_id"] == "POL-002" and rule["action"] == "REJECT" for rule in result["evaluated_rules"])

def test_missing_receipt_returns_insufficient_data_not_approval():
    result = evaluate_expense(expense(receipt={"provided": False}), POLICY)
    assert result["outcome"] == "INSUFFICIENT_DATA"

def test_receipt_amount_mismatch_routes_to_review():
    result = evaluate_expense(expense(receipt={"provided": True, "readable": True, "total": "95"}), POLICY)
    assert result["outcome"] == "REVIEW"

def test_duplicate_signal_does_not_auto_reject():
    result = evaluate_expense(expense(duplicate_suspected=True), POLICY)
    assert result["outcome"] == "REVIEW"

def test_over_limit_action_is_configurable():
    policy = dict(POLICY, over_limit_action="REJECT")
    result = evaluate_expense(expense(amount="101", receipt={"provided": True, "readable": True, "total": "101"}), policy)
    assert result["outcome"] == "REJECT"
    assert any(rule["rule_id"] == "POL-003" and rule["action"] == "REJECT" for rule in result["evaluated_rules"])

def test_missing_business_purpose_is_insufficient_data():
    result = evaluate_expense(expense(business_purpose=""), POLICY)
    assert result["outcome"] == "INSUFFICIENT_DATA"

def test_currency_mismatch_routes_to_review():
    result = evaluate_expense(expense(currency="USD"), POLICY)
    assert result["outcome"] == "REVIEW"

def test_identical_inputs_are_deterministic():
    assert evaluate_expense(expense(), POLICY) == evaluate_expense(expense(), POLICY)

def test_policy_rejects_unsupported_over_limit_action():
    with pytest.raises(ValueError, match="over_limit_action"):
        validate_policy(dict(POLICY, over_limit_action="AUTO_APPROVE"))


def test_zero_amount_is_insufficient_data_not_approved():
    result = evaluate_expense(expense(amount="0"), POLICY)
    assert result["outcome"] == "INSUFFICIENT_DATA"
    assert any("amount must be greater than zero" in str(rule["evidence"]) for rule in result["evaluated_rules"])


def test_future_dated_expense_is_insufficient_data():
    from datetime import date, timedelta
    future = (date.today() + timedelta(days=1)).isoformat()
    result = evaluate_expense(expense(transaction_date=future), POLICY)
    assert result["outcome"] == "INSUFFICIENT_DATA"
    assert any(rule["rule_id"] == "INPUT-002" and rule["status"] == "INSUFFICIENT"
               for rule in result["evaluated_rules"])


def test_malformed_currency_is_insufficient_data():
    result = evaluate_expense(expense(currency="EURO"), POLICY)
    assert result["outcome"] == "INSUFFICIENT_DATA"
    assert any(rule["rule_id"] == "INPUT-003" for rule in result["evaluated_rules"])


def test_missing_claim_identity_context_is_insufficient_data():
    incomplete = expense(merchant_name="", employee_id="", department="")
    result = evaluate_expense(incomplete, POLICY)
    assert result["outcome"] == "INSUFFICIENT_DATA"
    required = next(rule for rule in result["evaluated_rules"] if rule["rule_id"] == "INPUT-001")
    assert "merchant_name" in required["evidence"]["missing_fields"]
    assert "employee_id" in required["evidence"]["missing_fields"]
    assert "department" in required["evidence"]["missing_fields"]
