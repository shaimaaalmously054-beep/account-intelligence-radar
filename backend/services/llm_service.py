"""
Decision layer — LLM-based URL relevance scoring.

Supports DeepSeek (primary) with OpenAI fallback, then rule-based fallback.
Handles HTTP 402 (insufficient balance) and 429 (quota exceeded) gracefully.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import List, Dict, Any

import httpx

logger = logging.getLogger(__name__)

DEEPSEEK_BASE = "https://api.deepseek.com/v1/chat/completions"
OPENAI_BASE   = "https://api.openai.com/v1/chat/completions"

# Domains that are never useful for B2B intelligence extraction
_SKIP_DOMAINS = {
    "linkedin.com", "facebook.com", "twitter.com", "x.com",
    "instagram.com", "tiktok.com", "youtube.com",
    "glassdoor.com", "indeed.com", "ziprecruiter.com",
    "quora.com", "reddit.com", "pinterest.com",
}

# Domains we actively prefer (official / credible sources)
_PREFERRED_DOMAINS = {
    "bloomberg.com", "reuters.com", "ft.com", "wsj.com",
    "forbes.com", "businesswire.com", "prnewswire.com",
    "zawya.com", "arabianbusiness.com", "argaam.com",
}


class LLMError(Exception):
    pass


class InsufficientBalanceError(LLMError):
    """Raised when DeepSeek returns HTTP 402."""
    pass


class QuotaExceededError(LLMError):
    """Raised when any LLM returns HTTP 429."""
    pass


def _deepseek_key() -> str:
    return os.getenv("DEEPSEEK_API_KEY", "")


def _openai_key() -> str:
    return os.getenv("OPENAI_API_KEY", "")


SYSTEM_PROMPT = """You are a business intelligence analyst.
You will receive a list of web search results (title, URL, snippet) and an objective.
Your task: select the 3-5 most relevant URLs for extracting structured business intelligence
to support B2B outreach. Prefer official company websites, press releases, annual reports,
credible news sources. Exclude social media, job boards, and LinkedIn.

