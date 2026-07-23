"""Professional, canonical-data PDF rendering for intelligence reports."""

from __future__ import annotations

import io
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


GREEN = colors.HexColor("#176B52")
DARK = colors.HexColor("#17201C")
MUTED = colors.HexColor("#69736D")
LINE = colors.HexColor("#DCE1DA")
SOFT = colors.HexColor("#EEF1EB")


def _register_fonts() -> tuple[str, str, bool]:
    candidates = [
        (
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("C:/Windows/Fonts/arialbd.ttf"),
        ),
        (
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ),
    ]
    for regular, bold in candidates:
        if regular.exists() and bold.exists():
            pdfmetrics.registerFont(TTFont("RadarSans", str(regular)))
            pdfmetrics.registerFont(TTFont("RadarSans-Bold", str(bold)))
            return "RadarSans", "RadarSans-Bold", True
    return "Helvetica", "Helvetica-Bold", False


FONT_REGULAR, FONT_BOLD, UNICODE_FONT = _register_fonts()


def _text(value: Any) -> str:
    raw = str(value or "").replace("\u2011", "-").replace("\u2013", "-").replace("\u2014", "-")
    return raw if UNICODE_FONT else raw.encode("latin-1", "replace").decode("latin-1")


def _paragraph(value: Any, style, link: str | None = None) -> Paragraph:
    content = escape(_text(value))
    if link:
        content = f'<link href="{escape(link, quote=True)}" color="#176B52">{content}</link>'
    return Paragraph(content or "Not available", style)


