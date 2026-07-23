"""Durable SQLite-backed scan store."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from models.schemas import CompanyReport, InputMode, JobResponse, JobStatus
from services.database import connect


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_job(
    mode: InputMode,
    user_id: str,
    query: str,
    request_data: dict,
) -> JobResponse:
    job_id = str(uuid.uuid4())
    now = _now()
    with connect() as db:
        db.execute(
            """
            INSERT INTO jobs(
                id, user_id, mode, query, request_json, status, stage, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_id,
                user_id,
                mode.value,
                query,
                json.dumps(request_data),
                JobStatus.PENDING.value,
                "Queued",
                now,
                now,
            ),
        )
    return get_job(job_id, user_id)


def get_job(job_id: str, user_id: Optional[str] = None) -> Optional[JobResponse]:
    sql = "SELECT * FROM jobs WHERE id = ?"
    params: tuple = (job_id,)
    if user_id:
        sql += " AND user_id = ?"
        params += (user_id,)
    with connect() as db:
        row = db.execute(sql, params).fetchone()
        if not row:
            return None
        report_rows = db.execute(
            "SELECT id, source_count FROM reports WHERE job_id = ? ORDER BY created_at", (job_id,)
        ).fetchall()
        comparison = db.execute(
            """
            SELECT comparisons.id, previous.created_at AS previous_scan_date
            FROM comparisons
            JOIN reports current ON current.id = comparisons.current_report_id
            JOIN reports previous ON previous.id = comparisons.previous_report_id
            WHERE current.job_id = ?
            ORDER BY comparisons.created_at DESC LIMIT 1
            """,
            (job_id,),
        ).fetchone()
    result = None
    if row["result_json"]:
        result = [CompanyReport.model_validate(item) for item in json.loads(row["result_json"])]
    return JobResponse(
        job_id=row["id"],
        status=JobStatus(row["status"]),
        mode=InputMode(row["mode"]),
        query=row["query"],
        stage=row["stage"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        result=result,
        error=row["error"],
        report_paths=json.loads(row["report_paths_json"]) if row["report_paths_json"] else None,
        source_count=sum(item["source_count"] for item in report_rows),
        report_ids=[item["id"] for item in report_rows],
        comparison_id=comparison["id"] if comparison else None,
        previous_scan_date=comparison["previous_scan_date"] if comparison else None,
    )


def get_request(job_id: str, user_id: Optional[str] = None) -> Optional[dict]:
    sql = "SELECT request_json FROM jobs WHERE id = ?"
    params: tuple = (job_id,)
    if user_id:
        sql += " AND user_id = ?"
        params += (user_id,)
    with connect() as db:
        row = db.execute(sql, params).fetchone()
    return json.loads(row["request_json"]) if row else None


def update_job(job: JobResponse) -> None:
    with connect() as db:
        db.execute(
            """
            UPDATE jobs SET status = ?, stage = ?, result_json = ?, error = ?,
                report_paths_json = ?, updated_at = ? WHERE id = ?
            """,
            (
                job.status.value,
                job.stage,
                json.dumps([item.model_dump() for item in job.result]) if job.result else None,
                job.error,
                json.dumps(job.report_paths) if job.report_paths else None,
                _now(),
                job.job_id,
            ),
        )


def set_stage(job_id: str, stage: str) -> None:
    with connect() as db:
        db.execute(
            "UPDATE jobs SET stage = ?, updated_at = ? WHERE id = ?",
            (stage, _now(), job_id),
        )


def list_jobs(
    user_id: str,
    search: str = "",
    mode: Optional[str] = None,
    status: Optional[str] = None,
) -> list[dict]:
    clauses = ["user_id = ?"]
    params: list = [user_id]
    if search:
        clauses.append("query LIKE ?")
        params.append(f"%{search}%")
    if mode:
        clauses.append("mode = ?")
        params.append(mode)
    if status:
        clauses.append("status = ?")
        params.append(status)
    with connect() as db:
        rows = db.execute(
            f"""
            SELECT jobs.*,
                (SELECT COALESCE(SUM(source_count), 0) FROM reports WHERE job_id = jobs.id)
                    AS source_count,
                (SELECT COUNT(*) FROM comparisons c
                    JOIN reports r ON r.id = c.current_report_id WHERE r.job_id = jobs.id)
                    AS change_count
            FROM jobs WHERE {' AND '.join(clauses)}
            ORDER BY created_at DESC
            """,
            params,
        ).fetchall()
    return [
        {
            "id": row["id"],
            "query": row["query"],
            "mode": row["mode"],
            "status": row["status"],
            "stage": row["stage"],
            "source_count": row["source_count"],
            "has_comparison": bool(row["change_count"]),
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        for row in rows
    ]


def delete_job(job_id: str, user_id: str) -> bool:
    with connect() as db:
        cursor = db.execute("DELETE FROM jobs WHERE id = ? AND user_id = ?", (job_id, user_id))
    return cursor.rowcount > 0
