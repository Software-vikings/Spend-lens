"""Hardened SpendLens API with API-key roles and basic request throttling.

This is a single-process portfolio deployment baseline, not a substitute for
an enterprise identity provider, distributed rate limiter or security review.
"""
from __future__ import annotations
import json, os, secrets, time, logging, uuid
from collections import defaultdict, deque
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, Query, Header, Depends, Request
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field, field_validator
from .phase4 import connect, init_phase4
from .decision_engine import evaluate_expense
from .decision_store import init_decisions, save_decision, list_decisions, get_decision, get_claim, find_potential_duplicate

logger = logging.getLogger("spendlens.api")
ROOT = Path(__file__).resolve().parents[2]
DB_PATH = Path(os.getenv("SPENDLENS_DB", ROOT/"data"/"spendlens.db"))
ReviewStatus = Literal["new","under_review","confirmed","dismissed","resolved"]
ROLE_LEVEL = {"viewer":1,"analyst":2,"admin":3}

class ExpenseEvaluationRequest(BaseModel):
    expense: dict


class ReviewUpdate(BaseModel):
    status: ReviewStatus
    reviewer: str = Field(min_length=2, max_length=100)
    note: str = Field(default="", max_length=2000)

    @field_validator("reviewer")
    @classmethod
    def reviewer_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("reviewer cannot be blank")
        return value.strip()

def parse_api_keys(raw: str | None = None) -> dict[str,str]:
    """Parse comma-separated key:role pairs. Keys are never returned by API."""
    raw = os.getenv("SPENDLENS_API_KEYS", "") if raw is None else raw
    result={}
    for entry in raw.split(","):
        if not entry.strip(): continue
        if ":" not in entry: raise ValueError("Each API key entry must be key:role")
        key, role=entry.rsplit(":",1)
        key,role=key.strip(),role.strip().lower()
        if len(key)<24: raise ValueError("API keys must contain at least 24 characters")
        if role not in ROLE_LEVEL: raise ValueError(f"Unsupported API role: {role}")
        result[key]=role
    return result