def _footer(canvas, doc) -> None:
    canvas.saveState()
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 14 * mm, 192 * mm, 14 * mm)
    canvas.setFont(FONT_REGULAR, 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 9 * mm, "Account Intelligence Radar - Confidential")
    canvas.drawRightString(192 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


def render_report_pdf(payload: dict[str, Any]) -> bytes:
    """Render the same report payload used by the interactive dashboard."""
    buffer = io.BytesIO()
    company = payload.get("company_name") or "Intelligence Report"
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title=f"Account Intelligence Report - {company}",
        author="Account Intelligence Radar",
    )
    base = getSampleStyleSheet()
    styles = {
        "cover": ParagraphStyle(
            "Cover",
            parent=base["Title"],
            fontName=FONT_BOLD,
            fontSize=28,
            leading=32,
            textColor=DARK,
            spaceAfter=10,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle",
            parent=base["Normal"],
            fontSize=11,
            leading=16,
            textColor=MUTED,
        ),
        "h1": ParagraphStyle(
            "H1",
            parent=base["Heading1"],
            fontName=FONT_BOLD,
            fontSize=18,
            leading=22,
            textColor=DARK,
            spaceBefore=14,
            spaceAfter=9,
        ),
        "h2": ParagraphStyle(
            "H2",
            parent=base["Heading2"],
            fontName=FONT_BOLD,
            fontSize=12,
            leading=15,
            textColor=GREEN,
            spaceBefore=9,
            spaceAfter=5,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=base["BodyText"],
            fontSize=9.4,
            leading=14,
            textColor=DARK,
            spaceAfter=5,
        ),
        "small": ParagraphStyle(
            "Small",
            parent=base["BodyText"],
            fontSize=7.8,
            leading=10.5,
            textColor=MUTED,
        ),
        "table": ParagraphStyle(
            "Table",
            parent=base["BodyText"],
            fontSize=7.7,
            leading=10,
            textColor=DARK,
        ),
        "table_header": ParagraphStyle(
            "TableHeader",
            parent=base["BodyText"],
            fontName=FONT_BOLD,
            fontSize=7.7,
            leading=10,
            textColor=colors.white,
        ),
        "brand": ParagraphStyle(
            "Brand",
            parent=base["Normal"],
            fontName=FONT_BOLD,
            fontSize=9,
            leading=12,
            textColor=GREEN,
            spaceAfter=24,
        ),
    }
    story = [
        Paragraph("ACCOUNT INTELLIGENCE RADAR", styles["brand"]),
        _paragraph(company, styles["cover"]),
        Paragraph("Evidence-backed intelligence report", styles["subtitle"]),
        Spacer(1, 16 * mm),
    ]

    info = payload.get("search_information") or {}
    cover_rows = [
        ("Search type", payload.get("mode", "").title()),
        ("Search query", payload.get("query")),
        ("Objective", info.get("objective")),
        ("Report ID", payload.get("id")),
        ("Search date", payload.get("created_at")),
        ("Generated", datetime.now(timezone.utc).isoformat()),
    ]
    cover_table = Table(
        [
            [_paragraph(label, styles["small"]), _paragraph(value, styles["body"])]
            for label, value in cover_rows
            if value
        ],
        colWidths=[35 * mm, 125 * mm],
    )
    cover_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), SOFT),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.extend([cover_table, PageBreak()])

    summary = payload.get("summary") or {}
    story.extend([Paragraph("Executive Summary", styles["h1"])])
    if summary.get("high_level"):
        story.append(_paragraph(summary["high_level"], styles["body"]))
    for finding in summary.get("major_findings") or []:
        story.append(_paragraph(f"- {finding}", styles["body"]))

    story.append(Paragraph("Search Information", styles["h1"]))
    search_rows = [
        ("Company", payload.get("company_name")),
        ("Headquarters", (payload.get("intelligence") or {}).get("headquarters")),
        ("Search type", payload.get("mode", "").title()),
        ("Query", payload.get("query")),
        ("Objective", info.get("objective")),
        ("Location", info.get("location")),
        ("Target criteria", info.get("target_criteria")),
        ("Sources", payload.get("source_count")),
        ("Status", payload.get("status", "completed").title()),
    ]
    data = [[_paragraph("Field", styles["table_header"]), _paragraph("Value", styles["table_header"])]]
    data += [
        [_paragraph(label, styles["table"]), _paragraph(value, styles["table"])]
        for label, value in search_rows
        if value not in (None, "", [])
    ]
    table = Table(data, colWidths=[40 * mm, 120 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.append(table)

    intelligence = payload.get("intelligence") or {}
    story.append(Paragraph("Business Snapshot", styles["h1"]))
    for label, field in (
        ("Business Units", "business_units"),
        ("Products and Services", "products_and_services"),
        ("Target Industries", "target_industries"),
    ):
        values = intelligence.get(field) or []
        if values:
            story.append(Paragraph(label, styles["h2"]))
            for value in values:
                story.append(_paragraph(f"- {value}", styles["body"]))

    leadership = intelligence.get("leadership") or []
    if leadership:
        story.append(Paragraph("Leadership", styles["h1"]))
        data = [[_paragraph("Name", styles["table_header"]), _paragraph("Position", styles["table_header"]), _paragraph("Source", styles["table_header"])]]
        for item in leadership:
            source_url = item.get("source_url")
            data.append(
                [
                    _paragraph(item.get("name"), styles["table"]),
                    _paragraph(item.get("title"), styles["table"]),
                    _paragraph(source_url or "Not attributed", styles["table"], source_url),
                ]
            )
        table = Table(data, colWidths=[45 * mm, 65 * mm, 50 * mm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), GREEN),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.35, LINE),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(table)

    initiatives = intelligence.get("strategic_initiatives") or []
    if initiatives:
        story.append(Paragraph("Strategic Intelligence", styles["h1"]))
        for item in initiatives:
            block = [
                Paragraph(_text(item.get("category") or "Strategic Initiative"), styles["h2"]),
                _paragraph(item.get("description"), styles["body"]),
            ]
            if item.get("source_url"):
                block.append(_paragraph(item["source_url"], styles["small"], item["source_url"]))
            story.append(KeepTogether(block))

    comparison = payload.get("comparison")
    if comparison:
        meaningful = [
            item
            for item in comparison.get("changes") or []
            if item.get("status") != "unchanged"
        ]
        if meaningful:
            story.append(Paragraph("Changes Since Previous Scan", styles["h1"]))
            for item in meaningful:
                description = item.get("after") or item.get("before")
                story.append(
                    _paragraph(
                        f"{item.get('status', '').upper()} - {item.get('label')}: {description}",
                        styles["body"],
                    )
                )

    sources = payload.get("sources") or []
    if sources:
        story.append(Paragraph("Sources and Evidence", styles["h1"]))
        story.append(
            _paragraph(
                f"{len(sources)} unique source{'s' if len(sources) != 1 else ''} retained for this report.",
                styles["subtitle"],
            )
        )
        for index, source in enumerate(sources, 1):
            title = source.get("title") or source.get("domain") or f"Source {index}"
            block = [
                Paragraph(f"[{index}] {escape(_text(title))}", styles["h2"]),
                _paragraph(source.get("url"), styles["small"], source.get("url")),
            ]
            metadata = " | ".join(
                str(value)
                for value in (
                    source.get("publisher"),
                    source.get("source_type"),
                    source.get("published_at"),
                    source.get("extraction_status"),
                )
                if value
            )
            if metadata:
                block.append(_paragraph(metadata, styles["small"]))
            if source.get("snippet"):
                block.append(_paragraph(source["snippet"], styles["body"]))
            for evidence in source.get("evidence") or []:
                block.append(_paragraph(f"Evidence: {evidence}", styles["body"]))
            block.append(Spacer(1, 3 * mm))
            story.append(KeepTogether(block))

    search_results = payload.get("search_results") or []
    if search_results:
        story.append(PageBreak())
        story.append(Paragraph("Search Results Appendix", styles["h1"]))
        for index, result in enumerate(search_results, 1):
            block = [
                Paragraph(
                    f"{index}. {escape(_text(result.get('title') or result.get('domain') or 'Search result'))}",
                    styles["h2"],
                ),
                _paragraph(result.get("url"), styles["small"], result.get("url")),
            ]
            if result.get("search_query"):
                block.append(_paragraph(f"Query: {result['search_query']}", styles["small"]))
            if result.get("snippet"):
                block.append(_paragraph(result["snippet"], styles["body"]))
            block.append(Spacer(1, 2 * mm))
            story.append(KeepTogether(block))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
