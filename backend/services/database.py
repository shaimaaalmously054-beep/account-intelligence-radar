"""SQLite persistence for users, sessions, scans, reports, and comparisons."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


_BACKEND_DIR = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("RADAR_DB_PATH", _BACKEND_DIR / "data" / "radar.db"))


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                token_hash TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                mode TEXT NOT NULL,
                query TEXT NOT NULL,
                request_json TEXT NOT NULL,
                status TEXT NOT NULL,
                stage TEXT,
                result_json TEXT,
                error TEXT,
                report_paths_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reports (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                company_slug TEXT NOT NULL,
                company_name TEXT NOT NULL,
                intelligence_json TEXT NOT NULL,
                markdown TEXT NOT NULL,
                source_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS comparisons (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                previous_report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
                current_report_id TEXT NOT NULL REFERENCES reports(id) ON DELETE CASCADE,
                comparison_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS jobs_user_created_idx
                ON jobs(user_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS reports_user_company_idx
                ON reports(user_id, company_slug, created_at DESC);
            CREATE INDEX IF NOT EXISTS comparisons_current_idx
                ON comparisons(current_report_id);
            """
        )
