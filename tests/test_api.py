from spendlens.storage import create_database, load_transactions
from spendlens.phase4 import init_phase4, persist_findings, record_run
from spendlens.generate import generate_transactions, write_csv
from spendlens.api import create_app
from fastapi.testclient import TestClient

VIEWER="viewer-key-0123456789abcdef012345"
ANALYST="analyst-key-0123456789abcdef0123"
ADMIN="admin-key-0123456789abcdef012345"
KEYS={VIEWER:"viewer",ANALYST:"analyst",ADMIN:"admin"}

def prepared_db(tmp_path):
    csv_path=tmp_path/"tx.csv"; db=tmp_path/"test.db"
    rows=generate_transactions(120,seed=11);write_csv(rows,csv_path)
    create_database(db);load_transactions(csv_path,db);init_phase4(db)
    groups={"anomaly":[{"transaction_id":"TX-TEST","amount":999,"currency":"EUR","merchant_name":"Test"}]}
    n=persist_findings(db,groups,"run-test");record_run(db,"run-test",120,n)
    return db,len(rows)

def test_health_and_summary(tmp_path):
    db,n=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    assert client.get("/health").json()["status"]=="ok"
    summary=client.get("/v1/summary",headers={"X-API-Key":VIEWER}).json()
    assert summary["transaction_count"]==n
    assert summary["findings_by_status"]["new"]==1

