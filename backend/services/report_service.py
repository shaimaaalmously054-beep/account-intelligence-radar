"""
Report builder — assembles CompanyReport from raw extraction data
and persists JSON + Markdown to /reports folder.
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, List

from models.schemas import (
    CompanyReport,
    EvidenceLink,
    ExecutiveSignal,
    StrategicInitiative,
)

logger = logging.getLogger(__name__)

REPORTS_DIR = "reports"


def build_report(raw: Dict[str, Any], company_name: str) -> CompanyReport:
    """Convert raw Firecrawl extraction dict into a typed CompanyReport."""
    source_urls: List[str] = raw.get("_source_urls", [])

    # Leadership — only from official sources
    leadership = []
    for exec_item in raw.get("leadership", []):
        if isinstance(exec_item, dict):
            name = exec_item.get("name", "").strip()
            title = exec_item.get("title", "").strip()
            if name and title:
                leadership.append(ExecutiveSignal(name=name, title=title))

    # Strategic initiatives
    initiatives = []
    for item in raw.get("strategic_initiatives", []):
        if isinstance(item, dict):
            desc = item.get("description", "").strip()
            category = item.get("category", "").strip() or None
            if desc:
                initiatives.append(
                    StrategicInitiative(description=desc, category=category)
                )
        elif isinstance(item, str) and item.strip():
            initiatives.append(StrategicInitiative(description=item.strip()))

    # Evidence links
    evidence = [EvidenceLink(url=u) for u in source_urls if u.startswith("http")]

    # LinkedIn manual search suggestion (never automated)
    linkedin_suggestion = (
        f'site:linkedin.com/company "{company_name}" OR '
        f'site:linkedin.com/in "{company_name}"'
    )

    report = CompanyReport(
        company_name=raw.get("company_name") or company_name,
        headquarters=raw.get("headquarters") or None,
        business_units=_safe_list(raw.get("business_units")),
        products_and_services=_safe_list(raw.get("products_and_services")),
        target_industries=_safe_list(raw.get("target_industries")),
        leadership=leadership,
        strategic_initiatives=initiatives,
        evidence_links=evidence,
        raw_extraction=raw,
        linkedin_search_suggestion=linkedin_suggestion,
    )
    return report


def save_report(report: CompanyReport, job_id: str) -> Dict[str, str]:
    """Persist report to /reports/<company_name>/ as JSON and Markdown."""
    safe_name = re.sub(r"[^\w\-]", "_", report.company_name.strip().lower())
    safe_name = re.sub(r"_+", "_", safe_name).strip("_")
    folder    = os.path.join(REPORTS_DIR, safe_name)
    os.makedirs(folder, exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M")
    json_path = os.path.join(folder, f"{safe_name}_{timestamp}.json")
    md_path   = os.path.join(folder, f"{safe_name}_{timestamp}.md")

    # JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(exclude={"raw_extraction"}), f, indent=2, ensure_ascii=False)

    # Markdown
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(_to_markdown(report))

    logger.info("Report saved: %s | %s", json_path, md_path)
    return {"json": json_path, "markdown": md_path}


def _to_markdown(r: CompanyReport) -> str:
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        f"# Account Intelligence Report: {r.company_name}",
        f"*Generated: {ts}*",
        "",
        "---",
        "",
        "## 1. Company Identifiers",
        f"- **Name:** {r.company_name}",
        f"- **Headquarters:** {r.headquarters or 'Not found'}",
        "",
        "## 2. Business Snapshot",
    ]

    if r.business_units:
        lines += ["### Business Units"] + [f"- {u}" for u in r.business_units]
    if r.products_and_services:
        lines += ["", "### Products & Services"] + [f"- {p}" for p in r.products_and_services]
    if r.target_industries:
        lines += ["", "### Target Industries"] + [f"- {i}" for i in r.target_industries]

    lines += ["", "## 3. Leadership Signals"]
    if r.leadership:
        for exec_ in r.leadership:
            lines.append(f"- **{exec_.name}** — {exec_.title}")
    else:
        lines.append("*No publicly verifiable leadership data found.*")

    lines += ["", "## 4. Strategic Initiatives"]
    if r.strategic_initiatives:
        for init in r.strategic_initiatives:
            cat = f" *(#{init.category})*" if init.category else ""
            lines.append(f"- {init.description}{cat}")
    else:
        lines.append("*No strategic initiatives found.*")

    lines += ["", "## 5. Evidence Links"]
    if r.evidence_links:
        for ev in r.evidence_links:
            desc = f" — {ev.description}" if ev.description else ""
            lines.append(f"- [{ev.url}]({ev.url}){desc}")
    else:
        lines.append("*No evidence links available.*")

    lines += [
        "",
        "## 6. LinkedIn Outreach (Manual)",
        "> ⚠️ LinkedIn automation is prohibited. Use the query below manually in your browser.",
        f"```",
        r.linkedin_search_suggestion or "",
        "```",
        "",
        "---",
        "*Report generated by Account Intelligence Radar — Averroa*",
    ]

    return "\n".join(lines)


def _safe_list(val: Any) -> List[str]:
    if isinstance(val, list):
        return [str(v).strip() for v in val if v]
    return []
