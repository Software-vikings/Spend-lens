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


def save_decision(db_path: str | Path, expense: dict, evaluation: dict,\n                  idempotency_key: str | None = None) -> dict:
    request_hash = hashlib.sha256(json.dumps({"expense": expense, "evaluation": evaluation}, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    if idempotency_key:
        with connect(db_path) as conn:
            existing = conn.execute("SELECT decision_id,request_hash FROM expense_decisions WHERE idempotency_key=?", (idempotency_key,)).fetchone()
        if existing:
            if existing["request_hash"] != request_hash:
                raise ValueError("Idempotency key was already used for a different expense request")
            return get_decision(db_path, existing["decision_id"])
    decision = {
        "decision_id": str(uuid.uuid4()),
        "expense_id": str(evaluation["expense_id"]),
        "outcome": evaluation["outcome"],
        "policy_id": evaluation["policy_id"],
        "policy_version": evaluation["policy_version"],
        "engine_version": evaluation["engine_version"],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expense": expense,
        "evaluation": evaluation,
    }
    with connect(db_path) as conn:
        conn.execute("""
          INSERT INTO expense_decisions
          (decision_id,expense_id,outcome,policy_id,policy_version,engine_version,
           created_at,expense_payload,evaluation_payload,idempotency_key,request_hash)
          VALUES(?,?,?,?,?,?,?,?,?,?,?)
        """, (decision["decision_id"], decision["expense_id"], decision["outcome"],
              decision["policy_id"], decision["policy_version"], decision["engine_version"],
              decision["created_at"], json.dumps(expense, sort_keys=True),
              json.dumps(evaluation, sort_keys=True), idempotency_key, request_hash))
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
