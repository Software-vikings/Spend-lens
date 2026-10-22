"""Deterministic, policy-driven expense decision engine.

This module is deliberately separate from anomaly scoring: statistical risk signals
may request review, but they never create a policy rejection by themselves.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

ENGINE_VERSION = "0.1.0"
OUTCOMES = {"APPROVE", "REJECT", "REVIEW", "INSUFFICIENT_DATA"}


def _result(rule_id: str, label: str, status: str, explanation: str,
            evidence: dict[str, Any] | None = None, action: str = "none") -> dict:
    return {
        "rule_id": rule_id,
        "label": label,
        "status": status,
        "action": action,
        "explanation": explanation,
        "evidence": evidence or {},
    }


def _amount(value: Any) -> Decimal | None:
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0:
            return None
        return amount.quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return None


def validate_policy(policy: dict) -> None:
    required = {"policy_id", "version", "currency", "eligible_categories",
                "blocked_categories", "category_limits", "receipt_required_categories"}
    missing = required - policy.keys()
    if missing:
        raise ValueError(f"Policy missing fields: {', '.join(sorted(missing))}")
    if not isinstance(policy["policy_id"], str) or not policy["policy_id"].strip():
        raise ValueError("Policy ID must be a non-empty string")
    if not isinstance(policy["version"], str) or not policy["version"].strip():
        raise ValueError("Policy version must be a non-empty string")
    currency = policy["currency"]
    if not isinstance(currency, str) or len(currency) != 3 or not currency.isalpha() or not currency.isupper():
        raise ValueError("Policy currency must be a three-letter uppercase code")
    for field in ("eligible_categories", "blocked_categories", "receipt_required_categories"):
        values = policy[field]
        if not isinstance(values, list) or any(not isinstance(x, str) or not x.strip() for x in values):
            raise ValueError(f"{field} must be an array of non-empty category names")
        if len(values) != len(set(values)):
            raise ValueError(f"{field} cannot contain duplicate categories")
    eligible = set(policy["eligible_categories"])
    blocked = set(policy["blocked_categories"])
    receipt_required = set(policy["receipt_required_categories"])
    if eligible & blocked:
        raise ValueError("A category cannot be both eligible and blocked")
    if not receipt_required <= eligible:
        raise ValueError("Receipt-required categories must be eligible categories")
    if not isinstance(policy["category_limits"], dict):
        raise ValueError("category_limits must be an object")
    for category, limit in policy["category_limits"].items():
        if category not in eligible:
            raise ValueError(f"Category limit refers to non-eligible category: {category}")
        amount = _amount(limit)
        if amount is None or amount <= 0:
            raise ValueError(f"Invalid positive amount limit for category {category}")
    action = policy.get("over_limit_action", "REVIEW")
    if action not in {"REJECT", "REVIEW"}:
        raise ValueError("over_limit_action must be REJECT or REVIEW")
    for field in ("require_business_purpose",):
        if field in policy and not isinstance(policy[field], bool):
            raise ValueError(f"{field} must be a boolean")


def evaluate_expense(expense: dict, policy: dict) -> dict:
    """Evaluate one expense against one explicit policy version.

    Output is deterministic for identical inputs. Missing critical evidence
    produces INSUFFICIENT_DATA; ambiguity produces REVIEW. Only explicit
    hard-stop rules can produce REJECT.
    """
    validate_policy(policy)
    checks: list[dict] = []
    hard_reject = False
    needs_review = False
    insufficient = False

    required_fields = ("expense_id", "employee_id", "merchant_name", "department", "amount", "currency", "category", "transaction_date")
    missing = [field for field in required_fields if expense.get(field) in (None, "")]
    amount = _amount(expense.get("amount"))
    if amount is None and "amount" not in missing:
        missing.append("valid amount")
    elif amount == Decimal("0.00"):
        missing.append("amount must be greater than zero")
    if missing:
        insufficient = True
        checks.append(_result("INPUT-001", "Required expense data", "INSUFFICIENT",
            "Required fields are missing or invalid.", {"missing_fields": missing}, "INSUFFICIENT_DATA"))
    else:
        checks.append(_result("INPUT-001", "Required expense data", "PASS",
            "Required expense fields are present and valid.",
            {"expense_id": expense["expense_id"], "amount": str(amount)}))

    try:
        date.fromisoformat(str(expense.get("transaction_date", "")))
        date_valid = True
    except (TypeError, ValueError):
        date_valid = False
    if not date_valid:
        insufficient = True
        checks.append(_result("INPUT-002", "Expense date", "INSUFFICIENT",
            "A valid ISO expense date is required.", {"value": expense.get("transaction_date")}, "INSUFFICIENT_DATA"))
    elif date.fromisoformat(str(expense["transaction_date"])) > date.today():
        insufficient = True
        checks.append(_result("INPUT-002", "Expense date", "INSUFFICIENT",
            "The expense date is in the future. Check the submitted date before evaluation.",
            {"date": expense["transaction_date"], "evaluated_on": date.today().isoformat()}, "INSUFFICIENT_DATA"))
    else:
        checks.append(_result("INPUT-002", "Expense date", "PASS",
            "Expense date is valid and is not in the future.", {"date": expense["transaction_date"]}))

    currency = expense.get("currency")
    if not currency:
        insufficient = True
        checks.append(_result("POL-001", "Policy currency", "INSUFFICIENT",
            "Expense currency is missing; the system cannot compare it with the policy currency.",
            {"policy_currency": policy["currency"]}, "INSUFFICIENT_DATA"))
    elif len(str(currency)) != 3 or not str(currency).isalpha() or not str(currency).isupper():
        insufficient = True
        checks.append(_result("INPUT-003", "Currency format", "INSUFFICIENT",
            "Currency must be a three-letter uppercase ISO-style code.",
            {"currency": currency}, "INSUFFICIENT_DATA"))
    elif currency != policy["currency"]:
        needs_review = True
        checks.append(_result("POL-001", "Policy currency", "REVIEW",
            "Expense currency differs from the policy currency; conversion is not configured.",
            {"expense_currency": currency, "policy_currency": policy["currency"]}, "REVIEW"))
    else:
        checks.append(_result("POL-001", "Policy currency", "PASS",
            "Expense currency matches the policy currency.", {"currency": currency}))

    category = expense.get("category")
    if category in policy["blocked_categories"]:
        hard_reject = True
        checks.append(_result("POL-002", "Blocked category", "FAIL",
            "This category is explicitly blocked by the configured policy.",
            {"category": category}, "REJECT"))
    elif category not in policy["eligible_categories"]:
        needs_review = True
        checks.append(_result("POL-002", "Eligible category", "REVIEW",
            "This category is not explicitly listed as eligible in the policy.",
            {"category": category}, "REVIEW"))
    else:
        checks.append(_result("POL-002", "Eligible category", "PASS",
            "This category is listed as eligible.", {"category": category}))

    if amount is not None and category in policy["category_limits"]:
        limit = Decimal(str(policy["category_limits"][category]))
        if amount > limit:
            action = policy.get("over_limit_action", "REVIEW")
            hard_reject = hard_reject or action == "REJECT"
            needs_review = needs_review or action == "REVIEW"
            checks.append(_result("POL-003", "Category spending limit", action,
                "Expense exceeds the configured category limit.",
                {"amount": str(amount), "limit": str(limit), "category": category}, action))
        else:
            checks.append(_result("POL-003", "Category spending limit", "PASS",
                "Expense is within the configured category limit.",
                {"amount": str(amount), "limit": str(limit), "category": category}))
    else:
        checks.append(_result("POL-003", "Category spending limit", "NOT_APPLICABLE",
            "No category-specific limit is configured.", {"category": category}))

    if policy.get("require_business_purpose", True) and not str(expense.get("business_purpose", "")).strip():
        insufficient = True
        checks.append(_result("EVD-001", "Business purpose", "INSUFFICIENT",
            "A business purpose is required by policy.", {}, "INSUFFICIENT_DATA"))
    else:
        checks.append(_result("EVD-001", "Business purpose", "PASS",
            "Business purpose requirement is satisfied.",
            {"business_purpose": expense.get("business_purpose", "")}))

    receipt_required = category in policy["receipt_required_categories"]
    receipt = expense.get("receipt") or {}
    if receipt_required and not receipt.get("provided", False):
        insufficient = True
        checks.append(_result("EVD-002", "Receipt evidence", "INSUFFICIENT",
            "A receipt is required by policy but was not supplied.", {}, "INSUFFICIENT_DATA"))
    elif receipt_required and not receipt.get("readable", False):
        insufficient = True
        checks.append(_result("EVD-002", "Receipt evidence", "INSUFFICIENT",
            "A receipt was supplied but is not marked readable.", {}, "INSUFFICIENT_DATA"))
    elif receipt_required:
        checks.append(_result("EVD-002", "Receipt evidence", "PASS",
            "Required receipt evidence is present and marked readable.", {"receipt_id": receipt.get("receipt_id")}))
        receipt_amount = _amount(receipt.get("total"))
        if receipt_amount is None:
            insufficient = True
            checks.append(_result("EVD-003", "Receipt amount match", "INSUFFICIENT",
                "Receipt total is missing or invalid.", {}, "INSUFFICIENT_DATA"))
        elif amount is not None and receipt_amount != amount:
            needs_review = True
            checks.append(_result("EVD-003", "Receipt amount match", "REVIEW",
                "Receipt total does not match the claimed amount.",
                {"claim_amount": str(amount), "receipt_total": str(receipt_amount)}, "REVIEW"))
        else:
            checks.append(_result("EVD-003", "Receipt amount match", "PASS",
                "Receipt total matches the claimed amount.", {"receipt_total": str(receipt_amount)}))
    else:
        checks.append(_result("EVD-002", "Receipt evidence", "NOT_APPLICABLE",
            "No receipt requirement is configured for this category."))

    if expense.get("duplicate_suspected", False):
        needs_review = True
        checks.append(_result("RISK-001", "Duplicate claim signal", "REVIEW",
            "A possible duplicate was detected. This is a review signal, not an automatic rejection.",
            {"duplicate_suspected": True,
             "match": expense.get("duplicate_match")}, "REVIEW"))
    else:
        checks.append(_result("RISK-001", "Duplicate claim signal", "PASS",
            "No duplicate signal was supplied.", {"duplicate_suspected": False}))

    if hard_reject:
        outcome = "REJECT"
    elif insufficient:
        outcome = "INSUFFICIENT_DATA"
    elif needs_review:
        outcome = "REVIEW"
    else:
        outcome = "APPROVE"

    return {
        "expense_id": expense.get("expense_id"),
        "outcome": outcome,
        "policy_id": policy["policy_id"],
        "policy_version": policy["version"],
        "engine_version": ENGINE_VERSION,
        "evaluated_rules": checks,
        "decision_explanation": {
            "REJECT": "One or more explicit hard-stop policy rules failed.",
            "INSUFFICIENT_DATA": "The system cannot safely decide because required information or evidence is missing.",
            "REVIEW": "The expense needs an exception or further assessment; no automatic rejection was made.",
            "APPROVE": "All applicable configured policy checks passed.",
        }[outcome],
    }
