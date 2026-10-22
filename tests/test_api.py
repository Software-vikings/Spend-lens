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


def test_expense_evaluation_idempotency_returns_same_decision(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    headers={"X-API-Key":ANALYST,"Idempotency-Key":"expense-submit-000000000001"}
    expense={"expense_id":"EXP-IDEM-001","employee_id":"EMP-88","merchant_name":"Office Depot","department":"Operations","amount":"40.00","currency":"EUR","category":"Office Supplies","transaction_date":"2026-05-15","business_purpose":"Printer paper","receipt":{"provided":True,"readable":True,"receipt_id":"R-IDEM-001","total":"40.00"}}
    first=client.post("/v1/expenses/evaluate",headers=headers,json={"expense":expense})
    second=client.post("/v1/expenses/evaluate",headers=headers,json={"expense":expense})
    assert first.status_code == second.status_code == 200
    assert first.json()["decision_id"] == second.json()["decision_id"]
    assert client.get("/v1/decisions",headers={"X-API-Key":VIEWER}).json()["total"] == 1

def test_idempotency_key_cannot_be_reused_for_different_expense(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    headers={"X-API-Key":ANALYST,"Idempotency-Key":"expense-submit-000000000002"}
    base={"expense_id":"EXP-IDEM-002","employee_id":"EMP-89","merchant_name":"Office Depot","department":"Operations","amount":"40.00","currency":"EUR","category":"Office Supplies","transaction_date":"2026-05-15","business_purpose":"Printer paper","receipt":{"provided":True,"readable":True,"receipt_id":"R-IDEM-002","total":"40.00"}}
    assert client.post("/v1/expenses/evaluate",headers=headers,json={"expense":base}).status_code == 200
    changed=dict(base,amount="41.00")
    conflict=client.post("/v1/expenses/evaluate",headers=headers,json={"expense":changed})
    assert conflict.status_code == 409


def test_transaction_detail_returns_only_exactly_linked_findings(tmp_path):
    import sqlite3
    db,_=prepared_db(tmp_path)
    with sqlite3.connect(db) as conn:
        transaction_id=conn.execute(
            "SELECT transaction_id FROM transactions ORDER BY transaction_id LIMIT 1"
        ).fetchone()[0]
    persist_findings(db, {"anomaly":[
        {"transaction_id":transaction_id,"amount":250.0,"currency":"EUR","merchant_name":"Linked merchant"}
    ]}, "run-linked")
    client=TestClient(create_app(db,api_keys=KEYS))
    headers={"X-API-Key":VIEWER}
    assert client.get(f"/v1/transactions/{transaction_id}").status_code == 401
    response=client.get(f"/v1/transactions/{transaction_id}",headers=headers)
    assert response.status_code == 200
    payload=response.json()
    assert payload["transaction"]["transaction_id"] == transaction_id
    assert len(payload["related_findings"]) == 1
    assert payload["related_findings"][0]["finding_type"] == "anomaly"
    assert client.get("/v1/transactions/DOES-NOT-EXIST",headers=headers).status_code == 404


def test_expense_claim_persists_submission_decision_and_receipt_metadata(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    headers={"X-API-Key":ANALYST}
    expense={"expense_id":"CLAIM-001","employee_id":"EMP-501","merchant_name":"Rail Services",
      "department":"Operations","amount":"72.50","currency":"EUR","category":"Travel",
      "transaction_date":"2026-05-18","business_purpose":"Client site visit",
      "receipt":{"provided":True,"readable":True,"receipt_id":"RECEIPT-501","total":"72.50"}}
    submitted=client.post("/v1/expenses/evaluate",headers=headers,json={"expense":expense})
    assert submitted.status_code == 200
    decision=submitted.json()
    claim=client.get("/v1/claims/CLAIM-001",headers={"X-API-Key":VIEWER})
    assert claim.status_code == 200
    payload=claim.json()
    assert payload["claim_id"] == "CLAIM-001"
    assert payload["current_status"] == decision["outcome"]
    assert payload["latest_decision_id"] == decision["decision_id"]
    assert len(payload["submissions"]) == 1
    assert payload["submissions"][0]["decision_id"] == decision["decision_id"]
    assert len(payload["evidence"]) == 1
    assert payload["evidence"][0]["evidence_type"] == "RECEIPT"
    assert payload["evidence"][0]["evidence_ref"] == "RECEIPT-501"
    assert payload["evidence"][0]["evidence_status"] == "METADATA_SUBMITTED"
    assert payload["evidence"][0]["source"] == "SUBMITTED_METADATA"
    assert client.get("/v1/claims/CLAIM-001").status_code == 401
    assert client.get("/v1/claims/UNKNOWN",headers={"X-API-Key":VIEWER}).status_code == 404


def test_claim_resubmission_preserves_prior_decision_history(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    headers={"X-API-Key":ANALYST}
    expense={"expense_id":"CLAIM-HISTORY-001","employee_id":"EMP-502","merchant_name":"Rail Services",
      "department":"Operations","amount":"72.50","currency":"EUR","category":"Travel",
      "transaction_date":"2026-05-18","business_purpose":"Client site visit",
      "receipt":{"provided":True,"readable":True,"receipt_id":"RECEIPT-502","total":"72.50"}}
    first=client.post("/v1/expenses/evaluate",headers=headers,json={"expense":expense})
    revised=dict(expense,amount="75.00",receipt=dict(expense["receipt"],receipt_id="RECEIPT-503",total="75.00"))
    second=client.post("/v1/expenses/evaluate",headers=headers,json={"expense":revised})
    assert first.status_code == second.status_code == 200
    assert first.json()["decision_id"] != second.json()["decision_id"]
    claim=client.get("/v1/claims/CLAIM-HISTORY-001",headers={"X-API-Key":VIEWER}).json()
    assert len(claim["submissions"]) == 2
    assert len({item["decision_id"] for item in claim["submissions"]}) == 2
    assert claim["latest_decision_id"] == second.json()["decision_id"]
    assert claim["amount"] == "75.00"
    assert len(claim["evidence"]) == 2


def test_claim_register_is_paginated_and_filterable(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    headers={"X-API-Key":ANALYST}
    for index in range(3):
        expense={"expense_id":f"CLAIM-LIST-{index}","employee_id":"EMP-LIST",
          "merchant_name":f"Office Depot {index}","department":"Operations","amount":"25.00",
          "currency":"EUR","category":"Office Supplies","transaction_date":"2026-05-19",
          "business_purpose":"Stationery purchase",
          "receipt":{"provided":True,"readable":True,"receipt_id":f"RCPT-{index}","total":"25.00"}}
        assert client.post("/v1/expenses/evaluate",headers=headers,json={"expense":expense}).status_code == 200
    page=client.get("/v1/claims?limit=2&offset=1",headers={"X-API-Key":VIEWER})
    assert page.status_code == 200
    assert page.json()["total"] == 3
    assert len(page.json()["items"]) == 2
    assert client.get("/v1/claims?status=APPROVE",headers={"X-API-Key":VIEWER}).json()["total"] == 3
    assert client.get("/v1/claims").status_code == 401


def test_policy_versions_are_immutable_admin_managed_and_used_by_evaluator(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    viewer={"X-API-Key":VIEWER};admin={"X-API-Key":ADMIN}
    initial=client.get("/v1/policies",headers=viewer)
    assert initial.status_code==200
    active=next(x for x in initial.json()["items"] if x["is_active"])
    original=client.get(f"/v1/policies/{active['policy_id']}/{active['version']}",headers=viewer).json()
    revised=dict(original,version="1.0.1",name="Synthetic demonstration policy revised")
    created=client.post("/v1/policies",headers=admin,json=revised)
    assert created.status_code==201
    assert client.post("/v1/policies",headers=admin,json=revised).status_code==409
    assert client.post("/v1/policies",headers=viewer,json=dict(revised,version="1.0.2")).status_code==403
    invalid=dict(revised,version="1.0.2",blocked_categories=revised["eligible_categories"])
    assert client.post("/v1/policies",headers=admin,json=invalid).status_code==422
    activated=client.post(f"/v1/policies/{active['policy_id']}/1.0.1/activate",headers=admin)
    assert activated.status_code==200
    listed=client.get("/v1/policies",headers=viewer).json()["items"]
    assert next(x for x in listed if x["version"]=="1.0.1")["is_active"]
    expense={"expense_id":"POLICY-VERSION-001","employee_id":"EMP-POL","merchant_name":"City Cafe",
      "department":"Sales","amount":"85.00","currency":"EUR","category":"Meals",
      "transaction_date":"2026-05-14","business_purpose":"Client meeting",
      "receipt":{"provided":True,"readable":True,"receipt_id":"R-POL-1","total":"85.00"}}
    decision=client.post("/v1/expenses/evaluate",headers={"X-API-Key":ANALYST},json={"expense":expense})
    assert decision.status_code==200
    assert decision.json()["policy_version"]=="1.0.1"
    assert decision.json()["policy_id"]==active["policy_id"]


def test_policy_activation_requires_admin_and_unknown_version_is_404(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    assert client.post("/v1/policies/UNKNOWN/9.9/activate",headers={"X-API-Key":ANALYST}).status_code==403
    assert client.post("/v1/policies/UNKNOWN/9.9/activate",headers={"X-API-Key":ADMIN}).status_code==404


def test_claim_resolution_preserves_automated_decision_and_audits_actions(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    expense={"expense_id":"CLAIM-RESOLVE-001","employee_id":"EMP-RESOLVE",
      "merchant_name":"City Cafe","department":"Sales","amount":"85.00","currency":"EUR",
      "category":"Meals","transaction_date":"2026-05-20","business_purpose":"Client lunch",
      "receipt":{"provided":False}}
    submitted=client.post("/v1/expenses/evaluate",headers={"X-API-Key":ANALYST},json={"expense":expense})
    assert submitted.status_code==200
    original=submitted.json()
    assert original["outcome"]=="INSUFFICIENT_DATA"
    url="/v1/claims/CLAIM-RESOLVE-001/resolution"
    body={"action":"REQUEST_INFORMATION","reviewer":"Analyst A",
          "reason":"Receipt is required for this category","evidence_note":"Requested original receipt"}
    assert client.post(url,headers={"X-API-Key":VIEWER},json=body).status_code==403
    requested=client.post(url,headers={"X-API-Key":ANALYST},json=body)
    assert requested.status_code==200
    approved=client.post(url,headers={"X-API-Key":ADMIN},json={
      "action":"APPROVE","reviewer":"Finance Lead","reason":"Receipt reviewed outside this prototype",
      "evidence_note":"Evidence review is self-reported; no file is stored."})
    assert approved.status_code==200
    detail=client.get("/v1/claims/CLAIM-RESOLVE-001",headers={"X-API-Key":VIEWER}).json()
    assert detail["current_status"]=="INSUFFICIENT_DATA"
    assert detail["resolution_status"]=="HUMAN_APPROVED"
    assert len(detail["resolution_history"])==2
    decision=client.get(f"/v1/decisions/{original['decision_id']}",headers={"X-API-Key":VIEWER}).json()
    assert decision["outcome"]=="INSUFFICIENT_DATA"
    assert decision["evaluation"]["outcome"]=="INSUFFICIENT_DATA"


def test_claim_resolution_requires_reason_and_only_handles_exception_outcomes(tmp_path):
    db,_=prepared_db(tmp_path);client=TestClient(create_app(db,api_keys=KEYS))
    headers={"X-API-Key":ANALYST}
    approved_expense={"expense_id":"CLAIM-RESOLVE-002","employee_id":"EMP-OK",
      "merchant_name":"Office Depot","department":"Operations","amount":"25.00",
      "currency":"EUR","category":"Office Supplies","transaction_date":"2026-05-21",
      "business_purpose":"Stationery","receipt":{"provided":True,"readable":True,
      "receipt_id":"RCPT-OK","total":"25.00"}}
    result=client.post("/v1/expenses/evaluate",headers=headers,json={"expense":approved_expense})
    assert result.status_code==200 and result.json()["outcome"]=="APPROVE"
    url="/v1/claims/CLAIM-RESOLVE-002/resolution"
    assert client.post(url,headers=headers,json={"action":"REJECT","reviewer":"Analyst A","reason":" "}).status_code==422
    assert client.post(url,headers=headers,json={"action":"REJECT","reviewer":"Analyst A","reason":"Not compliant"}).status_code==409
    assert client.post("/v1/claims/DOES-NOT-EXIST/resolution",headers=headers,
      json={"action":"REJECT","reviewer":"Analyst A","reason":"Not compliant"}).status_code==404
