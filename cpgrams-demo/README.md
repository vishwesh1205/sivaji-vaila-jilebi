# CPGRAMS Educational Demo

An independent, local-only teaching replica of a CPGRAMS-style public grievance portal. It demonstrates a complete complaint journey without contacting the Government of India or filing a real grievance.

> **EDUCATIONAL DEMO — UNOFFICIAL REPLICA. NOT CONNECTED TO THE GOVERNMENT OF INDIA. NO REAL GOVERNMENT GRIEVANCE IS FILED.**

## What it includes

- Reference-inspired responsive homepage with a disclosure ribbon, masthead, carousel and service cards.
- Demo login and registration that store a local profile only. No passwords, OTPs, CAPTCHA, Aadhaar or government credentials are requested.
- Grievance form with server-side validation, a one-time submission token, optional attachment, generated registration number and a separate verification code.
- Status lookup, a local timeline, reminders/clarifications, and satisfaction feedback for closed demo records.
- Seeded examples, JSON/CSV exports, support pages in English, Hindi and Tamil, and English fallback for other languages.
- Optional, authenticated sync to the existing AICTE complaint dashboard. The integration is off by default.
- SQLite persistence with synthetic data only.

## Quick start

```bash
cd cpgrams-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m app.seed
uvicorn app.main:app --reload --port 8090
```

Open <http://127.0.0.1:8090>. Use the **Demo Citizen** login; no credentials are needed.

Current seeded references use the current year:

| Reference | Verification code | Status |
|---|---|---|
| `CPGRAMS-DEMO-<year>-00001` | `DEMO-CITIZEN-001` | Closed — Demo |
| `CPGRAMS-DEMO-<year>-00002` | `DEMO-CITIZEN-002` | Under Process — Demo |
| `CPGRAMS-DEMO-<year>-00003` | `DEMO-CITIZEN-003` | Received — Demo |

The homepage and status page display the current examples.

## Local data and reset

Data is stored in `data/cpgrams_demo.db`; attachments go to `data/uploads/`.

```bash
python -m app.seed            # create tables and seed only if empty
python -m app.seed --reset    # delete local records and restore examples
python -m app.seed --reset --no-seed
```

The HTTP reset endpoint is disabled by default. To enable it for a disposable local instance:

```bash
CPGRAMS_ALLOW_RESET=1 uvicorn app.main:app --port 8090
curl -X POST http://127.0.0.1:8090/demo/reset \
  -H 'Content-Type: application/json' \
  -d '{"confirm":"RESET-DEMO-DATA"}'
```

Reset is destructive and applies only to this demo database. Never point `CPGRAMS_DB_PATH` at another application's database.

## Configuration

Copy `.env.example` values into your shell environment or process manager. The app reads environment variables directly and does not require a `.env` loader.

| Variable | Purpose |
|---|---|
| `CPGRAMS_DB_PATH` | Override the local SQLite database path. |
| `CPGRAMS_UPLOAD_DIR` | Override the attachment directory. |
| `CPGRAMS_DB_URL` | Optional durable `libsql://` Turso database URL. Used instead of SQLite when set. |
| `CPGRAMS_DB_AUTH_TOKEN` | Turso database token for `CPGRAMS_DB_URL`. |
| `CPGRAMS_SESSION_SECRET` | Sign demo session/flash cookies. Set a strong random value outside local use. |
| `CPGRAMS_ALLOW_RESET` | Must be exactly `1` to enable `POST /demo/reset`. |
| `DASHBOARD_INGEST_URL` | Existing dashboard ingestion endpoint, for example `http://127.0.0.1:8000/ingest/json`. |
| `DASHBOARD_USERNAME` / `DASHBOARD_PASSWORD` | Dedicated dashboard account used to obtain and refresh bearer tokens. |
| `DASHBOARD_LOGIN_URL` | Optional dashboard login URL. Derived from `DASHBOARD_INGEST_URL` when omitted. |
| `DASHBOARD_BEARER_TOKEN` | Optional short-lived fallback token. |
| `DASHBOARD_TIMEOUT_SECONDS` | Sync timeout, clamped to 1–15 seconds. |

### Dashboard integration

When enabled, a new demo grievance is POSTed to the dashboard's existing authenticated `/ingest/json` contract. The payload is explicitly marked `source_name: CPGRAMS Simulator`, `source_type: SIMULATOR` and `is_synthetic: true`.

The demo can log in to the dashboard automatically and refresh an expired token. Create a dedicated dashboard account for this integration and configure it server-side:

