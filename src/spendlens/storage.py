"""SQLite persistence for the SpendLens prototype."""
import csv, sqlite3
from pathlib import Path
SCHEMA = Path(__file__).resolve().parents[2] / "sql" / "schema.sql"

def create_database(db_path: str | Path, schema_path: str | Path = SCHEMA) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(Path(schema_path).read_text(encoding="utf-8"))
    try:
        Path(db_path).chmod(0o600)
    except OSError:
        pass

def validate_transactions(rows: list[dict]) -> None:
    required = {"transaction_id","transaction_date","employee_id","department",
                "merchant_id","merchant_name","category","amount","currency","payment_method"}
    seen = set()
    for index, row in enumerate(rows, start=2):
        missing = sorted(required - row.keys())
        if missing:
            raise ValueError(f"Row {index}: missing required fields: {', '.join(missing)}")
        txid = str(row["transaction_id"]).strip()
        if not txid:
            raise ValueError(f"Row {index}: transaction_id cannot be blank")
        if txid in seen:
            raise ValueError(f"Row {index}: duplicate transaction_id {txid}")
        seen.add(txid)
        try:
            from datetime import date
            date.fromisoformat(str(row["transaction_date"]))
            amount = float(row["amount"])
        except (TypeError, ValueError):
            raise ValueError(f"Row {index}: invalid transaction_date or amount")
        if amount < 0:
            raise ValueError(f"Row {index}: amount cannot be negative")
        if not str(row["currency"]).strip():
            raise ValueError(f"Row {index}: currency cannot be blank")

def load_transactions(csv_path: str | Path, db_path: str | Path) -> int:
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    validate_transactions(rows)
    with sqlite3.connect(db_path) as conn:
        conn.executemany("""
            INSERT OR REPLACE INTO transactions
            (transaction_id,transaction_date,employee_id,department,merchant_id,merchant_name,
             category,amount,currency,payment_method,scenario_label,scenario_type,
             subscription_id,invoice_reference)
            VALUES (:transaction_id,:transaction_date,:employee_id,:department,:merchant_id,
             :merchant_name,:category,:amount,:currency,:payment_method,:scenario_label,
             :scenario_type,:subscription_id,:invoice_reference)
        """, rows)
    return len(rows)
