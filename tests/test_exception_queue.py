from test_api import prepared_db, KEYS, ANALYST, VIEWER
from fastapi.testclient import TestClient
from spendlens.api import create_app


def test_exception_assignment_and_queue_filters(tmp_path):
    db, _ = prepared_db(tmp_path)
    client = TestClient(create_app(db, api_keys=KEYS))
    expense = {
        "expense_id": "QUEUE-001", "employee_id": "EMP-Q",
        "merchant_name": "City Cafe", "department": "Sales",
        "amount": "85.00", "currency": "EUR", "category": "Meals",
        "transaction_date": "2026-05-20", "business_purpose": "Client lunch",
        "receipt": {"provided": False},
    }
    result = client.post("/v1/expenses/evaluate",
        headers={"X-API-Key": ANALYST}, json={"expense": expense})
    assert result.status_code == 200
    assert result.json()["outcome"] == "INSUFFICIENT_DATA"

    url = "/v1/claims/QUEUE-001/assignment"
    payload = {"assignee": "Analyst A", "assigned_by": "Team Lead",
               "priority": "URGENT", "sla_hours": 24, "note": "Receipt exception"}
    assert client.post(url, headers={"X-API-Key": VIEWER}, json=payload).status_code == 403
    assert client.post(url, headers={"X-API-Key": ANALYST}, json=payload).status_code == 200

    queue = client.get("/v1/exception-queue?assignee=Analyst%20A&priority=URGENT",
                       headers={"X-API-Key": VIEWER})
    assert queue.status_code == 200
    assert queue.json()["total"] == 1
    claim = queue.json()["items"][0]
    assert claim["assignee"] == "Analyst A"
    assert claim["priority"] == "URGENT"
    assert claim["sla_hours"] == 24
    assert claim["overdue"] == 0
    assert claim["due_at"] > claim["assigned_at"]
    assert client.get("/v1/exception-queue?overdue=true",
                      headers={"X-API-Key": VIEWER}).json()["total"] == 0
    assert client.post(url, headers={"X-API-Key": ANALYST},
                       json={**payload, "priority": "CRITICAL"}).status_code == 422
    assert client.get("/v1/exception-queue").status_code == 401


def test_exception_queue_pagination_and_empty_filter(tmp_path):
    db, _ = prepared_db(tmp_path)
    client = TestClient(create_app(db, api_keys=KEYS))
    headers = {"X-API-Key": ANALYST}
    for index in range(3):
        expense = {
            "expense_id": f"QUEUE-PAGE-{index}", "employee_id": f"EMP-{index}",
            "merchant_name": "City Cafe", "department": "Sales",
            "amount": "85.00", "currency": "EUR", "category": "Meals",
            "transaction_date": "2026-05-20", "business_purpose": "Client lunch",
            "receipt": {"provided": False},
        }
        assert client.post("/v1/expenses/evaluate", headers=headers,
                           json={"expense": expense}).status_code == 200
    page = client.get("/v1/exception-queue?limit=2&offset=1",
                      headers={"X-API-Key": VIEWER}).json()
    assert page["total"] == 3
    assert len(page["items"]) == 2
