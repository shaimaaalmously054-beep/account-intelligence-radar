"""
Discovery layer — SerpAPI Google Search.

Searches for relevant URLs about a target company or geography.
"""

from __future__ import annotations

import logging
import os
from typing import List, Dict, Any

import httpx

logger = logging.getLogger(__name__)

SERPAPI_BASE = "https://serpapi.com/search"


class SerpAPIError(Exception):
    pass


def _get_key() -> str:
    key = os.getenv("SERPAPI_KEY", "")
    if not key:
        raise SerpAPIError("SERPAPI_KEY is not set in environment.")
    return key


async def search_company(company_name: str, extra_query: str = "") -> List[Dict[str, Any]]:
    """
    Returns a list of organic search results for a company.
    Each result has: title, link, snippet.
    """
    query = f"{company_name} {extra_query}".strip()
    return await _search(query)


async def search_geography(location: str, criteria: str) -> List[Dict[str, Any]]:
    """
    Returns organic results for a geography + sector combination.
    """
    query = f"top companies {criteria} {location}"
    return await _search(query)


async def _search(query: str) -> List[Dict[str, Any]]:
    params = {
        "q": query,
        "api_key": _get_key(),
        "num": 10,
        "hl": "en",
    }
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(SERPAPI_BASE, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.TimeoutException:
        raise SerpAPIError(f"SerpAPI request timed out for query: {query!r}")
    except httpx.HTTPStatusError as exc:
        raise SerpAPIError(f"SerpAPI HTTP error {exc.response.status_code}: {exc.response.text[:200]}")

    organic = data.get("organic_results", [])
    if not organic:
        logger.warning("SerpAPI returned 0 organic results for query: %r", query)
        raise SerpAPIError(f"No search results found for: {query!r}")

    results = []
    for item in organic:
        results.append(
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            }
        )
    logger.info("SerpAPI returned %d results for %r", len(results), query)
    return results
