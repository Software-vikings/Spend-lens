-- SpendLens Phase 3: SQL analytical views and queries
-- SQLite-compatible. All amounts are in EUR in the current synthetic dataset.

CREATE VIEW IF NOT EXISTS v_monthly_department_spend AS
SELECT substr(transaction_date,1,7) AS month, department, currency,
       SUM(amount) AS total_spend, COUNT(*) AS transaction_count,
       AVG(amount) AS average_transaction
FROM transactions GROUP BY 1,2,3;

CREATE VIEW IF NOT EXISTS v_merchant_concentration AS
WITH totals AS (
  SELECT merchant_id, merchant_name, category, currency,
         SUM(amount) AS merchant_spend, COUNT(*) AS transaction_count
  FROM transactions GROUP BY 1,2,3,4
), all_spend AS (
  SELECT currency, SUM(amount) AS total_spend FROM transactions GROUP BY currency
)
SELECT t.*, a.total_spend,
       ROUND(100.0*t.merchant_spend/NULLIF(a.total_spend,0),2) AS spend_share_pct
FROM totals t JOIN all_spend a USING(currency);

-- Headcount is an explicit business input, not inferred from transaction activity.
CREATE VIEW IF NOT EXISTS v_monthly_department_totals AS
SELECT substr(transaction_date,1,7) AS month, department, currency,
       SUM(amount) AS total_spend, COUNT(*) AS transaction_count
FROM transactions GROUP BY 1,2,3;

SELECT subscription_id, merchant_id, merchant_name, employee_id,
       COUNT(*) AS payment_count, MIN(transaction_date) AS first_payment,
       MAX(transaction_date) AS latest_payment, ROUND(MIN(amount),2) AS minimum_amount,
       ROUND(MAX(amount),2) AS maximum_amount, ROUND(AVG(amount),2) AS average_amount
FROM transactions WHERE subscription_id IS NOT NULL AND subscription_id <> ''
GROUP BY subscription_id, merchant_id, merchant_name, employee_id HAVING COUNT(*) >= 3;

SELECT employee_id, merchant_id, transaction_date, amount,
       COUNT(*) AS matching_transactions, GROUP_CONCAT(transaction_id) AS transaction_ids
FROM transactions GROUP BY employee_id, merchant_id, transaction_date, amount HAVING COUNT(*) > 1;

SELECT employee_id, merchant_id, transaction_date, category,
       COUNT(*) AS transaction_count, SUM(amount) AS combined_amount,
       GROUP_CONCAT(transaction_id) AS transaction_ids
FROM transactions GROUP BY employee_id, merchant_id, transaction_date, category HAVING COUNT(*) >= 2;

SELECT substr(transaction_date,1,7) AS month, category, SUM(amount) AS total_spend,
       COUNT(*) AS transaction_count, ROUND(AVG(amount),2) AS average_transaction
FROM transactions GROUP BY 1,2 ORDER BY 1,2;
