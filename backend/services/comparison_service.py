"""Semantic-ish normalization and field-aware intelligence change detection."""

from __future__ import annotations

import json
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from typing import Any

from services.database import connect
from services.source_service import report_sources


_ALIASES = {
    "artificial intelligence": "ai",
    "chief executive officer": "ceo",
    "chief financial officer": "cfo",
    "digitalisation": "digital transformation",
    "digitization": "digital transformation",
    "programme": "program",
}


def normalize_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    text = text.casefold()
    for original, replacement in _ALIASES.items():
        text = text.replace(original, replacement)
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _similar(left: str, right: str) -> bool:
    a, b = normalize_text(left), normalize_text(right)
    if a == b:
        return True
    if not a or not b:
        return False
    a_tokens, b_tokens = set(a.split()), set(b.split())
    overlap = len(a_tokens & b_tokens) / max(len(a_tokens | b_tokens), 1)
    return overlap >= 0.72 or SequenceMatcher(None, a, b).ratio() >= 0.84


def _label(field: str) -> str:
    return field.replace("_", " ").replace("products and services", "product or service").title()


def _as_items(field: str, value: Any) -> list[dict]:
    if not value:
        return []
    if field == "leadership":
        return [
            {"key": normalize_text(item.get("name")), "text": f"{item.get('name')} — {item.get('title')}"}
            for item in value if isinstance(item, dict) and item.get("name")
        ]
    if field == "strategic_initiatives":
        return [
            {
                "key": normalize_text(item.get("description")),
                "text": item.get("description"),
                "category": item.get("category"),
            }
            for item in value if isinstance(item, dict) and item.get("description")
        ]
    if field == "evidence_links":
        return [
            {"key": normalize_text(item.get("url")), "text": item.get("url")}
            for item in value if isinstance(item, dict) and item.get("url")
        ]
    return [{"key": normalize_text(item), "text": str(item)} for item in value]


def compare_reports(previous: dict, current: dict) -> dict:
    changes: list[dict] = []
    scalar_fields = ("headquarters",)
    list_fields = (
        "business_units",
        "products_and_services",
        "target_industries",
        "leadership",
        "strategic_initiatives",
        "evidence_links",
    )

    for field in scalar_fields:
        old, new = previous.get(field), current.get(field)
        if old and new and not _similar(old, new):
            changes.append(
                {"status": "changed", "field": field, "label": _label(field), "before": old, "after": new}
            )
        elif new and not old:
            changes.append({"status": "new", "field": field, "label": _label(field), "after": new})
        elif old and not new:
            changes.append({"status": "removed", "field": field, "label": _label(field), "before": old})
        elif old and new:
            changes.append({"status": "unchanged", "field": field, "label": _label(field), "after": new})

    for field in list_fields:
        old_items = _as_items(field, previous.get(field))
        new_items = _as_items(field, current.get(field))
        used_new: set[int] = set()
        for old in old_items:
            matched = next(
                (index for index, new in enumerate(new_items) if index not in used_new and _similar(old["key"], new["key"])),
                None,
            )
            if matched is None:
                changes.append({"status": "removed", "field": field, "label": _label(field), "before": old["text"]})
                continue
            used_new.add(matched)
            new = new_items[matched]
            if field == "leadership" and not _similar(old["text"], new["text"]):
                changes.append(
                    {"status": "changed", "field": field, "label": "Leadership", "before": old["text"], "after": new["text"]}
                )
            else:
                changes.append({"status": "unchanged", "field": field, "label": _label(field), "after": new["text"]})
        for index, new in enumerate(new_items):
            if index not in used_new:
                changes.append({"status": "new", "field": field, "label": _label(field), "after": new["text"]})

    counts = {status: sum(item["status"] == status for item in changes) for status in ("new", "changed", "removed", "unchanged")}
    return {"counts": counts, "changes": changes}


def persist_report_and_comparison(
    job_id: str,
    user_id: str,
    report: dict,
    markdown: str,
) -> tuple[str, str | None]:
    company_name = report.get("company_name", "Unknown company")
    slug = re.sub(r"[^a-z0-9]+", "-", normalize_text(company_name)).strip("-")
    report_id = str(uuid.uuid4())
    comparison_id = None
    now = datetime.now(timezone.utc).isoformat()
    with connect() as db:
        previous = db.execute(
            """
            SELECT * FROM reports
            WHERE user_id = ? AND company_slug = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (user_id, slug),
        ).fetchone()
        db.execute(
            """
            INSERT INTO reports(
                id, job_id, user_id, company_slug, company_name, intelligence_json,
                markdown, source_count, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                report_id,
                job_id,
                user_id,
                slug,
                company_name,
                json.dumps(report),
                markdown,
                len(report_sources(report)),
                now,
            ),
        )
        if previous:
            comparison_id = str(uuid.uuid4())
            comparison = compare_reports(json.loads(previous["intelligence_json"]), report)
            db.execute(
                """
                INSERT INTO comparisons(
                    id, user_id, previous_report_id, current_report_id,
                    comparison_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    comparison_id,
                    user_id,
                    previous["id"],
                    report_id,
                    json.dumps(comparison),
                    now,
                ),
            )
    return report_id, comparison_id
