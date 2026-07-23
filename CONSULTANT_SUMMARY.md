# Account Intelligence Radar — Consultant Summary

**Prepared by:** Mazen Zawal
**Updated:** July 2026
**Client:** Averroa (Internal)

---

## 1. Executive Summary

Account Intelligence Radar is a persistent B2B intelligence workspace that
turns a company name or market brief into a structured, evidence-backed report.
It replaces fragmented manual research with a repeatable workflow:

`Search → Analyze → View → Save → Revisit → Compare → Detect Changes → Act`

The product now supports the complete research lifecycle rather than producing
only one-off JSON files. Consultants can search companies or geographies,
monitor real processing stages, review findings in an interactive dashboard,
inspect every retained source, revisit historical scans, identify meaningful
changes, and export a professional PDF report.

The result is a reusable account-intelligence capability for business
development, qualification, meeting preparation, and ongoing account
monitoring.

---

## 2. Business Problem Solved

Business development teams commonly face three research gaps:

1. They do not know which companies to prioritize in a target market.
2. They lack structured intelligence on decision-makers, products, initiatives,
   and strategic direction before outreach.
3. They cannot easily determine what has changed since an account was last
   researched.

Account Intelligence Radar addresses all three gaps. It converts public
information into a persistent company profile with traceable evidence and
historical comparisons, reducing manual research effort while improving the
quality and timing of outreach.

---

## 3. Current Product Experience

### Search and Processing

- Company intelligence search with a configurable research objective
- Geography intelligence search using location, industry, and target criteria
- Real pipeline-stage messages without fabricated completion percentages
- Automatic navigation to the completed report dashboard

### Intelligence Dashboard

- Executive summary and report metadata
- Business units, products, services, and target industries
- Leadership signals and source attribution when provided
- Strategic initiatives and transformation signals
- Evidence links with safe, clickable original URLs
- Searchable and filterable source library
- Source-details panel with publisher, domain, type, dates, search context,
  snippet, extraction status, and evidence
- Raw search-results view for newly generated reports
- Readable canonical JSON view

### Persistent Intelligence

- Secure user accounts and server-side sessions
- User-owned search history and reports
- Persistent company profiles
- Historical scan timelines
- Normalized NEW, CHANGED, REMOVED, and UNCHANGED detection
- Repeat-scan comparisons that ignore ordering, formatting, and common wording
  variations

### Exports

- Canonical JSON
- Human-readable Markdown
- Professional multi-page PDF with report metadata, findings, evidence,
  clickable source URLs, bibliography, headers, footers, and page numbers

---

## 4. Architecture Decisions

### Research Pipeline

| Layer | Technology | Purpose |
|---|---|---|
| Discovery | SerpAPI | Returns structured search results and source URLs |
| Decision | DeepSeek / OpenAI | Selects the highest-value sources for extraction |
| Fallback | Deterministic URL scoring | Keeps scans operational when LLM providers are unavailable |
| Extraction | Firecrawl | Extracts structured intelligence from selected pages |
| Canonical output | Pydantic JSON model | Provides one consistent intelligence format |
| Presentation | Responsive SPA | Renders dashboards, history, sources, and comparisons |
| Persistence | SQLite | Stores users, sessions, scans, reports, and comparisons |
| Documents | ReportLab | Generates consistent server-side PDF reports |

### Key Design Principles

**Preserve the research engine:** The original SerpAPI, LLM-selection, and
Firecrawl pipeline remains the core intelligence engine. The workspace,
persistence, and reporting layers are built around it rather than duplicating
its business logic.

**JSON as the canonical data layer:** The dashboard, comparisons, source views,
Markdown, and PDF exports derive from the same stored report. This prevents
conflicting report versions.

**Evidence-first presentation:** Original URLs remain visible and safely
clickable. New scans also retain search-result titles, snippets, rank, discovery
query, deterministic source type, and extraction status.

**Secure multi-user architecture:** Passwords are salted and hashed with
PBKDF2. Sessions are server-managed, records are ownership-scoped, secrets
remain in environment variables, and private data is not stored as
browser-authoritative state.

**Meaningful comparison:** Change detection normalizes business terms, names,
lists, sources, and formatting before comparison to reduce false positives.

---

## 5. Reliability and Security

| Risk | Mitigation |
|---|---|
| API key exposure | Provider credentials remain server-side and are excluded from source control |
| Cross-user data access | Every private report, scan, company, and comparison query enforces ownership |
| Plain-text passwords | PBKDF2 hashing with unique salts |
| Malicious source content | All external text is escaped; raw external HTML is never rendered |
| Unsafe links | Only HTTP and HTTPS URLs are accepted; links use `noopener noreferrer` |
| Tracking and duplicate URLs | URL normalization removes common tracking parameters and deduplicates stable pages |
| LLM provider balance or quota failure | DeepSeek falls back to OpenAI, then deterministic URL scoring |
| Firecrawl timeout | Bounded polling and user-friendly failure messages |
| Invalid or incomplete reports | Typed models, graceful empty states, and legacy-report normalization |
| Unsupported claims | Missing claim-level attribution is shown explicitly rather than inferred |
| Inconsistent PDF output | Server-side generation from the canonical stored report |

---

## 6. Validation Status

The current implementation has been validated through:

- 15 automated backend and integration tests
- Authentication and record-ownership tests
- Legacy report compatibility without a previous comparison
- NEW, CHANGED, REMOVED, and UNCHANGED comparison tests
- Unsafe URL rejection and source-normalization tests
- PDF endpoint, filename, MIME type, and clickable-link tests
- Long multi-page PDF tests containing every source
- Visual review of a real three-page Averroa PDF
- Authenticated desktop and mobile browser validation
- Source-details and secure new-tab behavior checks
- Frontend JavaScript syntax and application import checks

---

## 7. Current Limitations

- Historical reports created before source preservation contain evidence URLs
  but not the discarded SERP title, snippet, rank, or discovery query.
- Claim-level source attribution is available only when the extraction result
  provides it; the application does not fabricate mappings.
- Background scans currently use FastAPI background tasks, which are appropriate
  for a single-process deployment but not horizontal production scaling.
- Password recovery and email verification require an outbound email provider.
- The current Python/FastAPI application requires a Python-compatible production
  host and is not directly deployable as a Cloudflare Worker.

---

## 8. Recommended Next Improvements

1. **Durable worker queue** — move scans to Celery, Dramatiq, or a managed queue
   for retries, concurrency control, and horizontal scaling.
2. **Per-source extraction outcomes** — retain partial Firecrawl results and
   expose success or failure for each individual page.
3. **Claim-level evidence mapping** — extend the extraction schema so every
   leadership signal and initiative returns explicit source identifiers.
4. **Monitoring and scheduled rescans** — allow users to subscribe to companies
   and receive alerts when meaningful intelligence changes.
5. **Report caching and cost controls** — reuse recent discovery and extraction
   results where freshness requirements permit.
6. **Team collaboration** — add shared workspaces, comments, assignments, and
   role-based access.
7. **Opportunity scoring** — introduce a transparent, evidence-based scoring
   model only after sufficient historical data is available.

---

## 9. Strategic Value

Account Intelligence Radar has evolved from a research utility into a
persistent intelligence system. Its value is not limited to producing a faster
report; it creates a growing institutional record of target accounts, their
strategic signals, the supporting evidence, and the changes that matter over
time.

This makes the platform useful before outreach, during qualification, throughout
account planning, and whenever a consultant needs to answer:

**What do we know, what changed, and what should we do next?**
