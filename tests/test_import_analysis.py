from datetime import date, timedelta

from spendlens.import_analysis import _parse_amount, analyse_rows


def test_amount_parser_supports_common_financial_number_formats():
    assert _parse_amount("₹1,234.50") == _parse_amount("1.234,50") == 1234.50
    assert _parse_amount("(45.50)") == -45.50


def test_outlier_screen_flags_only_extreme_comparable_amount():
    rows = []
    today = date.today()
    for index in range(9):
        rows.append({
            "transaction_id": f"T-{index}",
            "transaction_date": (today - timedelta(days=index + 1)).isoformat(),
            "employee_id": f"E-{index}",
            "department": "Finance",
            "merchant_name": "Hotel Central",
            "merchant_key": "hotel central",
            "category": "Travel",
            "amount": 100.0,
            "currency": "INR",
            "signals": [],
            "review_status": "NO_FLAG",
            "source_row": index + 2,
        })
    rows.append({
        "transaction_id": "T-OUTLIER",
        "transaction_date": (today - timedelta(days=20)).isoformat(),
        "employee_id": "E-OUTLIER",
        "department": "Finance",
        "merchant_name": "Hotel Central",
        "merchant_key": "hotel central",
        "category": "Travel",
        "amount": 800.0,
        "currency": "INR",
        "signals": [],
        "review_status": "NO_FLAG",
        "source_row": 11,
    })
    mapping = {
        "transaction_date": "Date",
        "merchant_name": "Merchant",
        "amount": "Amount",
        "currency": "Currency",
    }
    result = analyse_rows(rows, "expenses.csv", mapping, [])
    flagged = [row for row in result["items"] if any(
        signal["type"] == "UNUSUAL_AMOUNT" for signal in row["signals"]
    )]
    assert len(flagged) == 1
    assert flagged[0]["transaction_id"] == "T-OUTLIER"
    assert result["summary"]["unusual_amount_signals"] == 1
    assert result["summary"]["rows_with_signals"] == 1
