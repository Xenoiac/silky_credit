# Silky Credit & Behaviour Engine v2.0 (ChatGPT 5.1)

This service powers the **Silky Credit & Behaviour Dashboard** for Silky Systems.
For any given customer (merchant) it combines:

- KYC profile (bank-style)
- Behavioural usage (activity & feature adoption)
- Financial health (revenue trends, liquidity, seasonality)
- Cashflow forecast (base / conservative / optimistic)
- Credit score & risk band
- Recommended credit limit and tenor
- Safety & governance notes
- Concrete **Credit Offers** per lender policy
- Early-warning flags and lifecycle monitoring
- **Improvement actions** for the merchant
- Segment-aware strengths / risks
- Audit metadata & simple economics estimates

All of this is returned as a single `CreditDashboard` JSON object that the Silky UI,
merchant portal, and banking partners can consume.

The engine uses the **OpenAI Python SDK** and the **ChatGPT 5.1 model** (via the
`OPENAI_MODEL` environment variable) with **structured JSON output**.

## 1. Tech stack

- Python 3.11+
- FastAPI
- SQLAlchemy (ORM)
- Pydantic models (for schemas)
- OpenAI SDK (`openai`) using the Responses API
- Uvicorn (ASGI server)
- SQLite by default (easy demo) – production can point to MySQL/Postgres via `DB_URL`

## 2. Setup

### 2.1. Create and activate virtualenv (optional but recommended)

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2.2. Install dependencies

```bash
pip install -r requirements.txt
```

### 2.3. Environment variables

Copy `.env.example` to `.env` and fill values:

```bash
cp .env.example .env
```

Important fields:

- `ENV` – `dev` or `prod`
- `DB_URL` – SQLAlchemy DSN, e.g.

  ```text
  sqlite:///./silky_credit.db
  ```

  or for MySQL:

  ```text
  mysql+pymysql://silky_user:super_secret@127.0.0.1:3306/silky_main
  ```

- `OPENAI_API_KEY` – your OpenAI API key.
- `OPENAI_MODEL` – e.g. `gpt-5.1` (or any compatible reasoning model)

### 2.4. Database

By default the service uses SQLite and automatically creates and seeds a demo DB at startup.

Tables include (simplified):

- `customers`
- `customer_settings`
- `users`
- `usage_events`
- `pos_transactions`
- `invoices`
- `silky_credit_profile_snapshots` (for history / monitoring)

The seed script inserts **one demo merchant (customer_id=1)** with:

- F&B QSR business in Riyadh
- 12 months of POS revenue
- A few invoices and usage events

This is enough to demo the full pipeline.

## 3. Running the service

### 3.1. Run with Uvicorn (dev)

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

On startup the app will:

- Create all tables.
- Seed demo data if the DB is empty.

### 3.2. Call the API

Example (internal analytics view):

```bash
curl "http://localhost:8000/api/credit-dashboard/1?viewer_type=silky_internal"
```

Example (bank partner view with simple lender id):

```bash
curl "http://localhost:8000/api/credit-dashboard/1?viewer_type=bank_partner&lender_id=SAB"
```

### 3.3. Response

You will get back a `CreditDashboard` JSON object with:

- KYC & behaviour sections
- Financial health & cashflow
- Credit score, band, recommended limit & tenor
- Credit offers for the lender
- Early-warning flags & lifecycle recommendations
- Improvement actions for the merchant
- Segment-specific commentary
- Audit metadata & basic economics

## 4. Integrating with Silky UI

Use your frontend stack (Vue/React) to call:

```http
GET /api/credit-dashboard/{customer_id}?viewer_type=silky_internal
```

Treat the response as the canonical `CreditDashboard` contract (see `app/schemas.py`).

You can render:

- KYC cards
- Behaviour cards
- Financial & cashflow charts
- Credit score & offers panel
- Flags and recommendations

## 5. Production notes

- In **prod**, point `DB_URL` to your analytics or OLTP database.
- Replace the seed data with real Silky data or an ETL pipeline.
- Optionally restrict the endpoint behind auth and role-based access.

## 6. Safety & governance

- The agent prompt **forbids** using protected attributes (religion, gender,
  nationality, ethnicity) in scoring.
- The `CreditDashboard` includes `safety_and_compliance` and `audit_metadata`
  sections for model governance and audits.
- Every call stores a snapshot in `silky_credit_profile_snapshots` so you can
  monitor score drift, overrides, and decisions over time.
