"""Phase 4 persistence for repeatable findings and human review."""
from __future__ import annotations
import hashlib, json, sqlite3
from datetime import datetime, timezone
from pathlib import Path

def connect(db_path: str | Path):
    conn = sqlite3.connect(str(db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def init_phase4(db_path: str | Path):
    with connect(db_path) as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS pipeline_runs (
          run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, transaction_count INTEGER NOT NULL,
          finding_count INTEGER NOT NULL, status TEXT NOT NULL CHECK(status IN ('success','failed'))
        );
        CREATE TABLE IF NOT EXISTS findings (
          finding_id TEXT PRIMARY KEY, finding_type TEXT NOT NULL, fingerprint TEXT NOT NULL UNIQUE,
          title TEXT NOT NULL, severity TEXT NOT NULL, amount REAL, currency TEXT,
          first_seen_at TEXT NOT NULL, last_seen_at TEXT NOT NULL, occurrences INTEGER NOT NULL DEFAULT 1,
          review_status TEXT NOT NULL DEFAULT 'new'
            CHECK(review_status IN ('new','under_review','confirmed','dismissed','resolved')),
          reviewer TEXT, review_note TEXT, source_payload TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS finding_events (
          event_id INTEGER PRIMARY KEY AUTOINCREMENT, finding_id TEXT NOT NULL,
          event_at TEXT NOT NULL, old_status TEXT, new_status TEXT NOT NULL,
          reviewer TEXT, note TEXT, FOREIGN KEY(finding_id) REFERENCES findings(finding_id)
        );
        CREATE INDEX IF NOT EXISTS idx_findings_status ON findings(review_status);
        CREATE INDEX IF NOT EXISTS idx_findings_type ON findings(finding_type);
        """)

def _identity(kind: str, row: dict) -> str:
    keys = {"anomaly":("transaction_id",),"recurring_payment_change":("subscription_id",),
      "merchant_price_drift":("merchant_id","category"),
      "duplicate_candidate":("employee_id","merchant_id","transaction_date","amount"),
      "fragmented_purchase":("employee_id","merchant_id","transaction_date","category")}[kind]
    raw = json.dumps([kind, *[row.get(k) for k in keys]], sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()

def _title(kind: str, row: dict) -> str:
    labels = {"anomaly":"Unusual transaction amount","recurring_payment_change":"Recurring payment changed",
      "merchant_price_drift":"Merchant spend increased","duplicate_candidate":"Possible duplicate transactions",
      "fragmented_purchase":"Potential fragmented purchase"}
    return labels[kind]

def persist_findings(db_path: str | Path, groups: dict[str, list[dict]], run_id: str):
    now = datetime.now(timezone.utc).isoformat()
    count = 0
    with connect(db_path) as c:
        for kind, rows in groups.items():
            for row in rows:
                fp = _identity(kind, row)
                finding_id = fp[:20]
                amount = row.get("amount") or row.get("latest_amount") or row.get("recent_median") or row.get("combined_amount")
                severity = "high" if kind in ("anomaly","duplicate_candidate","fragmented_purchase") else "medium"
                payload = json.dumps(row, sort_keys=True, default=str)
                c.execute("""
                  INSERT INTO findings(finding_id,finding_type,fingerprint,title,severity,amount,currency,
                    first_seen_at,last_seen_at,occurrences,source_payload)
                  VALUES(?,?,?,?,?,?,?, ?,?,?,?)
                  ON CONFLICT(fingerprint) DO UPDATE SET
                    last_seen_at=excluded.last_seen_at,
                    occurrences=findings.occurrences+1,
                    source_payload=excluded.source_payload
                """, (finding_id,kind,fp,_title(kind,row),severity,amount,
                      row.get("currency","EUR"),now,now,1,payload))
                count += 1
        c.execute("""INSERT OR REPLACE INTO pipeline_runs
          (run_id,started_at,transaction_count,finding_count,status) VALUES(?,?,?,?,?)""",
          (run_id,now,0,count,"success"))
    return count

def record_run(db_path: str | Path, run_id: str, transaction_count: int, finding_count: int):
    with connect(db_path) as c:
        c.execute("""INSERT OR REPLACE INTO pipeline_runs
          (run_id,started_at,transaction_count,finding_count,status) VALUES(?,?,?,?,?)""",
          (run_id,datetime.now(timezone.utc).isoformat(),transaction_count,finding_count,"success"))
