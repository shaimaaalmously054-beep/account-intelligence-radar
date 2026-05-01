# Account Intelligence Radar — Consultant Summary

**Prepared by:** Mazen Zawal  
**Date:** February 2026  
**Client:** Averroa (Internal)

---

## 1. Problem Solved

Business development teams lose significant outreach effort to two gaps: (1) not knowing which companies to prioritise in a given market, and (2) lacking structured intelligence on a company's decision-makers, current initiatives, and strategic direction before the first call.

This tool eliminates both gaps. Given a company name or geography, it produces a structured, evidence-backed intelligence report in under two minutes — replacing hours of manual research.

---

## 2. Architecture Decisions

**Three-API pipeline with clear separation of concerns:**

| Layer | Tool | Rationale |
|-------|------|-----------|
| Discovery | SerpAPI | Reliable, structured Google results via API — avoids brittle scraping |
| Decision | DeepSeek / OpenAI | LLM-driven URL relevance scoring outperforms regex or keyword matching |
| Extraction | Firecrawl | Handles JS-rendered pages and async extraction natively |

**Web app over CLI (Option B):** A browser frontend makes the tool accessible to non-technical consultants without requiring Python environment setup, and the job-polling model naturally handles Firecrawl's async extraction.

**DeepSeek-first with OpenAI fallback:** DeepSeek's reasoning models offer strong cost/performance for structured selection tasks. The 402 error is handled gracefully — the tool degrades to OpenAI, then to rule-based URL selection, so a depleted API balance never causes a hard failure.

**In-memory job store:** Sufficient for single-user local deployment. Clearly flagged in the codebase as a swap point for Redis in production.

---

## 3. Key Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| API key exposure | `.env` file with `.gitignore`; keys never logged |
| LinkedIn scraping temptation | Explicitly blocked; provides manual search query suggestion instead |
| Firecrawl async timeout | Polls up to 20× with graceful `FirecrawlNotReadyError` |
| LLM hallucinated executives | Firecrawl prompt instructs "only extract explicitly stated data" |
| DeepSeek 402 during demo | Automatic OpenAI fallback; logged as warning not failure |
| No SERP results | Raises descriptive error immediately rather than cascading silently |

---

## 4. What I Would Improve Next

1. **Persistent storage** — Redis or SQLite for job history across restarts
2. **Report caching** — identical queries return cached results to save API costs
3. **Streaming UI** — WebSocket progress updates instead of polling
4. **Multi-tenant auth** — per-user API key management for team deployments
5. **Scoring dashboard** — rank companies by outreach priority score based on initiative density and recency

---

*This tool is pipeline infrastructure, not a nice-to-have. Every minute saved on research is a minute added to outreach.*
