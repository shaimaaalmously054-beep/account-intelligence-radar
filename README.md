# Account Intelligence Radar

> **Pipeline generation infrastructure for B2B outreach.**  
> Built for Averroa | Author: Mazen Zawal | v1.0.0

---

## What It Does

Turns a company name or a geography into a structured intelligence report — including HQ, business units, key executives, strategic initiatives, and evidence links — ready for a consultant to use in outreach.

Demo: https://drive.google.com/file/d/1lre_cfuySCcR6He0aPcfq6fWvMLGuldb/view?usp=sharing

### Architecture

```
User Input
    │
    ▼
[FastAPI Backend]
    │
    ├─ 1. SerpAPI          → Google search results (discovery)
    ├─ 2. DeepSeek / GPT   → URL relevance scoring (decision)
    │       └─ Fallback: OpenAI if DeepSeek returns 402
    ├─ 3. Firecrawl        → Structured extraction from URLs (acquisition)
    └─ 4. Report Builder   → JSON + Markdown output
    │
    ▼
[Frontend]
    Single-page HTML app — polls job status, renders report cards,
    offers JSON + Markdown download.
```

---

## Quick Start

### 1. Clone / unzip

```bash
cd account-intelligence-radar
```

### 2. Set up virtual environment

```bash
cd backend
python -m venv .venv

# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

# macOS / Linux:
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure API keys

```bash
cp ../.env.example .env
# Edit .env and fill in your API keys
```

`.env` contents:

```
SERPAPI_KEY=your_serpapi_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here
OPENAI_API_KEY=your_openai_api_key_here   # optional fallback
FIRECRAWL_API_KEY=your_firecrawl_api_key_here
```

### 5. Run the backend

```bash
# From /backend:
uvicorn main:app --reload --port 8000
```

### 6. Open the frontend

Open `frontend/index.html` in your browser.  
Make sure the **API Base URL** field shows `http://localhost:8000`.

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/jobs` | Create a new intelligence job |
| GET | `/api/jobs/{id}` | Poll job status |
| GET | `/api/jobs/{id}/download/json` | Download JSON report |
| GET | `/api/jobs/{id}/download/markdown` | Download Markdown report |
| GET | `/health` | Health check |

### Example: Company mode (cURL)

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "company",
    "company": {
      "company_name": "Alfanar",
      "objective_prompt": "Extract headquarters, business units, core products, target industries, key executives, and recent strategic initiatives. Return structured JSON."
    }
  }'
```

### Example: Geography mode

```bash
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "geography",
    "geography": {
      "location": "Riyadh, Saudi Arabia",
      "target_criteria": "manufacturing, energy, logistics",
      "top_n": 3
    }
  }'
```

---

## Reports

All reports are saved to `/backend/reports/<job_id>/` as:
- `<company_name>.json` — structured data
- `<company_name>.md`   — human-readable Markdown summary

---

## Engineering Notes

### Error Handling
- **No SERP results** → raises `SerpAPIError` with clear message
- **DeepSeek HTTP 402** → logs warning, falls back to OpenAI automatically
- **OpenAI unavailable** → falls back to top-5 SERP results without LLM scoring
- **Firecrawl async** → polls up to 20 times with 3-second intervals
- **Firecrawl not ready** → raises `FirecrawlNotReadyError`
- **Invalid JSON from LLM** → raises `LLMError` with raw response snippet

### Security
- API keys loaded from `.env`, never logged or exposed
- LinkedIn scraping is explicitly prohibited; a manual search query is suggested instead
- All secrets managed via `python-dotenv`; `.env` is gitignored

### Traceability
- Every report includes `evidence_links` listing source URLs used
- Strategic initiatives and leadership data are attributed to sources

---

## What I Would Improve Next

1. **Persistent job store** — swap in-memory dict for Redis or SQLite
2. **Caching** — cache SERP + Firecrawl results for repeated queries
3. **Streaming** — SSE/WebSocket for real-time progress updates
4. **Auth** — add API key middleware for multi-user deployments
5. **Unit tests** — URL filtering logic, JSON parsing, report builder
6. **Rate limiting** — add per-IP throttling on the API endpoints

---

## Sample Companies Tested
- **Alfanar** (KSA) — engineering & construction conglomerate
- **Almarai** (KSA) — largest vertically integrated dairy company in the world

See `/reports/` for sample outputs.