```bash
export DASHBOARD_INGEST_URL=http://127.0.0.1:8000/ingest/json
export DASHBOARD_USERNAME=cpgrams.demo@example.test
export DASHBOARD_PASSWORD='replace-with-a-strong-password'
python -m uvicorn app.main:app --reload --port 8090
```

`DASHBOARD_LOGIN_URL` is derived by replacing `/ingest/json` with `/auth/login`. Set it explicitly if the dashboard is mounted under a different path. If the dashboard rejects a cached/static token with `401`, the adapter logs in again when credentials are configured. Do not use a personal administrator password for a public demo.

The dashboard must be publicly reachable and its ingestion endpoint must accept this app's origin at the network level. The request is server-to-server, so no browser CORS configuration is needed for the demo-to-dashboard sync. The dashboard must also be running a schema/version that stores `source_name`, `source_type`, `is_synthetic`, `subject`, and raw payload provenance; this repository's updated ingestion route does so.

A network failure never removes the local record. It remains `pending` and can be retried:

```bash
python -m app.dashboard_sync --limit 20
```

If the existing dashboard ignores provenance fields, its own schema remains authoritative. This project does not bypass its authentication or validation.

## Deploy on Vercel

The repository includes `vercel.json` for a FastAPI project rooted at `cpgrams-demo/`.

Vercel's local filesystem is ephemeral, so use a Turso database for durable records:

1. Create a free Turso database and database token.
2. Import `cpgrams-demo/` as a Vercel project (Framework Preset: FastAPI) or deploy that directory with the Vercel CLI.
3. Add these Vercel environment variables:
   - `CPGRAMS_DB_URL=libsql://...`
   - `CPGRAMS_DB_AUTH_TOKEN=...`
   - `CPGRAMS_SESSION_SECRET=<long random value>`
   - `DASHBOARD_INGEST_URL=https://<dashboard-api-host>/ingest/json`
   - `DASHBOARD_USERNAME=...`
   - `DASHBOARD_PASSWORD=...`
4. Deploy. The first request creates the schema and inserts the three seed examples.

The database is durable with Turso, but uploaded attachments are written to Vercel's temporary filesystem. For durable uploads, use external object storage in a production deployment. Without `CPGRAMS_DB_URL`, the app falls back to a temporary Vercel SQLite file and data may disappear between instances.

The AICTE dashboard frontend can also be deployed on Vercel from `frontend/`. Build it with `VITE_API_BASE_URL` set to the public dashboard API URL (for example `https://dashboard-api.example.com`). The dashboard backend needs persistent PostgreSQL and should run on a container host or other long-lived service; the dashboard's scheduled jobs are not suitable for a short-lived serverless function.

## Tests

```bash
cd cpgrams-demo
python -m pytest -q
```

The suite uses FastAPI's test client and isolated temporary SQLite databases. It covers public pages, demo auth, validation, one-time form tokens, complaint creation, status lookup, reminders, feedback, exports, reset gating, language fallback, dashboard failure handling, and dashboard token refresh.

## Routes

| Route | Purpose |
|---|---|
| `/` | Homepage, seeded examples and service links. |
| `/login`, `/register`, `/logout` | Local demo identity. |
| `/grievance/new` | Authenticated demo complaint form. |
| `/grievance/success` | Receipt with reference and verification code. |
| `/status`, `/status/view` | Lookup and timeline. |
| `/reminder`, `/feedback` | Clarification and satisfaction flows. |
| `/api/complaints` | Synthetic data export. |
| `/export/complaints.json`, `/export/complaints.csv` | Downloadable exports. |
| `/health` | Local health check. |

Supporting pages: `/about`, `/contact`, `/faq`, `/sitemap`, `/privacy`, `/grievance/process`, `/grievance/pension`.

## Privacy and safety

- All records are synthetic; the UI and exports label them as demo data.
- No real personal information is required. The form warns against entering Aadhaar, PAN, passwords or OTPs.
- Uploads accept only PDF, TXT, PNG and JPEG up to 2 MB and are stored locally.
- On Vercel, use Turso for complaint records; local attachment files are temporary unless external object storage is added.
- Security headers, signed HttpOnly cookies, one-time form tokens and parameterised SQL are used.
- The site sends no data to the official CPGRAMS portal and has no government affiliation.

## Limitations

- This is a demonstration of interface and workflow, not a legally valid grievance channel.
- Demo identities are not secure accounts; anyone with local access can use the shared demo identity.
- Status changes are simulated locally and are not made by government officers.
- The optional dashboard adapter depends on that project's current API contract and credentials.
- The dashboard displays demo grievances with `SIMULATOR` / `CPGRAMS Simulator` provenance; they are not live government complaints.
