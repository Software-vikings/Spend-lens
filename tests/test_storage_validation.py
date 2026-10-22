import pytest
from spendlens.storage import validate_transactions

def valid_row():
    return {"transaction_id":"T1","transaction_date":"2026-01-01","employee_id":"E1",
      "department":"Finance","merchant_id":"M1","merchant_name":"Merchant",
      "category":"Software","amount":"12.50","currency":"EUR","payment_method":"Card"}

def test_valid_rows_pass():
    validate_transactions([valid_row()])

def test_duplicate_ids_rejected():
    with pytest.raises(ValueError, match="duplicate transaction_id"):
        validate_transactions([valid_row(),valid_row()])

def test_negative_amount_rejected():
    row=valid_row(); row["amount"]="-1"
    with pytest.raises(ValueError, match="amount cannot be negative"):
        validate_transactions([row])

def test_invalid_date_rejected():
    row=valid_row(); row["transaction_date"]="not-a-date"
    with pytest.raises(ValueError, match="invalid transaction_date"):
        validate_transactions([row])
