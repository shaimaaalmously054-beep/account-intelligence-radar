"""Backward-compatible source normalization for reports and raw search results."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from models.schemas import SourceRecord


_TRACKING_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
}
_NEWS_DOMAINS = {
    "reuters.com",
    "bloomberg.com",
    "ft.com",
    "wsj.com",
    "forbes.com",
    "zawya.com",
    "arabianbusiness.com",
    "argaam.com",
    "businesswire.com",
    "prnewswire.com",
}


def normalize_url(value: str) -> tuple[str, str] | None:
    """Return a safe display URL and a stable deduplication key."""
    original = str(value or "").strip()
    try:
        parsed = urlsplit(original)
    except ValueError:
        return None
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
        return None
    host = parsed.hostname.lower().removeprefix("www.")
    try:
        port = f":{parsed.port}" if parsed.port else ""
    except ValueError:
        return None
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    query = [
        (key, val)
        for key, val in parse_qsl(parsed.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in _TRACKING_KEYS
    ]
    normalized = urlunsplit((parsed.scheme.lower(), host + port, path, urlencode(query), ""))
    dedupe_key = urlunsplit(("", host + port, path, urlencode(query), ""))
    return normalized, dedupe_key


def classify_source(url: str, domain: str) -> str:
    lower_url = url.lower()
    if domain == "linkedin.com" or domain.endswith(".linkedin.com"):
        return "LinkedIn"
    if domain.endswith(".gov") or ".gov." in domain:
        return "Government"
    if domain.endswith(".edu") or ".edu." in domain:
        return "Research"
    if any(domain == item or domain.endswith("." + item) for item in _NEWS_DOMAINS):
        return "News"
    if lower_url.endswith(".pdf") or "annual-report" in lower_url or "annual_report" in lower_url:
        return "Financial Report"
    return "Other"


def source_from_search_result(
    item: dict[str, Any],
    selected_urls: Iterable[str] = (),
    retrieved_at: str | None = None,
) -> SourceRecord | None:
    original_url = item.get("link") or item.get("url") or ""
    normalized = normalize_url(original_url)
    if not normalized:
        return None
    url, key = normalized
    selected_keys = {
        candidate[1]
        for value in selected_urls
        if (candidate := normalize_url(value)) is not None
    }
    domain = urlsplit(url).hostname or ""
    title = str(item.get("title") or "").strip() or None
    publisher = domain.removeprefix("www.") or None
    return SourceRecord(
        id=hashlib.sha256(key.encode()).hexdigest()[:16],
        title=title,
        url=url,
        original_url=original_url if original_url != url else None,
        domain=domain,
        publisher=publisher,
        author=item.get("author"),
        snippet=str(item.get("snippet") or "").strip() or None,
        extracted_text=item.get("extracted_text"),
        published_at=item.get("published_at") or item.get("date"),
        retrieved_at=retrieved_at or datetime.now(timezone.utc).isoformat(),
        source_type=classify_source(url, domain),
        search_query=item.get("search_query"),
        rank=item.get("rank"),
        relevance_score=item.get("relevance_score"),
        extraction_status="extracted" if key in selected_keys else "search_only",
        evidence=[str(value) for value in item.get("evidence", []) if value],
    )


def build_source_records(
    search_results: Iterable[dict[str, Any]],
    selected_urls: Iterable[str],
) -> list[SourceRecord]:
    records: list[SourceRecord] = []
    seen: set[str] = set()
    retrieved_at = datetime.now(timezone.utc).isoformat()
    for item in search_results:
        record = source_from_search_result(item, selected_urls, retrieved_at)
        if record and record.id not in seen:
            records.append(record)
            seen.add(record.id)
    return records


def report_sources(intelligence: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize enriched and legacy report sources into one dashboard view model."""
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in intelligence.get("search_results") or []:
        record = source_from_search_result(
            {
                **item,
                "link": item.get("url"),
                "title": item.get("title"),
                "snippet": item.get("snippet"),
            },
            [item.get("url")] if item.get("extraction_status") == "extracted" else [],
            item.get("retrieved_at"),
        )
        if not record:
            continue
        data = {**record.model_dump(), **{key: value for key, value in item.items() if value is not None}}
        data["url"] = record.url
        data["domain"] = record.domain
        data["source_type"] = item.get("source_type") or record.source_type
        data["extraction_status"] = item.get("extraction_status") or record.extraction_status
        if record.id not in seen:
            output.append(data)
            seen.add(record.id)

    for item in intelligence.get("evidence_links") or []:
        normalized = normalize_url(item.get("url", ""))
        if not normalized:
            continue
        url, key = normalized
        source_id = hashlib.sha256(key.encode()).hexdigest()[:16]
        if source_id in seen:
            for source in output:
                if source["id"] == source_id and item.get("description") and not source.get("evidence"):
                    source["evidence"] = [item["description"]]
            continue
        domain = urlsplit(url).hostname or ""
        output.append(
            {
                "id": source_id,
                "title": item.get("description") or domain,
                "url": url,
                "original_url": item.get("url") if item.get("url") != url else None,
                "domain": domain,
                "publisher": domain,
                "author": None,
                "snippet": None,
                "extracted_text": None,
                "published_at": None,
                "retrieved_at": None,
                "source_type": classify_source(url, domain),
                "search_query": None,
                "rank": None,
                "relevance_score": None,
                "extraction_status": "evidence",
                "evidence": [item["description"]] if item.get("description") else [],
            }
        )
        seen.add(source_id)
    return output
