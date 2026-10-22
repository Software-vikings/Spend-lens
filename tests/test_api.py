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
