"""
Simple in-memory job store.
For production, replace with Redis or a database.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Optional
import uuid

from models.schemas import JobResponse, JobStatus, InputMode


_store: Dict[str, JobResponse] = {}


def create_job(mode: InputMode) -> JobResponse:
    job_id = str(uuid.uuid4())
    now = _now()
    job = JobResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        mode=mode,
        created_at=now,
        updated_at=now,
    )
    _store[job_id] = job
    return job


def get_job(job_id: str) -> Optional[JobResponse]:
    return _store.get(job_id)


def update_job(job: JobResponse) -> None:
    job.updated_at = _now()
    _store[job.job_id] = job


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
