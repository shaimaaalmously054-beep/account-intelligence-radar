"""
Acquisition & extraction layer — Firecrawl Extract API.

Crawls selected URLs and extracts structured business intelligence.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

FIRECRAWL_EXTRACT_URL = "https://api.firecrawl.dev/v1/extract"
FIRECRAWL_POLL_URL = "https://api.firecrawl.dev/v1/extract/{job_id}"


class FirecrawlError(Exception):
    pass


class FirecrawlNotReadyError(FirecrawlError):
    """Raised when extraction job is still processing."""
    pass


def _get_key() -> str:
    key = os.getenv("FIRECRAWL_API_KEY", "")
    if not key:
        raise FirecrawlError("FIRECRAWL_API_KEY is not set in environment.")
    return key


EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "company_name": {"type": "string"},
        "headquarters": {"type": "string"},
        "business_units": {"type": "array", "items": {"type": "string"}},
        "products_and_services": {"type": "array", "items": {"type": "string"}},
        "target_industries": {"type": "array", "items": {"type": "string"}},
        "leadership": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "title": {"type": "string"},
                },
            },
        },
        "strategic_initiatives": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "description": {"type": "string"},
                    "category": {"type": "string"},
                },
            },
        },
    },
}


async def extract_from_urls(
    urls: List[str],
    objective_prompt: str,
    company_name: str,
) -> Dict[str, Any]:
    """
    Submits URLs to Firecrawl Extract and returns structured JSON data.
    Polls for completion if the job is async.
    """
    if not urls:
        raise FirecrawlError("No URLs provided for extraction.")

    headers = {
        "Authorization": f"Bearer {_get_key()}",
        "Content-Type": "application/json",
    }

    full_prompt = (
        f"Company: {company_name}\n"
        f"Task: {objective_prompt}\n"
        f"Only extract information that is explicitly stated in the source pages. "
        f"For leadership, only include executives mentioned on official company pages. "
        f"Do not infer or fabricate data."
    )

    payload = {
        "urls": urls,
        "prompt": full_prompt,
        "schema": EXTRACTION_SCHEMA,
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(FIRECRAWL_EXTRACT_URL, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        raise FirecrawlError("Firecrawl request timed out.")
    except httpx.HTTPStatusError as exc:
        raise FirecrawlError(
            f"Firecrawl HTTP error {exc.response.status_code}: {exc.response.text[:300]}"
        )

    # Synchronous result
    if data.get("success") and data.get("data"):
        logger.info("Firecrawl returned synchronous result for %s", company_name)
        return _normalise(data["data"], urls)

    # Async job — poll for completion
    job_id = data.get("id")
    if job_id:
        logger.info("Firecrawl async job %s started, polling...", job_id)
        return await _poll_job(job_id, headers, urls)

    raise FirecrawlError(f"Unexpected Firecrawl response: {str(data)[:300]}")


async def _poll_job(
    job_id: str,
    headers: Dict[str, str],
    urls: List[str],
    max_attempts: int = 20,
    interval: float = 3.0,
) -> Dict[str, Any]:
    import asyncio

    poll_url = FIRECRAWL_POLL_URL.format(job_id=job_id)

    for attempt in range(max_attempts):
        await asyncio.sleep(interval)
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.get(poll_url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPStatusError as exc:
            raise FirecrawlError(f"Firecrawl poll HTTP {exc.response.status_code}")

        status = data.get("status", "")
        logger.info("Firecrawl poll attempt %d/%d — status: %s", attempt + 1, max_attempts, status)

        if status == "completed" and data.get("data"):
            return _normalise(data["data"], urls)

        if status == "failed":
            raise FirecrawlError(f"Firecrawl extraction job failed: {data.get('error', 'unknown')}")

    raise FirecrawlNotReadyError(
        f"Firecrawl job {job_id} did not complete after {max_attempts} attempts."
    )


def _normalise(raw: Any, urls: List[str]) -> Dict[str, Any]:
    """
    Normalise Firecrawl output to our internal schema.
    raw can be a dict or a list; we merge if list.
    """
    if isinstance(raw, list):
        merged: Dict[str, Any] = {}
        for item in raw:
            if isinstance(item, dict):
                for k, v in item.items():
                    if k not in merged:
                        merged[k] = v
                    elif isinstance(merged[k], list) and isinstance(v, list):
                        # Deduplicate lists
                        seen = {json.dumps(x, sort_keys=True) for x in merged[k]}
                        for entry in v:
                            if json.dumps(entry, sort_keys=True) not in seen:
                                merged[k].append(entry)
                                seen.add(json.dumps(entry, sort_keys=True))
        raw = merged

    if not isinstance(raw, dict):
        raw = {}

    raw["_source_urls"] = urls
    return raw