def create_app(db_path: str | Path = DB_PATH, api_keys: dict[str,str] | None = None,
               rate_limit: int = 120, rate_window_seconds: int = 60) -> FastAPI:
    db_path=Path(db_path)
    configured=parse_api_keys() if api_keys is None else dict(api_keys)
    app=FastAPI(title="SpendLens API",version="1.0.0",
      description="Authenticated spending signals for human review. Findings are not fraud determinations.")
    app.state.db_path=db_path
    app.state.api_keys=configured
    app.state.rate_limit=rate_limit
    app.state.rate_window_seconds=rate_window_seconds
    request_times: dict[str,deque]=defaultdict(deque)

    @app.middleware("http")
    async def security_middleware(request: Request, call_next):
        client_ip=request.client.host if request.client else "unknown"
        now=time.monotonic()
        bucket=request_times[client_ip]
        while bucket and now-bucket[0]>=rate_window_seconds: bucket.popleft()
        request_id=str(uuid.uuid4())
        started=time.perf_counter()
        if len(bucket)>=rate_limit:
            response=JSONResponse(status_code=429,content={"detail":"Rate limit exceeded"})
        else:
            bucket.append(now)
            response=await call_next(request)
        response.headers["X-Request-ID"]=request_id
        logger.info("request_complete request_id=%s method=%s path=%s status=%s duration_ms=%.2f",
                    request_id,request.method,request.url.path,response.status_code,
                    (time.perf_counter()-started)*1000)
        response.headers["X-Content-Type-Options"]="nosniff"
        response.headers["X-Frame-Options"]="DENY"
        response.headers["Referrer-Policy"]="no-referrer"
        response.headers["Cache-Control"]="no-store"
        response.headers["Content-Security-Policy"]="default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        return response

    def require_role(minimum: str):
        def dependency(x_api_key: str | None = Header(default=None,alias="X-API-Key")):
            if not configured:
                raise HTTPException(503,"API authentication is not configured")
            if not x_api_key:
                raise HTTPException(401,"API key required",headers={"WWW-Authenticate":"ApiKey"})
            role=next((r for k,r in configured.items() if secrets.compare_digest(k,x_api_key)),None)
            if role is None:
                raise HTTPException(401,"Invalid API key")
            if ROLE_LEVEL.get(role,0)<ROLE_LEVEL[minimum]:
                raise HTTPException(403,"Insufficient role")
            return role
        return dependency

    def db():
        if not db_path.exists():
            raise HTTPException(503,"SpendLens database not found. Run the pipeline first.")
        init_phase4(db_path)
        init_decisions(db_path)
        return connect(db_path)

    def transaction_filters(month: str | None, department: str | None,
                            category: str | None) -> tuple[list[str], list[str]]:
        """Build parameterised filters shared by dashboard and ledger endpoints."""
        clauses: list[str] = []
        params: list[str] = []
        if month:
            clauses.append("substr(transaction_date,1,7)=?")
            params.append(month)
        if department:
            clauses.append("department=?")
            params.append(department)
        if category:
            clauses.append("category=?")
            params.append(category)
        return clauses, params

    def where_clause(clauses: list[str]) -> str:
        return (" WHERE " + " AND ".join(clauses)) if clauses else ""

    frontend_dir = ROOT / "frontend"

    @app.get("/", include_in_schema=False)
    def dashboard():
        index = frontend_dir / "index.html"
        if not index.exists():
            raise HTTPException(404, "SpendLens dashboard assets not installed")
        return FileResponse(index)

    @app.get("/health")
    def health():
        if not db_path.exists(): return {"status":"degraded","service":"spendlens-api"}
        with connect(db_path) as c: c.execute("SELECT 1")
        return {"status":"ok","service":"spendlens-api"}

    @app.get("/v1/summary")
    def summary(month:str|None=Query(None,pattern=r"^\d{4}-\d{2}$"),
                department:str|None=None,category:str|None=None,
                _:str=Depends(require_role("viewer"))):
        clauses,params=transaction_filters(month,department,category)
        where=where_clause(clauses)
        with db() as c:
            tx=c.execute("SELECT COUNT(*) n,COALESCE(SUM(amount),0) spend FROM transactions"+where,params).fetchone()
            # Findings are deliberately global until findings carry transaction-level
            # dimension keys. Do not imply that these counts are cross-filtered.
            findings=c.execute("SELECT review_status,COUNT(*) n FROM findings GROUP BY review_status").fetchall()
            types=c.execute("SELECT finding_type,COUNT(*) n FROM findings GROUP BY finding_type").fetchall()
        return {"transaction_count":tx["n"],"total_spend":round(tx["spend"],2),
          "findings_by_status":{r["review_status"]:r["n"] for r in findings},
          "findings_by_type":{r["finding_type"]:r["n"] for r in types},
          "currency":"EUR","data_note":"Synthetic demonstration data.",
          "active_filters":{"month":month,"department":department,"category":category}}

    @app.get("/v1/analytics/overview")
    def analytics_overview(month:str|None=Query(None,pattern=r"^\d{4}-\d{2}$"),
                           department:str|None=None,category:str|None=None,
                           _:str=Depends(require_role("viewer"))):
        clauses,params=transaction_filters(month,department,category)
        where=where_clause(clauses)
        with db() as c:
            monthly=c.execute(f"""SELECT substr(transaction_date,1,7) month,
                ROUND(SUM(amount),2) spend,COUNT(*) transaction_count
                FROM transactions{where} GROUP BY 1 ORDER BY 1""",params).fetchall()
            departments=c.execute(f"""SELECT department,ROUND(SUM(amount),2) spend,
                COUNT(*) transaction_count FROM transactions{where} GROUP BY department
                ORDER BY spend DESC""",params).fetchall()
            categories=c.execute(f"""SELECT category,ROUND(SUM(amount),2) spend,
                COUNT(*) transaction_count FROM transactions{where} GROUP BY category
                ORDER BY spend DESC LIMIT 8""",params).fetchall()
        return {"monthly":[dict(r) for r in monthly],
                "departments":[dict(r) for r in departments],
                "categories":[dict(r) for r in categories],"currency":"EUR",
                "active_filters":{"month":month,"department":department,"category":category}}

    @app.get("/v1/transactions")
    def transactions(limit:int=Query(100,ge=1,le=500),offset:int=Query(0,ge=0),
        month:str|None=Query(None,pattern=r"^\d{4}-\d{2}$"),
        department:str|None=None,category:str|None=None,q:str|None=Query(None,max_length=120),
        _:str=Depends(require_role("viewer"))):
        clauses,params=transaction_filters(month,department,category)
        if q and q.strip():
            clauses.append("(transaction_id LIKE ? OR merchant_name LIKE ? OR employee_id LIKE ? OR department LIKE ? OR category LIKE ?)")
            term=f"%{q.strip()}%";params.extend([term]*5)
        where=where_clause(clauses)
        with db() as c:
            total=c.execute("SELECT COUNT(*) n FROM transactions"+where,params).fetchone()["n"]
            rows=c.execute("SELECT transaction_id,transaction_date,employee_id,department,merchant_id,merchant_name,category,amount,currency,payment_method FROM transactions"+where+" ORDER BY transaction_date DESC,transaction_id LIMIT ? OFFSET ?",params+[limit,offset]).fetchall()
        return {"total":total,"limit":limit,"offset":offset,"items":[dict(r) for r in rows],
                "active_filters":{"month":month,"department":department,"category":category}}

    @app.get("/v1/transactions/{transaction_id}")
    def transaction_detail(transaction_id: str, _:str=Depends(require_role("viewer"))):
        """Return one ledger transaction and only findings linked by exact transaction ID."""
        with db() as conn:
            transaction = conn.execute(
                "SELECT transaction_id,transaction_date,employee_id,department,merchant_id,merchant_name,category,amount,currency,payment_method "
                "FROM transactions WHERE transaction_id=?", (transaction_id,)
            ).fetchone()
            if transaction is None:
                raise HTTPException(404, "Transaction not found")
            linked = conn.execute(
                "SELECT finding_id,finding_type,title,severity,amount,currency,review_status,last_seen_at "
                "FROM findings WHERE transaction_id=? ORDER BY last_seen_at DESC",
                (transaction_id,)
            ).fetchall()
        return {"transaction": dict(transaction), "related_findings": [dict(row) for row in linked],
                "relationship_note": "Findings are linked only when their source record contains this exact transaction ID. Expense claims and decisions are separate records until an explicit source relationship is supplied."}

    @app.post("/v1/expenses/evaluate")
    def evaluate_expense_route(body: ExpenseEvaluationRequest,
                               idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
                               _:str=Depends(require_role("analyst"))):
        if not db_path.exists():
            raise HTTPException(503, "SpendLens database not found. Run the pipeline first.")
        init_decisions(db_path)
        policy_path = ROOT / "policies" / "demo_policy.json"
        if not policy_path.exists():
            raise HTTPException(503, "Configured demo policy is missing")
        try:
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
            expense = dict(body.expense)
            duplicate_match = find_potential_duplicate(db_path, expense)
            if duplicate_match:
                # Similarity is a review signal only; never an automatic rejection.
                expense["duplicate_suspected"] = True
                expense["duplicate_match"] = duplicate_match
            evaluation = evaluate_expense(expense, policy)
            return save_decision(db_path, expense, evaluation, idempotency_key)
        except ValueError as exc:
            status = 409 if "Idempotency key" in str(exc) else 422
            raise HTTPException(status, str(exc)) from exc

    @app.get("/v1/claims/{claim_id}")
    def claim_detail(claim_id:str,_:str=Depends(require_role("viewer"))):
        db()
        item=get_claim(db_path,claim_id)
        if item is None:
            raise HTTPException(404,"Expense claim not found")
        return item

    @app.get("/v1/decisions")
    def decisions(outcome:Literal["APPROVE","REJECT","REVIEW","INSUFFICIENT_DATA"]|None=None,
                  limit:int=Query(100,ge=1,le=500),offset:int=Query(0,ge=0),
                  _:str=Depends(require_role("viewer"))):
        db()
        return list_decisions(db_path, outcome, limit, offset)

    @app.get("/v1/decisions/{decision_id}")
    def decision_detail(decision_id:str,_:str=Depends(require_role("viewer"))):
        db()
        item=get_decision(db_path,decision_id)
        if item is None:
            raise HTTPException(404,"Decision not found")
        return item

    @app.get("/v1/findings")
    def findings(status:ReviewStatus|None=None,finding_type:str|None=None,
        limit:int=Query(100,ge=1,le=500),offset:int=Query(0,ge=0),
        _:str=Depends(require_role("viewer"))):
        clauses=[];params=[]
        if status: clauses.append("review_status=?");params.append(status)
        if finding_type: clauses.append("finding_type=?");params.append(finding_type)
        where=(" WHERE "+" AND ".join(clauses)) if clauses else ""
        with db() as c:
            total=c.execute("SELECT COUNT(*) n FROM findings"+where,params).fetchone()["n"]
            rows=c.execute("SELECT * FROM findings"+where+" ORDER BY last_seen_at DESC LIMIT ? OFFSET ?",params+[limit,offset]).fetchall()
        result=[]
        for r in rows:
            item=dict(r);item["details"]=json.loads(item.pop("source_payload"));result.append(item)
        return {"total":total,"limit":limit,"offset":offset,"items":result}

    @app.get("/v1/findings/{finding_id}")
    def finding_detail(finding_id:str,_:str=Depends(require_role("viewer"))):
        with db() as c:
            r=c.execute("SELECT * FROM findings WHERE finding_id=?",(finding_id,)).fetchone()
            if not r: raise HTTPException(404,"Finding not found")
            events=c.execute("SELECT event_at,old_status,new_status,reviewer,note FROM finding_events WHERE finding_id=? ORDER BY event_id",(finding_id,)).fetchall()
        item=dict(r);item["details"]=json.loads(item.pop("source_payload"));item["events"]=[dict(x) for x in events]
        return item

    @app.patch("/v1/findings/{finding_id}/review")
    def update_review(finding_id:str,body:ReviewUpdate,_:str=Depends(require_role("analyst"))):
        with db() as c:
            old=c.execute("SELECT review_status FROM findings WHERE finding_id=?",(finding_id,)).fetchone()
            if not old: raise HTTPException(404,"Finding not found")
            if old["review_status"] in ("resolved","dismissed") and body.status=="under_review":
                raise HTTPException(409,"Reopen by setting status to new before review.")
            from datetime import datetime,timezone
            now=datetime.now(timezone.utc).isoformat()
            c.execute("UPDATE findings SET review_status=?,reviewer=?,review_note=? WHERE finding_id=?",
              (body.status,body.reviewer,body.note.strip(),finding_id))
            c.execute("""INSERT INTO finding_events(finding_id,event_at,old_status,new_status,reviewer,note)
              VALUES(?,?,?,?,?,?)""",(finding_id,now,old["review_status"],body.status,body.reviewer,body.note.strip()))
        return {"finding_id":finding_id,"previous_status":old["review_status"],
          "review_status":body.status,"reviewer":body.reviewer,"updated_at":now}
    from fastapi.staticfiles import StaticFiles
    if frontend_dir.exists():
        app.mount("/assets", StaticFiles(directory=frontend_dir), name="frontend-assets")
    return app

app=create_app()
