"""Versioned policy registry with immutable policy documents and activation history."""
from __future__ import annotations
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from .phase4 import connect
from .decision_engine import validate_policy

def init_policy_registry(db_path: str | Path, seed_policy: dict | None = None) -> None:
    with connect(db_path) as conn:
        # Serialise schema creation and seed checks across simultaneous API requests.
        # executescript() implicitly commits, so use individual statements after
        # BEGIN IMMEDIATE to keep the whole initialisation atomic.
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""
        CREATE TABLE IF NOT EXISTS policies (
          policy_id TEXT NOT NULL, version TEXT NOT NULL, name TEXT NOT NULL,
          document TEXT NOT NULL, created_at TEXT NOT NULL, created_by TEXT NOT NULL,
          PRIMARY KEY(policy_id,version)
        )
        """)
        conn.execute("""
        CREATE TABLE IF NOT EXISTS policy_activations (
          activation_id INTEGER PRIMARY KEY AUTOINCREMENT,
          policy_id TEXT NOT NULL, version TEXT NOT NULL,
          activated_at TEXT NOT NULL, activated_by TEXT NOT NULL,
          FOREIGN KEY(policy_id,version) REFERENCES policies(policy_id,version)
        )
        """)
        conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_policy_activation_latest
          ON policy_activations(policy_id,activation_id DESC)
        """)
        if seed_policy:
            validate_policy(seed_policy)
            exists=conn.execute("SELECT 1 FROM policies WHERE policy_id=? AND version=?",
                                (seed_policy["policy_id"],seed_policy["version"])).fetchone()
            if not exists:
                conn.execute("INSERT INTO policies VALUES(?,?,?,?,?,?)",
                    (seed_policy["policy_id"],seed_policy["version"],seed_policy.get("name",seed_policy["policy_id"]),
                     json.dumps(seed_policy,sort_keys=True),datetime.now(timezone.utc).isoformat(),"system-seed"))
            active=conn.execute("SELECT 1 FROM policy_activations WHERE policy_id=? LIMIT 1",
                                (seed_policy["policy_id"],)).fetchone()
            if not active:
                conn.execute("INSERT INTO policy_activations(policy_id,version,activated_at,activated_by) VALUES(?,?,?,?)",
                    (seed_policy["policy_id"],seed_policy["version"],datetime.now(timezone.utc).isoformat(),"system-seed"))

def _insert_policy_audit(conn, event_type: str, policy_id: str, version: str, actor: str, now: str) -> None:
    """Write policy audit data in the same transaction as the policy change."""
    conn.execute("""INSERT INTO audit_events
      (event_id,event_type,entity_type,entity_id,actor,details,created_at)
      VALUES(?,?,?,?,?,?,?)""",
      (str(uuid.uuid4()), event_type, "policy", f"{policy_id}:{version}", actor,
       json.dumps({"policy_id": policy_id, "version": version}, sort_keys=True), now))


def create_policy_version(db_path: str | Path, policy: dict, created_by: str) -> dict:
    validate_policy(policy)
    now=datetime.now(timezone.utc).isoformat()
    with connect(db_path) as conn:
        if conn.execute("SELECT 1 FROM policies WHERE policy_id=? AND version=?",
                        (policy["policy_id"],policy["version"])).fetchone():
            raise ValueError("Policy version already exists and policy versions are immutable")
        conn.execute("INSERT INTO policies VALUES(?,?,?,?,?,?)",
            (policy["policy_id"],policy["version"],policy.get("name",policy["policy_id"]),
             json.dumps(policy,sort_keys=True),now,created_by))
        _insert_policy_audit(conn, "POLICY_CREATED", policy["policy_id"], policy["version"], created_by, now)
    return {"policy_id":policy["policy_id"],"version":policy["version"],"name":policy.get("name",policy["policy_id"]),"created_at":now,"created_by":created_by}

def activate_policy_version(db_path: str | Path, policy_id: str, version: str, activated_by: str) -> dict:
    now=datetime.now(timezone.utc).isoformat()
    with connect(db_path) as conn:
        row=conn.execute("SELECT document FROM policies WHERE policy_id=? AND version=?",(policy_id,version)).fetchone()
        if not row: raise LookupError("Policy version not found")
        validate_policy(json.loads(row["document"]))
        conn.execute("INSERT INTO policy_activations(policy_id,version,activated_at,activated_by) VALUES(?,?,?,?)",
                     (policy_id,version,now,activated_by))
        _insert_policy_audit(conn, "POLICY_ACTIVATED", policy_id, version, activated_by, now)
    return {"policy_id":policy_id,"version":version,"activated_at":now,"activated_by":activated_by}

def get_active_policy(db_path: str | Path, policy_id: str | None = None) -> dict | None:
    with connect(db_path) as conn:
        if policy_id:
            row=conn.execute("SELECT p.document FROM policy_activations a JOIN policies p USING(policy_id,version) WHERE a.policy_id=? ORDER BY a.activation_id DESC LIMIT 1",(policy_id,)).fetchone()
        else:
            row=conn.execute("SELECT p.document FROM policy_activations a JOIN policies p USING(policy_id,version) ORDER BY a.activation_id DESC LIMIT 1").fetchone()
    return json.loads(row["document"]) if row else None

def list_policy_versions(db_path: str | Path) -> list[dict]:
    with connect(db_path) as conn:
        rows=conn.execute("""
          SELECT p.policy_id,p.version,p.name,p.created_at,p.created_by,
            (SELECT a.activated_at FROM policy_activations a WHERE a.policy_id=p.policy_id AND a.version=p.version ORDER BY a.activation_id DESC LIMIT 1) activated_at,
            (SELECT a.activated_by FROM policy_activations a WHERE a.policy_id=p.policy_id AND a.version=p.version ORDER BY a.activation_id DESC LIMIT 1) activated_by,
            CASE WHEN EXISTS(SELECT 1 FROM policy_activations a WHERE a.policy_id=p.policy_id AND a.version=p.version AND a.activation_id=(SELECT MAX(a2.activation_id) FROM policy_activations a2 WHERE a2.policy_id=p.policy_id)) THEN 1 ELSE 0 END is_active
          FROM policies p ORDER BY p.policy_id,p.created_at DESC
        """).fetchall()
    return [dict(r) for r in rows]

def get_policy_version(db_path: str | Path, policy_id: str, version: str) -> dict | None:
    with connect(db_path) as conn:
        row=conn.execute("SELECT document FROM policies WHERE policy_id=? AND version=?",(policy_id,version)).fetchone()
    return json.loads(row["document"]) if row else None
