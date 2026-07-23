"""Report, comparison, and persistent company profile APIs."""

from __future__ import annotations

import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, Response

from services.auth_service import require_user
from services.database import connect
from services.pdf_service import render_report_pdf
from services.source_service import report_sources


router = APIRouter()


def _report_row(report_id: str, user_id: str):
    with connect() as db:
        return db.execute(
            """
            SELECT reports.*, jobs.mode, jobs.query, jobs.request_json, jobs.status,
                jobs.created_at AS scan_created_at, jobs.updated_at AS scan_updated_at
            FROM reports JOIN jobs ON jobs.id = reports.job_id
            WHERE reports.id = ? AND reports.user_id = ?
            """,
            (report_id, user_id),
        ).fetchone()


def _comparison_for_report(report_id: str):
    with connect() as db:
        return db.execute(
            """
            SELECT comparisons.id, comparisons.comparison_json,
                previous.created_at AS previous_scan_date
            FROM comparisons
            JOIN reports previous ON previous.id = comparisons.previous_report_id
            WHERE comparisons.current_report_id = ?
            ORDER BY comparisons.created_at DESC LIMIT 1
            """,
            (report_id,),
        ).fetchone()


def _report_payload(row, comparison=None) -> dict:
    intelligence = json.loads(row["intelligence_json"])
    request_data = json.loads(row["request_json"] or "{}")
    mode_data = request_data.get(row["mode"]) or {}
    sources = report_sources(intelligence)
    findings_count = sum(
        len(intelligence.get(field) or [])
        for field in (
            "business_units",
            "products_and_services",
            "target_industries",
            "leadership",
            "strategic_initiatives",
        )
    )
    major_findings = []
    if intelligence.get("headquarters"):
        major_findings.append(f"Headquarters: {intelligence['headquarters']}")
    major_findings.extend(
        item.get("description")
        for item in (intelligence.get("strategic_initiatives") or [])[:4]
        if item.get("description")
    )
    summary_parts = [f"{row['company_name']} intelligence report"]
    if intelligence.get("headquarters"):
        summary_parts.append(f"headquartered in {intelligence['headquarters']}")
    summary_parts.append(
        f"with {findings_count} structured finding{'s' if findings_count != 1 else ''} "
        f"supported by {len(sources)} retained source{'s' if len(sources) != 1 else ''}"
    )
    comparison_payload = (
        {
            "id": comparison["id"],
            "previous_scan_date": comparison["previous_scan_date"],
            **json.loads(comparison["comparison_json"]),
        }
        if comparison
        else None
    )
    return {
        "id": row["id"],
        "job_id": row["job_id"],
        "company_slug": row["company_slug"],
        "company_name": row["company_name"],
        "mode": row["mode"],
        "query": row["query"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["scan_updated_at"],
        "source_count": len(sources),
        "findings_count": findings_count,
        "intelligence": intelligence,
        "summary": {
            "high_level": "; ".join(summary_parts) + ".",
            "major_findings": major_findings,
        },
        "search_information": {
            "objective": mode_data.get("objective_prompt"),
            "company_name": mode_data.get("company_name"),
            "location": mode_data.get("location"),
            "target_criteria": mode_data.get("target_criteria"),
            "top_n": mode_data.get("top_n"),
        },
        "sources": sources,
        "search_results": [
            source for source in sources if source.get("search_query") or source.get("rank")
        ],
        "comparison": comparison_payload,
    }


@router.get("/reports/{report_id}")
def get_report(report_id: str, user: dict = Depends(require_user)):
    row = _report_row(report_id, user["id"])
    if not row:
        raise HTTPException(404, "Report not found")
    return _report_payload(row, _comparison_for_report(report_id))


@router.get("/reports/{report_id}/export/{fmt}")
def export_report(report_id: str, fmt: str, user: dict = Depends(require_user)):
    row = _report_row(report_id, user["id"])
    if not row:
        raise HTTPException(404, "Report not found")
    if fmt == "json":
        return JSONResponse(
            json.loads(row["intelligence_json"]),
            headers={"Content-Disposition": f'attachment; filename="{row["company_slug"]}.json"'},
        )
    if fmt == "markdown":
        return Response(
            row["markdown"],
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{row["company_slug"]}.md"'},
        )
    if fmt == "pdf":
        try:
            payload = _report_payload(row, _comparison_for_report(report_id))
            content = render_report_pdf(payload)
        except Exception as exc:
            raise HTTPException(500, "We couldn't generate the PDF report. Please try again.") from exc
        date = datetime.fromisoformat(row["created_at"]).strftime("%Y-%m-%d")
        filename = f"account-intelligence-{row['company_slug']}-{date}.pdf"
        return Response(
            content,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    raise HTTPException(400, "Use json, markdown, or pdf.")


@router.get("/comparisons/{comparison_id}")
def get_comparison(comparison_id: str, user: dict = Depends(require_user)):
    with connect() as db:
        row = db.execute(
            "SELECT * FROM comparisons WHERE id = ? AND user_id = ?",
            (comparison_id, user["id"]),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Comparison not found")
    return {"id": row["id"], "created_at": row["created_at"], **json.loads(row["comparison_json"])}


@router.get("/companies")
def list_companies(user: dict = Depends(require_user)):
    with connect() as db:
        rows = db.execute(
            """
            SELECT company_slug, company_name, COUNT(*) AS scan_count,
                MAX(created_at) AS last_scanned, SUM(source_count) AS source_count
            FROM reports WHERE user_id = ?
            GROUP BY company_slug, company_name ORDER BY last_scanned DESC
            """,
            (user["id"],),
        ).fetchall()
    return {"items": [dict(row) for row in rows]}


@router.get("/companies/{company_slug}")
def company_profile(company_slug: str, user: dict = Depends(require_user)):
    with connect() as db:
        reports = db.execute(
            """
            SELECT id, job_id, company_name, intelligence_json, source_count, created_at
            FROM reports WHERE user_id = ? AND company_slug = ?
            ORDER BY created_at DESC
            """,
            (user["id"], company_slug),
        ).fetchall()
        if not reports:
            raise HTTPException(404, "Company profile not found")
        timeline = db.execute(
            """
            SELECT comparisons.id, comparisons.comparison_json, comparisons.created_at
            FROM comparisons JOIN reports ON reports.id = comparisons.current_report_id
            WHERE comparisons.user_id = ? AND reports.company_slug = ?
            ORDER BY comparisons.created_at DESC
            """,
            (user["id"], company_slug),
        ).fetchall()
    current = reports[0]
    return {
        "company_slug": company_slug,
        "company_name": current["company_name"],
        "current_report_id": current["id"],
        "current_intelligence": json.loads(current["intelligence_json"]),
        "scans": [
            {
                "id": row["id"],
                "job_id": row["job_id"],
                "source_count": row["source_count"],
                "created_at": row["created_at"],
            }
            for row in reports
        ],
        "timeline": [
            {"id": row["id"], "created_at": row["created_at"], **json.loads(row["comparison_json"])}
            for row in timeline
        ],
    }
