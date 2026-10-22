"""Persistence and audit history for deterministic expense decisions."""
from __future__ import annotations

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


def save_decision(db_path: str | Path, expense: dict, evaluation: dict) -> dict:
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
           created_at,expense_payload,evaluation_payload)
          VALUES(?,?,?,?,?,?,?,?,?)
        """, (decision["decision_id"], decision["expense_id"], decision["outcome"],
              decision["policy_id"], decision["policy_version"], decision["engine_version"],
              decision["created_at"], json.dumps(expense, sort_keys=True),
              json.dumps(evaluation, sort_keys=True)))
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
