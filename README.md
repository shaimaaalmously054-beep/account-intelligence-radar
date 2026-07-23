# Account Intelligence Radar

A persistent B2B intelligence workspace for researching companies and markets,
reviewing evidence, preserving scan history, and detecting meaningful change.

## Product workflow

`Search → Analyze → View → Save → Revisit → Compare → Detect Changes → Act`

The original research engine remains intact:

1. SerpAPI discovers public sources.
2. DeepSeek or OpenAI selects high-value URLs, with a rule-based fallback.
3. Firecrawl extracts normalized company intelligence.
4. The report builder preserves canonical JSON and Markdown outputs.
5. SQLite stores user-owned scans, reports, company profiles, and comparisons.
6. The responsive workspace presents dashboards, history, evidence, and changes.

## Features

- Secure registration, login, logout, and server-side sessions
- Salted PBKDF2 password hashing; passwords and API keys never reach the browser
- Company and geography intelligence search modes
- Real pipeline stage messages without fabricated percentages
- Responsive SaaS dashboard with collapsible mobile navigation
- Automatic per-user scan history and persistent company profiles
- Normalized NEW, CHANGED, REMOVED, and UNCHANGED detection
- Field-aware comparisons that ignore ordering, formatting, and common aliases
- Full source/search-result preservation for new scans, with legacy evidence fallback
- Searchable source cards, full URLs, deterministic types, and a details drawer
- Raw SERP results and canonical JSON report tabs
- Clickable evidence sources and claim-level attribution when available
- Professional server-generated PDFs with clickable source bibliographies
- PDF, JSON, and Markdown download routes
- Light, dark, and system themes
- Friendly provider, timeout, empty-result, and extraction error states

## Architecture

```text
frontend/index.html (responsive SPA)
        │ secure same-origin cookies
        ▼
FastAPI
├── auth router
├── jobs router
├── reports / comparisons / companies router
├── existing research pipeline
└── SQLite persistence
        ├── users
        ├── sessions
        ├── jobs
        ├── reports
        └── comparisons
```

The generated JSON remains the canonical intelligence format. The dashboard,
source views, history, profiles, comparisons, and all exports are derived from it.

## Run locally

Requires Python 3.10+.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item ..\example.env .env
```

Add the provider keys to `backend/.env`, then start the application:

```powershell
uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000`. The FastAPI process now serves both the application
and the API, which keeps authentication cookies same-origin.

## Test

From `backend/`:

```powershell
python -m unittest discover -s tests -v
python -m compileall -q .
```

The tests cover password hashing, session lifecycle, authenticated API access,
record ownership, durable jobs, deletion authorization, comparison behavior,
unsafe URL rejection, source normalization, legacy reports, PDF endpoints,
clickable PDF links, and long multi-page reports.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/register` | Create an account and session |
| POST | `/api/auth/login` | Sign in |
| POST | `/api/auth/logout` | Revoke the current session |
| GET | `/api/auth/me` | Current user |
| POST | `/api/jobs` | Start a company or geography scan |
| GET | `/api/jobs` | Search and filter user-owned history |
| GET | `/api/jobs/{id}` | Poll status and real pipeline stage |
| POST | `/api/jobs/{id}/rerun` | Run the stored request again |
| DELETE | `/api/jobs/{id}` | Delete a scan and dependent records |
| GET | `/api/reports/{id}` | Dashboard-ready report |
| GET | `/api/reports/{id}/export/{format}` | PDF, JSON, or Markdown export |
| GET | `/api/comparisons/{id}` | Normalized change set |
| GET | `/api/companies` | Persistent company profiles |
| GET | `/api/companies/{slug}` | Current report, scans, and timeline |

All intelligence and history endpoints require an authenticated user and enforce
record ownership server-side.

## Data and migration

The database is created automatically at `backend/data/radar.db` on first start.
No manual migration is required for a fresh deployment. The original report
files under `backend/reports/` remain untouched and readable; new completed scans
are written to both the legacy JSON/Markdown files and the persistent database.

Existing historical files are not automatically assigned to users because they
have no trustworthy ownership metadata. They can be imported later with an
explicit administrator migration if needed.

## Deployment notes

- Set `COOKIE_SECURE=true` behind HTTPS.
- Set `ALLOWED_ORIGINS` to the exact permitted origins.
- Store `SERPAPI_KEY`, `FIRECRAWL_API_KEY`, and optional LLM keys in server
  environment variables.
- Back up `backend/data/radar.db` and `backend/reports/`.
- Run background scans through a durable worker queue before horizontal scaling;
  FastAPI background tasks remain appropriate for the current single-process
  deployment model.