def test_findings_review_history(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    item=client.get("/v1/findings",headers={"X-API-Key":VIEWER}).json()["items"][0]
    fid=item["finding_id"]
    response=client.patch(f"/v1/findings/{fid}/review",headers={"X-API-Key":ANALYST},
      json={"status":"under_review","reviewer":"Analyst A","note":"Checking invoice"})
    assert response.status_code==200
    detail=client.get(f"/v1/findings/{fid}",headers={"X-API-Key":VIEWER}).json()
    assert detail["review_status"]=="under_review"
    assert len(detail["events"])==1

def test_invalid_review_status_rejected(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    item=client.get("/v1/findings",headers={"X-API-Key":VIEWER}).json()["items"][0]
    response=client.patch(f"/v1/findings/{item['finding_id']}/review",headers={"X-API-Key":ANALYST},
      json={"status":"fraud","reviewer":"Analyst A"})
    assert response.status_code==422

def test_transaction_pagination_and_filters(tmp_path):
    db,n=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    response=client.get("/v1/transactions?limit=10&offset=5",headers={"X-API-Key":VIEWER})
    assert response.status_code==200
    assert len(response.json()["items"])==10
    assert response.json()["total"]==n

def test_protected_routes_require_key_and_reject_bad_key(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    assert client.get("/v1/summary").status_code==401
    assert client.get("/v1/summary",headers={"X-API-Key":"wrong"}).status_code==401

def test_viewer_cannot_change_reviews(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    item=client.get("/v1/findings",headers={"X-API-Key":VIEWER}).json()["items"][0]
    response=client.patch(f"/v1/findings/{item['finding_id']}/review",
      headers={"X-API-Key":VIEWER},json={"status":"under_review","reviewer":"Analyst A"})
    assert response.status_code==403

def test_security_headers_and_rate_limit(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS,rate_limit=2))
    first=client.get("/health")
    assert first.headers["X-Content-Type-Options"]=="nosniff"
    assert first.headers["Cache-Control"]=="no-store"
    csp=first.headers["Content-Security-Policy"]
    assert "script-src 'self'" in csp
    assert "style-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    client.get("/health")
    assert client.get("/health").status_code==429

def test_unconfigured_auth_fails_closed(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys={}))
    assert client.get("/v1/summary").status_code==503

def test_analytics_overview_requires_viewer_and_returns_series(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    assert client.get("/v1/analytics/overview").status_code==401
    data=client.get("/v1/analytics/overview",headers={"X-API-Key":VIEWER})
    assert data.status_code==200
    assert data.json()["monthly"]
    assert data.json()["departments"]

def test_dashboard_and_assets_are_served(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    page=client.get("/")
    assert page.status_code==200
    assert "Spend overview" in page.text
    assert client.get("/assets/app.js").status_code==200

def test_transaction_search_is_server_side_and_paged(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    response=client.get("/v1/transactions?q=TX-000001&limit=10",headers={"X-API-Key":VIEWER})
    assert response.status_code==200
    assert response.json()["total"] <= 1


def test_dashboard_cross_filters_match_transaction_ledger(tmp_path):
    db,n=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    headers={"X-API-Key":VIEWER}
    all_rows=client.get("/v1/transactions?limit=500",headers=headers).json()["items"]
    selected=all_rows[0]
    month=selected["transaction_date"][:7]
    department=selected["department"]

    ledger=client.get(
      f"/v1/transactions?limit=500&month={month}&department={department}",
      headers=headers
    ).json()
    summary=client.get(
      f"/v1/summary?month={month}&department={department}",headers=headers
    ).json()
    overview=client.get(
      f"/v1/analytics/overview?month={month}&department={department}",headers=headers
    ).json()

    assert ledger["total"] > 0
    assert all(row["transaction_date"].startswith(month) for row in ledger["items"])
    assert all(row["department"] == department for row in ledger["items"])
    assert summary["transaction_count"] == ledger["total"]
    assert summary["total_spend"] == round(sum(row["amount"] for row in ledger["items"]),2)
    assert len(overview["monthly"]) == 1
    assert overview["monthly"][0]["month"] == month
    assert all(row["department"] == department for row in overview["departments"])


def test_dashboard_filters_support_category_and_reject_invalid_month(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    headers={"X-API-Key":VIEWER}
    base=client.get("/v1/transactions?limit=500",headers=headers).json()["items"]
    category=base[0]["category"]
    filtered=client.get(
      f"/v1/transactions?limit=500&category={category}",headers=headers
    ).json()
    summary=client.get(
      f"/v1/summary?category={category}",headers=headers
    ).json()
    assert filtered["total"] > 0
    assert all(row["category"] == category for row in filtered["items"])
    assert summary["transaction_count"] == filtered["total"]
    assert client.get(
      "/v1/transactions?month=not-a-month",headers=headers
    ).status_code == 422


def test_expense_evaluation_is_persisted_and_retrievable(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    body={"expense":{
      "expense_id":"EXP-API-001","employee_id":"EMP-1001","merchant_name":"City Cafe","department":"Sales","amount":"85.00","currency":"EUR",
      "category":"Meals","transaction_date":"2026-05-14",
      "business_purpose":"Project working lunch",
      "receipt":{"provided":True,"readable":True,"receipt_id":"R-API-001","total":"85.00"}
    }}
    denied=client.post("/v1/expenses/evaluate",json=body,headers={"X-API-Key":VIEWER})
    assert denied.status_code==403
    response=client.post("/v1/expenses/evaluate",json=body,headers={"X-API-Key":ANALYST})
    assert response.status_code==200
    saved=response.json()
    assert saved["outcome"]=="APPROVE"
    listing=client.get("/v1/decisions?outcome=APPROVE",headers={"X-API-Key":VIEWER})
    assert listing.status_code==200 and listing.json()["total"]==1
    detail=client.get(f"/v1/decisions/{saved['decision_id']}",headers={"X-API-Key":VIEWER})
    assert detail.status_code==200
    assert detail.json()["evaluation"]["policy_version"]=="1.0.0"


def test_expense_evaluation_missing_evidence_is_not_approved(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    body={"expense":{
      "expense_id":"EXP-API-002","employee_id":"EMP-1002","merchant_name":"City Cafe","department":"Sales","amount":"85.00","currency":"EUR",
      "category":"Meals","transaction_date":"2026-05-14",
      "business_purpose":"Project working lunch","receipt":{"provided":False}
    }}
    response=client.post("/v1/expenses/evaluate",json=body,headers={"X-API-Key":ANALYST})
    assert response.status_code==200
    assert response.json()["outcome"]=="INSUFFICIENT_DATA"


def test_finding_detail_requires_authentication_and_allows_viewer(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    item=client.get("/v1/findings",headers={"X-API-Key":VIEWER}).json()["items"][0]
    url=f"/v1/findings/{item['finding_id']}"
    assert client.get(url).status_code == 401
    assert client.get(url,headers={"X-API-Key":"invalid-key"}).status_code == 401
    assert client.get(url,headers={"X-API-Key":VIEWER}).status_code == 200


def test_backend_flags_matching_prior_expense_for_review(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    headers={"X-API-Key":ANALYST}
    first={"expense_id":"EXP-DUP-001","employee_id":"EMP-77","merchant_name":"City Cafe",
      "department":"Sales","amount":"85.00","currency":"EUR","category":"Meals",
      "transaction_date":"2026-05-14","business_purpose":"Project lunch",
      "receipt":{"provided":True,"readable":True,"receipt_id":"R-DUP-001","total":"85.00"}}
    first_result=client.post("/v1/expenses/evaluate",headers=headers,json={"expense":first})
    assert first_result.status_code == 200
    assert first_result.json()["outcome"] == "APPROVE"

    second=dict(first,expense_id="EXP-DUP-002",receipt=dict(first["receipt"],receipt_id="R-DUP-002"))
    second_result=client.post("/v1/expenses/evaluate",headers=headers,json={"expense":second})
    assert second_result.status_code == 200
    saved=second_result.json()
    assert saved["outcome"] == "REVIEW"
    risk_rule=next(rule for rule in saved["evaluation"]["evaluated_rules"] if rule["rule_id"]=="RISK-001")
    assert risk_rule["status"] == "REVIEW"
    assert risk_rule["evidence"]["match"]["prior_expense_id"] == "EXP-DUP-001"
