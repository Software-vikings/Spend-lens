"""Persistence and audit history for deterministic expense decisions."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from .phase4 import connect


def init_decisions(db_path: str | Path) -> None:
    with connect(db_path) as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS expense_decisions (
          decision_id TEXT PRIMARY KEY,
          expense_id TEXT NOT NULL,
          outcome TEXT NOT NULL CHECK(outcome IN ('APPROVE','REJECT','REVIEW','INSUFFICIENT_DATA')),
          policy_id TEXT NOT NULL,
          policy_version TEXT NOT NULL,
          engine_version TEXT NOT NULL,
          created_at TEXT NOT NULL,
          expense_payload TEXT NOT NULL,
          evaluation_payload TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_expense_decisions_outcome ON expense_decisions(outcome);
        CREATE INDEX IF NOT EXISTS idx_expense_decisions_expense ON expense_decisions(expense_id, created_at);
        """)
        # Serialize schema inspection and ALTER TABLE operations. API requests may
        # initialise the store concurrently; without a write lock two workers can
        # both observe a missing column and race to add it.
        conn.execute("BEGIN IMMEDIATE")
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(expense_decisions)")}
        if "idempotency_key" not in columns:
            conn.execute("ALTER TABLE expense_decisions ADD COLUMN idempotency_key TEXT")
        if "request_hash" not in columns:
            conn.execute("ALTER TABLE expense_decisions ADD COLUMN request_hash TEXT")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_expense_decisions_idempotency ON expense_decisions(idempotency_key) WHERE idempotency_key IS NOT NULL")
        conn.commit()
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS expense_claims (
          claim_id TEXT PRIMARY KEY,
          employee_id TEXT,
          merchant_name TEXT,
          department TEXT,
          amount TEXT,
          currency TEXT,
          category TEXT,
          transaction_date TEXT,
          business_purpose TEXT,
          current_status TEXT NOT NULL DEFAULT 'SUBMITTED',
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          latest_decision_id TEXT,
          current_payload TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_expense_claims_employee ON expense_claims(employee_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_expense_claims_status ON expense_claims(current_status);
        CREATE TABLE IF NOT EXISTS claim_submissions (
          submission_id TEXT PRIMARY KEY,
          claim_id TEXT NOT NULL REFERENCES expense_claims(claim_id),
          decision_id TEXT NOT NULL UNIQUE REFERENCES expense_decisions(decision_id),
          submitted_at TEXT NOT NULL,
          payload TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_claim_submissions_claim ON claim_submissions(claim_id, submitted_at);
        CREATE TABLE IF NOT EXISTS claim_evidence (
          evidence_id TEXT PRIMARY KEY,
          claim_id TEXT NOT NULL REFERENCES expense_claims(claim_id),
          decision_id TEXT NOT NULL REFERENCES expense_decisions(decision_id),
          evidence_type TEXT NOT NULL,
          evidence_ref TEXT,
          evidence_status TEXT NOT NULL,
          source TEXT NOT NULL,
          metadata TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_claim_evidence_claim ON claim_evidence(claim_id, created_at);
        CREATE TABLE IF NOT EXISTS claim_resolution_events (
          resolution_id TEXT PRIMARY KEY,
          claim_id TEXT NOT NULL REFERENCES expense_claims(claim_id),
          action TEXT NOT NULL CHECK(action IN ('REQUEST_INFORMATION','APPROVE','REJECT')),
          previous_status TEXT NOT NULL,
          new_status TEXT NOT NULL,
          reviewer TEXT NOT NULL,
          reason TEXT NOT NULL,
          evidence_note TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_claim_resolution_claim
          ON claim_resolution_events(claim_id,created_at);
        CREATE TABLE IF NOT EXISTS audit_events (
          event_id TEXT PRIMARY KEY,
          event_type TEXT NOT NULL,
          entity_type TEXT NOT NULL,
          entity_id TEXT NOT NULL,
          actor TEXT NOT NULL,
          details TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_audit_events_created ON audit_events(created_at);
        CREATE INDEX IF NOT EXISTS idx_audit_events_entity ON audit_events(entity_type,entity_id,created_at);
        CREATE TABLE IF NOT EXISTS claim_assignment_events (
          assignment_id TEXT PRIMARY KEY,
          claim_id TEXT NOT NULL REFERENCES expense_claims(claim_id),
          assignee TEXT NOT NULL,
          priority TEXT NOT NULL CHECK(priority IN ('LOW','NORMAL','HIGH','URGENT')),
          sla_hours INTEGER NOT NULL CHECK(sla_hours BETWEEN 1 AND 720),
          due_at TEXT NOT NULL,
          assigned_by TEXT NOT NULL,
          note TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_claim_assignment_claim
          ON claim_assignment_events(claim_id,created_at);

        """)



def find_potential_duplicate(db_path: str | Path, expense: dict) -> dict | None:
    """Find an exact high-similarity prior claim candidate; never infer fraud.

    A match is based on employee, merchant, amount, currency and transaction
    date. It is a conservative review signal and can include legitimate repeats.
    """
    identity = ("employee_id", "merchant_name", "amount", "currency", "transaction_date")
    if any(expense.get(key) in (None, "") for key in identity):
        return None
    with connect(db_path) as conn:
        rows = conn.execute(
            "SELECT expense_id, expense_payload FROM expense_decisions "
            "ORDER BY created_at DESC LIMIT 500"
        ).fetchall()
    for row in rows:
        if row["expense_id"] == str(expense.get("expense_id", "")):
            continue
        try:
            prior = json.loads(row["expense_payload"])
        except (TypeError, json.JSONDecodeError):
            continue
        if all(str(prior.get(key, "")).strip().casefold() ==
               str(expense.get(key, "")).strip().casefold() for key in identity):
            return {"prior_expense_id": row["expense_id"],
                    "match_fields": list(identity)}
    return None


def save_decision(db_path: str | Path, expense: dict, evaluation: dict,
                  idempotency_key: str | None = None) -> dict:
    request_hash = hashlib.sha256(json.dumps({"expense": expense, "evaluation": evaluation}, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    if idempotency_key:
        with connect(db_path) as conn:
            existing = conn.execute("SELECT decision_id,request_hash FROM expense_decisions WHERE idempotency_key=?", (idempotency_key,)).fetchone()
        if existing:
            if existing["request_hash"] != request_hash:
                raise ValueError("Idempotency key was already used for a different expense request")
            return get_decision(db_path, existing["decision_id"])
    now = datetime.now(timezone.utc).isoformat()
    decision = {
        "decision_id": str(uuid.uuid4()),
        "expense_id": str(evaluation["expense_id"]),
        "outcome": evaluation["outcome"],
        "policy_id": evaluation["policy_id"],
        "policy_version": evaluation["policy_version"],
        "engine_version": evaluation["engine_version"],
        "created_at": now,
        "expense": expense,
        "evaluation": evaluation,
    }
    claim_id = decision["expense_id"]
    with connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        if idempotency_key:
            existing = conn.execute("SELECT decision_id,request_hash FROM expense_decisions WHERE idempotency_key=?", (idempotency_key,)).fetchone()
            if existing:
                if existing["request_hash"] != request_hash:
                    raise ValueError("Idempotency key was already used for a different expense request")
                conn.rollback()
                return get_decision(db_path, existing["decision_id"])
        conn.execute("""
          INSERT INTO expense_decisions
          (decision_id,expense_id,outcome,policy_id,policy_version,engine_version,
           created_at,expense_payload,evaluation_payload,idempotency_key,request_hash)
          VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """, (decision["decision_id"], decision["expense_id"], decision["outcome"],
              decision["policy_id"], decision["policy_version"], decision["engine_version"],
              now, json.dumps(expense, sort_keys=True), json.dumps(evaluation, sort_keys=True),
              idempotency_key, request_hash))
        conn.execute("""
          INSERT INTO expense_claims
          (claim_id,employee_id,merchant_name,department,amount,currency,category,
           transaction_date,business_purpose,current_status,created_at,updated_at,
           latest_decision_id,current_payload)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
          ON CONFLICT(claim_id) DO UPDATE SET
            employee_id=excluded.employee_id, merchant_name=excluded.merchant_name,
            department=excluded.department, amount=excluded.amount, currency=excluded.currency,
            category=excluded.category, transaction_date=excluded.transaction_date,
            business_purpose=excluded.business_purpose,current_status=excluded.current_status,
            updated_at=excluded.updated_at,latest_decision_id=excluded.latest_decision_id,
            current_payload=excluded.current_payload
        """, (claim_id, expense.get("employee_id"), expense.get("merchant_name"),
              expense.get("department"), str(expense.get("amount")) if expense.get("amount") is not None else None,
              expense.get("currency"), expense.get("category"), expense.get("transaction_date"),
              expense.get("business_purpose"), decision["outcome"], now, now,
              decision["decision_id"], json.dumps(expense, sort_keys=True)))
        conn.execute("""
          INSERT INTO claim_submissions(submission_id,claim_id,decision_id,submitted_at,payload)
          VALUES(?,?,?,?,?)
        """, (str(uuid.uuid4()), claim_id, decision["decision_id"], now, json.dumps(expense, sort_keys=True)))
        receipt = expense.get("receipt") or {}
        if receipt:
            conn.execute("""
              INSERT INTO claim_evidence
              (evidence_id,claim_id,decision_id,evidence_type,evidence_ref,evidence_status,
               source,metadata,created_at)
              VALUES(?,?,?,?,?,?,?,?,?)
            """, (str(uuid.uuid4()), claim_id, decision["decision_id"], "RECEIPT",
                  receipt.get("receipt_id"), "METADATA_SUBMITTED" if receipt.get("provided") else "NOT_PROVIDED",
                  "SUBMITTED_METADATA", json.dumps(receipt, sort_keys=True), now))
    return decision


def list_decisions(db_path: str | Path, outcome: str | None = None,
                   limit: int = 100, offset: int = 0) -> dict:
    clauses, params = [], []
    if outcome:
        clauses.append("outcome=?")
        params.append(outcome)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) n FROM expense_decisions" + where, params).fetchone()["n"]
        rows = conn.execute(
            "SELECT decision_id,expense_id,outcome,policy_id,policy_version,engine_version,created_at "
            "FROM expense_decisions" + where + " ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset]).fetchall()
    return {"total": total, "limit": limit, "offset": offset,
            "items": [dict(row) for row in rows]}


def get_decision(db_path: str | Path, decision_id: str) -> dict | None:
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM expense_decisions WHERE decision_id=?", (decision_id,)).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["expense"] = json.loads(item.pop("expense_payload"))
    item["evaluation"] = json.loads(item.pop("evaluation_payload"))
    return item



def list_claims(db_path: str | Path, status: str | None = None,
                limit: int = 100, offset: int = 0) -> dict:
    clauses, params = [], []
    if status:
        clauses.append("current_status=?")
        params.append(status)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) n FROM expense_claims" + where, params).fetchone()["n"]
        rows = conn.execute(
            "SELECT claim_id,employee_id,merchant_name,department,amount,currency,category,"
            "transaction_date,current_status,created_at,updated_at,latest_decision_id "
            "FROM expense_claims" + where + " ORDER BY updated_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset]
        ).fetchall()
    return {"total": total, "limit": limit, "offset": offset, "items": [dict(row) for row in rows]}


def get_claim(db_path: str | Path, claim_id: str) -> dict | None:
    with connect(db_path) as conn:
        claim = conn.execute("SELECT * FROM expense_claims WHERE claim_id=?", (claim_id,)).fetchone()
        if claim is None:
            return None
        submissions = conn.execute(
            "SELECT submission_id,decision_id,submitted_at,payload FROM claim_submissions WHERE claim_id=? ORDER BY submitted_at DESC",
            (claim_id,)
        ).fetchall()
        evidence = conn.execute(
            "SELECT evidence_id,decision_id,evidence_type,evidence_ref,evidence_status,source,metadata,created_at FROM claim_evidence WHERE claim_id=? ORDER BY created_at DESC",
            (claim_id,)
        ).fetchall()
        resolutions = conn.execute(
            "SELECT resolution_id,action,previous_status,new_status,reviewer,reason,evidence_note,created_at FROM claim_resolution_events WHERE claim_id=? ORDER BY created_at,rowid",
            (claim_id,)
        ).fetchall()
        assignments = conn.execute(
            "SELECT assignment_id,assignee,priority,sla_hours,due_at,assigned_by,note,created_at FROM claim_assignment_events WHERE claim_id=? ORDER BY created_at,rowid",
            (claim_id,)
        ).fetchall()
    item = dict(claim)
    item["current_payload"] = json.loads(item["current_payload"])
    item["submissions"] = [{**dict(row), "payload": json.loads(row["payload"])} for row in submissions]
    item["evidence"] = [{**dict(row), "metadata": json.loads(row["metadata"])} for row in evidence]
    item["resolution_history"] = [dict(row) for row in resolutions]
    item["resolution_status"] = resolutions[-1]["new_status"] if resolutions else None
    item["assignment_history"] = [dict(row) for row in assignments]
    item["current_assignment"] = dict(assignments[-1]) if assignments else None
    return item

def resolve_claim(db_path: str | Path, claim_id: str, action: str,
                  reviewer: str, reason: str, evidence_note: str = "",
                  audit_actor: str | None = None) -> dict:
    allowed = {"REQUEST_INFORMATION", "APPROVE", "REJECT"}
    if action not in allowed:
        raise ValueError("Unsupported claim resolution action")
    if not reviewer.strip() or not reason.strip():
        raise ValueError("Reviewer and reason are required")
    now = datetime.now(timezone.utc).isoformat()
    statuses = {"REQUEST_INFORMATION": "AWAITING_INFORMATION",
                "APPROVE": "HUMAN_APPROVED", "REJECT": "HUMAN_REJECTED"}
    with connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        claim = conn.execute("SELECT current_status FROM expense_claims WHERE claim_id=?",
                             (claim_id,)).fetchone()
        if claim is None:
            raise LookupError("Expense claim not found")
        if claim["current_status"] not in ("REVIEW", "INSUFFICIENT_DATA"):
            raise ValueError("Only REVIEW or INSUFFICIENT_DATA claims can be resolved by an analyst")
        previous = conn.execute(
            "SELECT new_status FROM claim_resolution_events WHERE claim_id=? ORDER BY created_at DESC,rowid DESC LIMIT 1",
            (claim_id,)).fetchone()
        previous_status = previous["new_status"] if previous else claim["current_status"]
        if previous_status in ("HUMAN_APPROVED", "HUMAN_REJECTED"):
            raise ValueError("This claim already has a terminal human resolution")
        new_status = statuses[action]
        resolution_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO claim_resolution_events(resolution_id,claim_id,action,previous_status,new_status,reviewer,reason,evidence_note,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
            (resolution_id,claim_id,action,previous_status,new_status,reviewer.strip(),
             reason.strip(),evidence_note.strip(),now))
        if audit_actor is not None:
            _insert_audit_event(conn, "CLAIM_RESOLVED", "claim", claim_id, audit_actor,
                {"action": action, "resolution_status": new_status,
                 "reviewer": reviewer.strip(), "reason": reason.strip()}, now)
    return {"resolution_id":resolution_id,"claim_id":claim_id,"action":action,
            "previous_status":previous_status,"resolution_status":new_status,
            "reviewer":reviewer.strip(),"reason":reason.strip(),
            "evidence_note":evidence_note.strip(),"created_at":now}


def list_claim_resolutions(db_path: str | Path, claim_id: str) -> list[dict]:
    with connect(db_path) as conn:
        rows=conn.execute(
            "SELECT resolution_id,action,previous_status,new_status,reviewer,reason,evidence_note,created_at FROM claim_resolution_events WHERE claim_id=? ORDER BY created_at,rowid",
            (claim_id,)).fetchall()
    return [dict(row) for row in rows]

def assign_claim(db_path: str | Path, claim_id: str, assignee: str,
                 assigned_by: str, priority: str = "NORMAL",
                 sla_hours: int = 24, note: str = "",
                 audit_actor: str | None = None) -> dict:
    priority = priority.upper()
    if priority not in {"LOW", "NORMAL", "HIGH", "URGENT"}:
        raise ValueError("Priority must be LOW, NORMAL, HIGH or URGENT")
    if not 1 <= int(sla_hours) <= 720:
        raise ValueError("SLA must be between 1 and 720 hours")
    if not assignee.strip() or not assigned_by.strip():
        raise ValueError("Assignee and assigning reviewer are required")
    now = datetime.now(timezone.utc)
    event = {"assignment_id": str(uuid.uuid4()), "claim_id": claim_id,
             "assignee": assignee.strip(), "priority": priority,
             "sla_hours": int(sla_hours),
             "due_at": (now + timedelta(hours=int(sla_hours))).isoformat(),
             "assigned_by": assigned_by.strip(), "note": note.strip(),
             "created_at": now.isoformat()}
    with connect(db_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        claim = conn.execute("SELECT current_status FROM expense_claims WHERE claim_id=?", (claim_id,)).fetchone()
        if claim is None:
            raise LookupError("Expense claim not found")
        if claim["current_status"] not in ("REVIEW", "INSUFFICIENT_DATA"):
            raise ValueError("Only REVIEW or INSUFFICIENT_DATA claims can be assigned")
        terminal = conn.execute("SELECT new_status FROM claim_resolution_events WHERE claim_id=? ORDER BY created_at DESC,rowid DESC LIMIT 1", (claim_id,)).fetchone()
        if terminal and terminal["new_status"] in ("HUMAN_APPROVED", "HUMAN_REJECTED"):
            raise ValueError("Terminally resolved claims cannot be assigned")
        conn.execute("""INSERT INTO claim_assignment_events
          (assignment_id,claim_id,assignee,priority,sla_hours,due_at,assigned_by,note,created_at)
          VALUES(?,?,?,?,?,?,?,?,?)""",
          tuple(event[k] for k in ("assignment_id","claim_id","assignee","priority","sla_hours","due_at","assigned_by","note","created_at")))
        if audit_actor is not None:
            _insert_audit_event(conn, "CLAIM_ASSIGNED", "claim", claim_id, audit_actor,
                {"assignee": event["assignee"], "priority": priority,
                 "sla_hours": int(sla_hours)}, event["created_at"])
    return event


def list_exception_queue(db_path: str | Path, status: str | None = None,
                         assignee: str | None = None, priority: str | None = None,
                         overdue: bool | None = None, limit: int = 50,
                         offset: int = 0, sort: str = "priority") -> dict:
    now = datetime.now(timezone.utc).isoformat()
    clauses = ["c.current_status IN ('REVIEW','INSUFFICIENT_DATA')"]
    params = []
    if status:
        clauses.append("COALESCE(r.new_status,c.current_status)=?")
        params.append(status)
    if assignee:
        clauses.append("a.assignee=?")
        params.append(assignee)
    if priority:
        clauses.append("a.priority=?")
        params.append(priority.upper())
    if overdue is True:
        clauses.append("a.due_at IS NOT NULL AND a.due_at < ?")
        params.append(now)
    elif overdue is False:
        clauses.append("(a.due_at IS NULL OR a.due_at >= ?)")
        params.append(now)
    where = " WHERE " + " AND ".join(clauses)
    order_by = {
        "priority": "CASE a.priority WHEN 'URGENT' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'NORMAL' THEN 3 WHEN 'LOW' THEN 4 ELSE 5 END, a.due_at IS NULL, a.due_at, c.created_at",
        "sla": "a.due_at IS NULL, a.due_at, CASE a.priority WHEN 'URGENT' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'NORMAL' THEN 3 WHEN 'LOW' THEN 4 ELSE 5 END, c.created_at",
        "newest": "c.created_at DESC"
    }.get(sort)
    if order_by is None:
        raise ValueError("Sort must be priority, sla or newest")
    joins = """ FROM expense_claims c
      LEFT JOIN (SELECT claim_id,new_status FROM (
        SELECT claim_id,new_status,ROW_NUMBER() OVER(PARTITION BY claim_id ORDER BY created_at DESC,rowid DESC) rn
        FROM claim_resolution_events) WHERE rn=1) r ON r.claim_id=c.claim_id
      LEFT JOIN (SELECT claim_id,assignee,priority,sla_hours,due_at,assigned_by,note,created_at FROM (
        SELECT *,ROW_NUMBER() OVER(PARTITION BY claim_id ORDER BY created_at DESC,rowid DESC) rn
        FROM claim_assignment_events) WHERE rn=1) a ON a.claim_id=c.claim_id"""
    with connect(db_path) as conn:
        aggregate = conn.execute(
            "SELECT COUNT(*) total, SUM(CASE WHEN a.assignee IS NOT NULL THEN 1 ELSE 0 END) assigned_count, "
            "SUM(CASE WHEN a.assignee IS NULL THEN 1 ELSE 0 END) unassigned_count, "
            "SUM(CASE WHEN a.due_at IS NOT NULL AND a.due_at < ? THEN 1 ELSE 0 END) overdue_count"
            + joins + where, [now] + params
        ).fetchone()
        total = aggregate["total"] or 0
        rows = conn.execute("""SELECT c.claim_id,c.employee_id,c.merchant_name,c.department,
          c.amount,c.currency,c.category,c.current_status,c.created_at,c.updated_at,
          COALESCE(r.new_status,c.current_status) resolution_status,
          a.assignee,a.priority,a.sla_hours,a.due_at,a.assigned_by,a.note assignment_note,
          a.created_at assigned_at,
          CASE WHEN a.due_at IS NOT NULL AND a.due_at < ? THEN 1 ELSE 0 END overdue
        """ + joins + where + " ORDER BY " + order_by + " LIMIT ? OFFSET ?",
          [now] + params + [limit, offset]).fetchall()
    return {"total": total, "limit": limit, "offset": offset,
            "metrics": {"assigned": aggregate["assigned_count"] or 0,
                        "unassigned": aggregate["unassigned_count"] or 0,
                        "overdue": aggregate["overdue_count"] or 0},
            "items": [dict(row) for row in rows]}


def _insert_audit_event(conn: sqlite3.Connection, event_type: str, entity_type: str,
                        entity_id: str, actor: str, details: dict | None = None,
                        created_at: str | None = None) -> dict:
    """Insert an audit event using the caller's transaction."""
    if not all(str(value).strip() for value in (event_type, entity_type, entity_id, actor)):
        raise ValueError("Audit event type, entity type, entity ID and actor are required")
    event = {"event_id": str(uuid.uuid4()), "event_type": event_type,
             "entity_type": entity_type, "entity_id": entity_id,
             "actor": actor.strip(), "details": details or {},
             "created_at": created_at or datetime.now(timezone.utc).isoformat()}
    conn.execute("""INSERT INTO audit_events
      (event_id,event_type,entity_type,entity_id,actor,details,created_at)
      VALUES(?,?,?,?,?,?,?)""",
      (event["event_id"], event_type, entity_type, entity_id, actor.strip(),
       json.dumps(event["details"], sort_keys=True), event["created_at"]))
    return event


def record_audit_event(db_path: str | Path, event_type: str, entity_type: str,
                       entity_id: str, actor: str, details: dict | None = None) -> dict:
    """Append an operational audit event; existing events are never updated."""
    with connect(db_path) as conn:
        return _insert_audit_event(conn, event_type, entity_type, entity_id, actor, details)

def list_audit_events(db_path: str | Path, entity_type: str | None = None,
                      entity_id: str | None = None, event_type: str | None = None,
                      limit: int = 100, offset: int = 0) -> dict:
    clauses, params = [], []
    for column, value in (("entity_type", entity_type), ("entity_id", entity_id),
                          ("event_type", event_type)):
        if value:
            clauses.append(column + "=?")
            params.append(value)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    with connect(db_path) as conn:
        total = conn.execute("SELECT COUNT(*) n FROM audit_events" + where, params).fetchone()["n"]
        rows = conn.execute("SELECT * FROM audit_events" + where +
            " ORDER BY created_at DESC,event_id DESC LIMIT ? OFFSET ?",
            params + [limit, offset]).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["details"] = json.loads(item["details"])
        items.append(item)
    return {"total": total, "limit": limit, "offset": offset, "items": items}
