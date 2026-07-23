"""
Jobs API router.

POST /api/jobs          — create a new job
GET  /api/jobs/{id}     — poll job status
GET  /api/jobs/{id}/download/{fmt}  — download JSON or Markdown report
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from typing import List

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse

from models.schemas import (
    InputMode,
    JobCreateRequest,
    JobResponse,
    JobStatus,
)
from services import job_store
from services.serp_service import SerpAPIError, search_company, search_geography
from services.llm_service import LLMError, select_best_urls
from services.firecrawl_service import FirecrawlError, extract_from_urls
from services.report_service import build_report, save_report
from services.report_service import to_markdown
from services.auth_service import require_user
from services.comparison_service import persist_report_and_comparison

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Create job
# ---------------------------------------------------------------------------

@router.post("", response_model=JobResponse, status_code=202)
async def create_job(
    body: JobCreateRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_user),
):
    if body.mode == InputMode.COMPANY and not body.company:
        raise HTTPException(422, "company field is required for company mode")
    if body.mode == InputMode.GEOGRAPHY and not body.geography:
        raise HTTPException(422, "geography field is required for geography mode")

    query = (
        body.company.company_name
        if body.mode == InputMode.COMPANY
        else body.geography.location
    )
    job = job_store.create_job(
        body.mode, user["id"], query, body.model_dump(mode="json")
    )
    background_tasks.add_task(_run_job, job.job_id, user["id"], body)
    return job


@router.get("")
async def list_jobs(
    search: str = Query(default="", max_length=100),
    mode: str | None = None,
    status: str | None = None,
    user: dict = Depends(require_user),
):
    return {"items": job_store.list_jobs(user["id"], search, mode, status)}


# ---------------------------------------------------------------------------
# Poll status
# ---------------------------------------------------------------------------

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str, user: dict = Depends(require_user)):
    job = job_store.get_job(job_id, user["id"])
    if not job:
        raise HTTPException(404, f"Job {job_id!r} not found")
    return job


# ---------------------------------------------------------------------------
# Download report
# ---------------------------------------------------------------------------

@router.get("/{job_id}/download/{fmt}")
async def download_report(
    job_id: str, fmt: str, user: dict = Depends(require_user)
):
    job = job_store.get_job(job_id, user["id"])
    if not job:
        raise HTTPException(404, "Job not found")
    if job.status != JobStatus.COMPLETED:
        raise HTTPException(400, "Report not ready yet")
    if not job.report_paths:
        raise HTTPException(404, "No report files found")

    if fmt == "json":
        json_paths = [v for k, v in job.report_paths.items() if "_json" in k or k == "json"]
        if not json_paths:
            raise HTTPException(404, "JSON report not found")
        return FileResponse(json_paths[0], media_type="application/json", filename="report.json")

    elif fmt == "markdown":
        md_paths = [v for k, v in job.report_paths.items() if "_md" in k or k == "markdown"]
        if not md_paths:
            raise HTTPException(404, "Markdown report not found")
        return FileResponse(md_paths[0], media_type="text/markdown", filename="report.md")

    raise HTTPException(400, f"Unsupported format: {fmt!r}. Use 'json' or 'markdown'.")


# ---------------------------------------------------------------------------
# Background job runner
# ---------------------------------------------------------------------------

@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: str, user: dict = Depends(require_user)):
    if not job_store.delete_job(job_id, user["id"]):
        raise HTTPException(404, "Scan not found")


@router.post("/{job_id}/rerun", response_model=JobResponse, status_code=202)
async def rerun_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_user),
):
    request_data = job_store.get_request(job_id, user["id"])
    if not request_data:
        raise HTTPException(404, "Scan not found")
    body = JobCreateRequest.model_validate(request_data)
    return await create_job(body, background_tasks, user)


async def _run_job(job_id: str, user_id: str, body: JobCreateRequest):
    job = job_store.get_job(job_id)
    job.status = JobStatus.RUNNING
    job.stage = "Discovering relevant sources"
    job_store.update_job(job)

    try:
        if body.mode == InputMode.COMPANY:
            reports = await _process_company(
                job_id,
                body.company.company_name,
                body.company.objective_prompt,
            )
        else:
            reports = await _process_geography(job_id, body.geography)

        job_store.set_stage(job_id, "Building intelligence report")
        all_paths = {}
        for report in reports:
            paths = save_report(report, job_id)
            safe_key = report.company_name.lower().replace(" ", "_")[:30]
            all_paths[f"{safe_key}_json"] = paths["json"]
            all_paths[f"{safe_key}_md"]   = paths["markdown"]
            persist_report_and_comparison(
                job_id,
                user_id,
                report.model_dump(exclude={"raw_extraction"}),
                to_markdown(report),
            )

        job.status = JobStatus.COMPLETED
        job.stage = "Dashboard ready"
        job.result = reports
        job.report_paths = all_paths

    except (SerpAPIError, LLMError, FirecrawlError) as exc:
        logger.error("Job %s failed: %s", job_id, exc)
        job.status = JobStatus.FAILED
        job.error = _friendly_error(exc)

    except Exception as exc:
        logger.exception("Unexpected error in job %s", job_id)
        job.status = JobStatus.FAILED
        job.error = "We could not complete this scan. Please try again in a moment."

    finally:
        job_store.update_job(job)


async def _process_company(
    job_id: str,
    company_name: str,
    objective: str,
    context_results: list | None = None,
):
    job_store.set_stage(job_id, "Discovering relevant sources")
    logger.info("[%s] Searching for company: %s", job_id, company_name)
    serp_results = await search_company(company_name, "official site annual report executives")

    job_store.set_stage(job_id, "Analyzing and selecting high-value sources")
    logger.info("[%s] Selecting best URLs via LLM / fallback", job_id)
    urls = await select_best_urls(serp_results, objective, company_name)

    if not urls:
        raise FirecrawlError("No usable URLs found — cannot extract data.")

    job_store.set_stage(job_id, "Extracting intelligence")
    logger.info("[%s] Extracting from %d URLs via Firecrawl", job_id, len(urls))
    raw = await extract_from_urls(urls, objective, company_name)

    job_store.set_stage(job_id, "Validating evidence")
    report = build_report(
        raw,
        company_name,
        search_results=[*(context_results or []), *serp_results],
        selected_urls=urls,
    )
    return [report]


async def _process_geography(job_id: str, geo):
    logger.info("[%s] Geography search: %s / %s", job_id, geo.location, geo.target_criteria)
    serp_results = await search_geography(geo.location, geo.target_criteria)

    company_names = await _extract_company_names_from_serp(
        serp_results, geo.location, geo.target_criteria
    )
    company_names = company_names[: geo.top_n]

    if not company_names:
        raise SerpAPIError("Could not identify target companies from geography search.")

    logger.info("[%s] Found %d companies: %s", job_id, len(company_names), company_names)

    reports = []
    for name in company_names:
        try:
            company_reports = await _process_company(
                job_id, name, geo.objective_prompt, context_results=serp_results
            )
            reports.extend(company_reports)
        except Exception as exc:
            logger.warning("[%s] Skipping company %r: %s", job_id, name, exc)
        await asyncio.sleep(1)  # Polite rate limiting

    return reports


# ---------------------------------------------------------------------------
# Company name extraction from geography SERP results
# ---------------------------------------------------------------------------

async def _extract_company_names_from_serp(
    serp_results: list,
    location: str,
    criteria: str,
) -> List[str]:
    """
    Extract company names from geography SERP results.

    Priority:
      1. DeepSeek LLM
      2. OpenAI LLM
      3. Rule-based regex extraction (no LLM needed)
    """
    content = "\n".join(
        f"[{i+1}] {r['title']} — {r['snippet']}"
        for i, r in enumerate(serp_results)
    )
    prompt = (
        f"From these search results about companies in '{location}' matching '{criteria}', "
        f"extract a list of real company names only. Return ONLY a JSON array of strings. "
        f"Example: [\"Company A\", \"Company B\"]\n\nResults:\n{content}"
    )

    deepseek_key = os.getenv("DEEPSEEK_API_KEY", "")
    openai_key   = os.getenv("OPENAI_API_KEY", "")

    for base_url, key, model in [
        ("https://api.deepseek.com/v1/chat/completions", deepseek_key, "deepseek-chat"),
        ("https://api.openai.com/v1/chat/completions",   openai_key,   "gpt-4o-mini"),
    ]:
        if not key:
            continue
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    base_url,
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 256,
                        "temperature": 0,
                    },
                )
                if resp.status_code in (402, 429):
                    logger.warning(
                        "Company extraction: %s returned HTTP %d — trying next",
                        base_url.split("/")[2], resp.status_code,
                    )
                    continue
                resp.raise_for_status()
                text = resp.json()["choices"][0]["message"]["content"].strip()
                if text.startswith("```"):
                    text = text.split("```")[1].lstrip("json").strip()
                names = json.loads(text)
                if isinstance(names, list):
                    result = [n for n in names if isinstance(n, str) and n.strip()]
                    logger.info("LLM extracted %d company names", len(result))
                    return result
        except Exception as exc:
            logger.warning("Company name LLM extraction failed (%s): %s", base_url.split("/")[2], exc)

    # ── Rule-based fallback ────────────────────────────────────────────────
    logger.warning("All LLMs unavailable — using rule-based company name extraction")
    return _rule_based_company_names(serp_results, location, criteria)


def _rule_based_company_names(
    serp_results: list,
    location: str,
    criteria: str,
    max_names: int = 10,
) -> List[str]:
    """
    Extract likely company names from SERP titles and snippets without an LLM.

    Strategy:
    - Pull Title-Case runs of 1–4 words from titles
    - Boost candidates that appear in multiple results
    - Apply a blocklist of generic words unlikely to be company names
    - Deduplicate, return top N by frequency
    """
    # Generic words to exclude from company name candidates
    BLOCKLIST = {
        "top", "best", "leading", "major", "largest", "companies", "company",
        "list", "industry", "industries", "sector", "sectors", "market",
        "energy", "oil", "gas", "power", "water", "telecom", "bank", "finance",
        "group", "holding", "international", "national", "saudi", "arabia",
        "riyadh", "jeddah", "dubai", "uae", "gcc", "mena", "middle", "east",
        "the", "and", "for", "with", "from", "into", "about", "more", "new",
        "news", "report", "reports", "annual", "review", "overview", "guide",
        "how", "why", "what", "when", "which", "who", "where",
        location.lower(),
    } | {w.lower() for w in criteria.split(",")}

    # Add location words to blocklist
    for word in re.split(r"[\s,]+", location):
        BLOCKLIST.add(word.lower())

    candidate_freq: dict[str, int] = {}

    for r in serp_results:
        text = r.get("title", "") + " " + r.get("snippet", "")
        # Extract Title Case sequences (1–4 consecutive capitalised words)
        matches = re.findall(r"\b([A-Z][a-zA-Z&\-\.]{1,}(?:\s+[A-Z][a-zA-Z&\-\.]{1,}){0,3})\b", text)
        for m in matches:
            words = m.strip().split()
            # Filter: skip if any word is in blocklist or word is a single char
            if any(w.lower() in BLOCKLIST or len(w) <= 1 for w in words):
                continue
            # Skip very generic single-word capitalised words
            if len(words) == 1 and len(m) < 4:
                continue
            candidate_freq[m] = candidate_freq.get(m, 0) + 1

    # Sort by frequency desc, then alphabetically for tie-breaking
    ranked = sorted(candidate_freq.items(), key=lambda x: (-x[1], x[0]))
    names = [name for name, _ in ranked[:max_names]]

    logger.info("Rule-based extraction found %d candidate companies: %s", len(names), names[:5])
    return names


def _friendly_error(exc: Exception) -> str:
    message = str(exc)
    if "402" in message or "balance" in message.lower():
        return "The intelligence provider has insufficient balance. Check the server billing configuration."
    if "timed out" in message.lower():
        return "The research provider timed out. Your scan was saved; please run it again."
    if "No search results" in message:
        return "No relevant public sources were found. Try a more specific company or location."
    if "FIRECRAWL" in message.upper():
        return "A source could not be extracted. Please retry the scan."
    return "The scan could not be completed with the available sources. Please refine the query and try again."