Return ONLY a JSON array of selected URLs, no explanation.
Example: ["https://example.com/about", "https://news.example.com/press"]"""


async def select_best_urls(
    serp_results: List[Dict[str, Any]],
    objective: str,
    company_name: str,
) -> List[str]:
    """
    Select the most relevant URLs for extraction.

    Priority:
      1. DeepSeek LLM
      2. OpenAI LLM (if DeepSeek is 402)
      3. Rule-based scoring (if all LLMs are out of quota / unavailable)
    """
    # Strip blacklisted domains before any LLM call
    filtered = [
        r for r in serp_results
        if not _is_blacklisted(r.get("link", ""))
    ]

    if not filtered:
        logger.warning("All SERP results were blacklisted — returning empty URL list")
        return []

    user_content = _build_user_content(company_name, objective, filtered)

    # ── 1. DeepSeek ──────────────────────────────────────────────────────────
    deepseek_key = _deepseek_key()
    if deepseek_key:
        try:
            urls = await _call_llm(DEEPSEEK_BASE, deepseek_key, user_content)
            logger.info("DeepSeek selected %d URLs", len(urls))
            return urls
        except InsufficientBalanceError:
            logger.warning("DeepSeek 402: insufficient balance — trying OpenAI")
        except QuotaExceededError:
            logger.warning("DeepSeek 429: quota exceeded — trying OpenAI")
        except LLMError as exc:
            logger.warning("DeepSeek error: %s — trying OpenAI", exc)

    # ── 2. OpenAI ────────────────────────────────────────────────────────────
    openai_key = _openai_key()
    if openai_key:
        try:
            urls = await _call_llm(OPENAI_BASE, openai_key, user_content, model="gpt-4o-mini")
            logger.info("OpenAI selected %d URLs", len(urls))
            return urls
        except InsufficientBalanceError:
            logger.warning("OpenAI 402: insufficient balance — using rule-based fallback")
        except QuotaExceededError:
            logger.warning("OpenAI 429: quota exceeded — using rule-based fallback")
        except LLMError as exc:
            logger.warning("OpenAI error: %s — using rule-based fallback", exc)

    # ── 3. Rule-based fallback ────────────────────────────────────────────────
    urls = _rule_based_select(filtered, company_name)
    logger.warning(
        "All LLMs unavailable — rule-based fallback selected %d URLs: %s",
        len(urls), urls,
    )
    return urls


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_blacklisted(url: str) -> bool:
    try:
        domain = url.split("/")[2].lstrip("www.")
    except IndexError:
        return True
    return any(domain == d or domain.endswith("." + d) for d in _SKIP_DOMAINS)


def _build_user_content(company_name: str, objective: str, results: List[Dict]) -> str:
    lines = [f"Company: {company_name}", f"Objective: {objective}", "", "Search results:"]
    for i, r in enumerate(results, 1):
        lines.append(f"[{i}] Title: {r['title']}")
        lines.append(f"    URL: {r['link']}")
        lines.append(f"    Snippet: {r['snippet']}")
    return "\n".join(lines)


def _rule_based_select(results: List[Dict], company_name: str, n: int = 5) -> List[str]:
    """
    Score SERP results without an LLM.
    Scoring heuristics (higher = better):
      +3  URL contains company name slug
      +2  URL is from a preferred news/financial domain
      +2  Title contains 'about', 'annual report', 'investor', 'leadership', 'executive'
      +1  URL ends in / (likely a homepage or section root)
      -1  URL path is very deep (more than 4 segments — probably a blog/job post)
    """
    company_slug = re.sub(r"[^\w]", "", company_name.lower())
    scored = []
    for r in results:
        url   = r.get("link", "")
        title = r.get("title", "").lower()
        score = 0

        try:
            domain = url.split("/")[2].lstrip("www.")
            path   = "/" + "/".join(url.split("/")[3:])
        except IndexError:
            domain, path = "", url

        if company_slug and company_slug in domain:
            score += 3
        if any(domain == d or domain.endswith("." + d) for d in _PREFERRED_DOMAINS):
            score += 2
        if any(kw in title for kw in ("about", "annual report", "investor", "leadership", "executive", "overview")):
            score += 2
        if url.rstrip("/").count("/") <= 3:
            score += 1
        if path.count("/") > 4:
            score -= 1

        scored.append((score, url))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [url for _, url in scored[:n]]


async def _call_llm(
    base_url: str,
    api_key: str,
    user_content: str,
    model: str = "deepseek-chat",
) -> List[str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_content},
        ],
        "max_tokens": 512,
        "temperature": 0,
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(base_url, headers=headers, json=payload)

            if resp.status_code == 402:
                raise InsufficientBalanceError("HTTP 402 — insufficient API balance")
            if resp.status_code == 429:
                raise QuotaExceededError("HTTP 429 — quota / rate limit exceeded")

            resp.raise_for_status()
            data = resp.json()

    except (InsufficientBalanceError, QuotaExceededError):
        raise
    except httpx.TimeoutException:
        raise LLMError("LLM request timed out")
    except httpx.HTTPStatusError as exc:
        raise LLMError(
            f"LLM HTTP error {exc.response.status_code}: {exc.response.text[:200]}"
        )

    raw_text = data["choices"][0]["message"]["content"].strip()

    # Strip markdown fences if present
    if raw_text.startswith("```"):
        raw_text = raw_text.split("```")[1]
        if raw_text.startswith("json"):
            raw_text = raw_text[4:]
        raw_text = raw_text.strip()

    try:
        urls = json.loads(raw_text)
        if not isinstance(urls, list):
            raise ValueError("Expected JSON array")
        return [u for u in urls if isinstance(u, str) and u.startswith("http")]
    except (json.JSONDecodeError, ValueError) as exc:
        raise LLMError(f"LLM returned invalid JSON: {exc} | raw: {raw_text[:300]}")
