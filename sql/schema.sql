PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id TEXT PRIMARY KEY,
    transaction_date TEXT NOT NULL,
    employee_id TEXT NOT NULL,
    department TEXT NOT NULL,
    merchant_id TEXT NOT NULL,
    merchant_name TEXT NOT NULL,
    category TEXT NOT NULL,
    amount REAL NOT NULL CHECK (amount >= 0),
    currency TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    scenario_label INTEGER NOT NULL DEFAULT 0 CHECK (scenario_label IN (0,1)),
    scenario_type TEXT NOT NULL DEFAULT 'ordinary',
    subscription_id TEXT,
    invoice_reference TEXT
);

CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(transaction_date);
CREATE INDEX IF NOT EXISTS idx_transactions_merchant ON transactions(merchant_id);
CREATE INDEX IF NOT EXISTS idx_transactions_department ON transactions(department);
CREATE INDEX IF NOT EXISTS idx_transactions_subscription ON transactions(subscription_id);
CREATE INDEX IF NOT EXISTS idx_transactions_invoice ON transactions(invoice_reference);

CREATE VIEW IF NOT EXISTS monthly_department_spend AS
SELECT substr(transaction_date,1,7) AS month, department, currency,
       SUM(amount) AS total_spend, COUNT(*) AS transaction_count
FROM transactions GROUP BY 1,2,3;

CREATE VIEW IF NOT EXISTS merchant_spend AS
SELECT merchant_id, merchant_name, category, currency, SUM(amount) AS total_spend,
       COUNT(*) AS transaction_count, AVG(amount) AS average_transaction
FROM transactions GROUP BY merchant_id, merchant_name, category, currency;
