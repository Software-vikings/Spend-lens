# SpendLens

**Upload-first expense review and transaction screening.**

SpendLens turns an employer's transaction export into an explainable review list. Upload a CSV or Excel workbook, inspect the records that need attention, and download a review file for the finance team.

## What the upload workflow does

- Accepts .csv and .xlsx files up to 10 MB and 10,000 data rows.
- Automatically recognises common transaction-export headings for date, merchant/payee, amount, currency, employee, department, category, payment method and receipt/invoice reference.
- Validates required fields and reports rows that could not be analysed.
- Identifies possible duplicates based on employee (when supplied), merchant, date, amount and currency.
- Screens for unusually high amounts within merchant/category/currency groups when there are at least nine comparable records. The screen uses a robust median/MAD score.
- Flags future-dated records for checking and keeps negative-value credits/refunds visible.
- Shows data coverage, currency totals, row-level explanations and a downloadable CSV review report.

The upload workflow analyses the submitted file during the request and does not insert uploaded rows into the application database or retain a saved import history. The multipart framework may temporarily spool request data to server-managed temporary storage before analysis; the request file is closed after processing. Results are held in the current browser page and are cleared when the page is refreshed.

## What it does not claim

A transaction export alone cannot prove that a payment happened, that a receipt is genuine, that a named employee made the purchase, or that an expense is legitimate. Similar transactions may be valid recurring purchases; an unusual amount may have a reasonable explanation.

The current upload workflow is a screening tool, not a fraud adjudicator:
- A possible duplicate or unusual amount is a lead for human review.
- A row with no screening signal is not automatically approved.
- Employer-specific policy compliance is not yet evaluated by the upload workflow. That requires the organisation's authorised policy rules to be configured and applied, rather than assuming example thresholds are correct.
- Receipt authenticity and bank/card settlement verification require source-system evidence or integrations that are not part of this upload release.

## Run locally

Requires Python 3.10+.

    git clone https://github.com/Software-vikings/Spend-lens.git
    cd Spend-lens
    python -m venv .venv
    source .venv/bin/activate        # Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    PYTHONPATH=src uvicorn spendlens.api:app --host 127.0.0.1 --port 8000

Open http://127.0.0.1:8000. The upload workflow does not ask visitors for an API key.

The repository retains protected operational API routes for the policy, decision and exception-management prototype. Those routes use API-key roles; configure them with the SPENDLENS_API_KEYS environment variable only when using those internal endpoints. The browser upload workspace does not expose or ask users to enter those keys.

## Upload API

POST /v1/imports/analyze accepts one multipart file field named file. It returns:
- detected source-column mappings;
- records analysed and row-level input errors;
- duplicate and unusual-amount review signals;
- positive totals grouped by currency;
- a list of limitations that accompany the results.

The route is intentionally stateless and does not write the source file or imported rows to the application database.

## Rate limiting

The API uses separate per-client-IP request budgets rather than one counter for every website request:
- Upload analysis: 10 requests per 60 seconds.
- State-changing API requests: 60 per 60 seconds.
- Read-only API requests: 600 per 60 seconds.
- Static website assets and the health endpoint do not consume these API budgets.

A 429 response includes a Retry-After header. The in-memory limiter is process-local and is not a distributed production rate limiter.

## Security and data handling

The uploaded file is received by the server for processing, so the server hosting SpendLens can access its contents during the request even though the application does not persist it. Use HTTPS in any hosted environment. Do not upload sensitive business or employee data to a public instance until the organisation has approved the hosting, access, retention and privacy arrangements.

See SECURITY.md for the current controls and remaining production work. This repository is a portfolio prototype, not a production-certified financial control platform.
