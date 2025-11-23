# Getting started with the Silky Credit & Behaviour Engine

This guide explains what the service does, how it is structured, and how to run it locally for demos or development.

## What the app does

- **Purpose**: Generate a `CreditDashboard` JSON payload for a given merchant that blends KYC data, behavioural analytics, financial health, cashflow forecasting, credit scoring, and lender-specific offers.
- **Consumers**: Silky internal dashboards, merchant portals, and banking partners needing a consistent credit view.
- **Safety**: The prompt forbids use of protected attributes (religion, gender, nationality, ethnicity) and every response includes governance metadata (`safety_and_compliance`, `audit_metadata`).

## Project layout

```
main.py                # FastAPI entrypoint and startup hooks
app/api.py             # HTTP routes
app/config.py          # Settings from env vars
app/db.py              # SQLAlchemy engine/session and Base
app/models.py          # ORM models for merchants, usage, transactions, snapshots
app/schemas.py         # Pydantic schemas including CreditDashboard contract
app/services/          # Domain services that fetch/prepare data and call OpenAI
app/seed_db.py         # Demo data seeding for a single merchant
app/static/            # Prompt templates
```

## Prerequisites

- Python 3.11+
- Access to an OpenAI API key with the Responses API enabled
- (Optional) A running database if you do not want to use SQLite

## Environment configuration

1. Copy the sample env file and set values:

   ```bash
   cp .env.example .env
   ```

2. Key environment variables:

   - `ENV`: `dev` or `prod`
   - `DB_URL`: SQLAlchemy DSN (e.g., `sqlite:///./silky_credit.db` for local demos; Postgres/MySQL URIs also work)
   - `OPENAI_API_KEY`: your OpenAI key
   - `OPENAI_MODEL`: e.g., `gpt-5.1`
   - `LOG_LEVEL`: `INFO`, `DEBUG`, etc.

## Installing dependencies

```bash
python -m venv venv && source venv/bin/activate  # recommended
pip install -r requirements.txt
```

## Running the API locally

Start Uvicorn with auto-reload for development:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

On startup the app will:

- Create all tables in the configured database.
- Seed demo data if the DB is empty (one F&B QSR merchant with POS revenue, invoices, and usage events).

## Trying the credit dashboard

Fetch the dashboard for the demo merchant (ID `1`):

```bash
# Internal analytics view
curl "http://localhost:8000/api/credit-dashboard/1?viewer_type=silky_internal"

# Bank partner view with lender context
curl "http://localhost:8000/api/credit-dashboard/1?viewer_type=bank_partner&lender_id=SAB"
```

The response matches the `CreditDashboard` schema in [`app/schemas.py`](../app/schemas.py).

## Using a custom database

- SQLite (default): `DB_URL=sqlite:///./silky_credit.db`
- Postgres example: `DB_URL=postgresql+psycopg2://user:pass@localhost:5432/silky_credit`
- MySQL example: `DB_URL=mysql+pymysql://user:pass@localhost:3306/silky_credit`

Run migrations by recreating tables on startup (currently handled by `Base.metadata.create_all`).

## Running tests

```bash
pytest
```

Tests stub OpenAI calls and spin up a TestClient against an in-memory SQLite DB. Ensure your `.env` is not pointing to a production database when running tests.

## Troubleshooting

- **Missing OpenAI credentials**: Ensure `OPENAI_API_KEY` and `OPENAI_MODEL` are set; the API will fail if unset.
- **Database locked (SQLite)**: Stop other processes holding the file or switch to a separate test DB via `DB_URL`.
- **Slow startup**: The seed step runs only when tables are empty; persistent DBs avoid reseeding each boot.
- **Structured output issues**: Confirm the configured model supports the Responses API.

