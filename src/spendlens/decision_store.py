"""Persistence and audit history for deterministic expense decisions."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
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
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(expense_decisions)")}
        if "idempotency_key" not in columns:
            conn.execute("ALTER TABLE expense_decisions ADD COLUMN idempotency_key TEXT")
        if "request_hash" not in columns:
            conn.execute("ALTER TABLE expense_decisions ADD COLUMN request_hash TEXT")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_expense_decisions_idempotency ON expense_decisions(idempotency_key) WHERE idempotency_key IS NOT NULL")
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
    return {"total": total, "limit": limit, "offset": offset, "items": [dict(row) for row in rows]}


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
    item = dict(claim)
    item["current_payload"] = json.loads(item["current_payload"])
    item["submissions"] = [{**dict(row), "payload": json.loads(row["payload"])} for row in submissions]
    item["evidence"] = [{**dict(row), "metadata": json.loads(row["metadata"])} for row in evidence]
    item["resolution_history"] = [dict(row) for row in resolutions]
    item["resolution_status"] = resolutions[-1]["new_status"] if resolutions else None
    return item

def resolve_claim(db_path: str | Path, claim_id: str, action: str,
                  reviewer: str, reason: str, evidence_note: str = "") -> dict:
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
