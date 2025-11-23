# Silky Credit & Behaviour Engine v2.0 (ChatGPT 5.1)

The Silky Credit & Behaviour Engine powers the **Silky Credit & Behaviour Dashboard**. For any given merchant it combines KYC details, behaviour and feature adoption, financial health, cashflow forecast, a credit score and band, and prescriptive credit offers into a single `CreditDashboard` JSON payload consumable by Silky's UI and banking partners.

- **Tech stack**: FastAPI, SQLAlchemy, Pydantic, OpenAI SDK (Responses API), Uvicorn, SQLite (defaults to SQLite for demos; works with Postgres/MySQL via `DB_URL`).
- **Model**: Uses the `OPENAI_MODEL` environment variable (defaults to ChatGPT 5.1 family) with structured JSON output.
- **Seeded demo**: On startup the app creates tables and seeds multiple sample merchants so you can try the dashboard immediately.

> Looking for a detailed walkthrough? See [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) for environment setup, runtime options, and troubleshooting tips.

## How to run locally

**Requirements**: Python 3.10+, `pip`, and optionally `virtualenv`/`venv`.

1. Create and activate a virtual environment (recommended):

   ```bash
   python -m venv venv && source venv/bin/activate
   # On Windows: python -m venv venv && venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set environment variables:

   - `OPENAI_API_KEY` (required)
   - `OPENAI_MODEL` (optional, defaults to `gpt-5.1`)
   - `DB_URL` (optional, defaults to local SQLite; if unavailable the app will fall back to `sqlite:///./silky_credit.db` and seed demo data)

4. Run the app:

   ```bash
   uvicorn main:app --reload
   ```

5. Open the dashboard UI at http://127.0.0.1:8000/dashboard and click through the sample customers. If no external DB is configured, the app automatically provisions a demo SQLite database with multiple merchants and usage patterns.

## Core capabilities

- **KYC profile**: Bank-style legal and registration details per merchant.
- **Behavioural analytics**: Activity, feature adoption, discipline, and behavioural risk tracking.
- **Financial health**: Revenue trends, liquidity proxies, seasonality, and profitability proxies.
- **Cashflow forecast**: Base, conservative, and optimistic scenarios with drivers.
- **Credit intelligence**: Credit score, risk band, limit/tenor recommendation, and offer suggestions.
- **Governance**: Safety and compliance flags plus audit metadata for every generated dashboard.

## Quickstart

1. **Install dependencies**

   ```bash
   python -m venv venv && source venv/bin/activate  # optional but recommended
   pip install -r requirements.txt
   ```

2. **Set environment variables**

   Copy the starter file and fill values:

   ```bash
   cp .env.example .env
   ```

   Key fields:
   - `ENV`: `dev` or `prod`
   - `DB_URL`: SQLAlchemy DSN (e.g., `sqlite:///./silky_credit.db` for demos)
   - `OPENAI_API_KEY`: your OpenAI key
   - `OPENAI_MODEL`: e.g., `gpt-5.1` or a compatible reasoning model
   - `LOG_LEVEL`: log verbosity (e.g., `INFO`, `DEBUG`)

3. **Run the API server**

   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

   Startup automatically creates the schema and seeds demo data when the database is empty.

4. **Call the API**

   - Internal analytics view:

     ```bash
     curl "http://localhost:8000/api/credit-dashboard/1?viewer_type=silky_internal"
     ```

   - Bank partner view (with lender context):

     ```bash
     curl "http://localhost:8000/api/credit-dashboard/1?viewer_type=bank_partner&lender_id=SAB"
     ```

   Both return the `CreditDashboard` JSON contract defined in [`app/schemas.py`](app/schemas.py).

## Development & testing

- **Run tests**:

  ```bash
  pytest
  ```

- **Code layout**:
  - `main.py`: FastAPI application factory and startup hooks.
  - `app/api.py`: Routes for generating credit dashboards.
  - `app/models.py` & `app/db.py`: SQLAlchemy models and engine/session setup.
  - `app/services/`: Domain services that assemble dashboard data.
  - `app/seed_db.py`: Demo data seeding on startup.

## Safety & governance

- The prompt and schema explicitly forbid using protected attributes (religion, gender, nationality, ethnicity) in scoring.
- `safety_and_compliance` and `audit_metadata` sections capture why a score was produced and how it should be governed.
- Each call stores a snapshot table (`silky_credit_profile_snapshots`) so you can monitor drift, overrides, and lifecycle events.

## Additional documentation

- [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) – detailed environment setup, running locally, API examples, and troubleshooting.

