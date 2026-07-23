"""Password hashing and opaque server-side session management."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Cookie, HTTPException, status

from services.database import connect


SESSION_COOKIE = "air_session"
SESSION_DAYS = int(os.getenv("SESSION_DAYS", "14"))
PBKDF2_ITERATIONS = 310_000


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        PBKDF2_ITERATIONS,
        base64.urlsafe_b64encode(salt).decode(),
        base64.urlsafe_b64encode(derived).decode(),
    )


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_text, digest_text = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_text)
        expected = base64.urlsafe_b64decode(digest_text)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def public_user(row) -> dict:
    return {"id": row["id"], "name": row["name"], "email": row["email"]}


def create_user(name: str, email: str, password: str) -> dict:
    now = _iso(_now())
    user_id = str(uuid.uuid4())
    try:
        with connect() as db:
            db.execute(
                "INSERT INTO users(id, name, email, password_hash, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, name.strip(), email.strip().lower(), hash_password(password), now, now),
            )
            row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return public_user(row)
    except Exception as exc:
        if "UNIQUE constraint failed" in str(exc):
            raise ValueError("An account with this email already exists.") from exc
        raise


def authenticate(email: str, password: str) -> Optional[dict]:
    with connect() as db:
        row = db.execute(
            "SELECT * FROM users WHERE email = ? COLLATE NOCASE", (email.strip(),)
        ).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        return None
    return public_user(row)


def create_session(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    now = _now()
    with connect() as db:
        db.execute("DELETE FROM sessions WHERE expires_at <= ?", (_iso(now),))
        db.execute(
            "INSERT INTO sessions(id, user_id, token_hash, expires_at, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                user_id,
                token_hash,
                _iso(now + timedelta(days=SESSION_DAYS)),
                _iso(now),
            ),
        )
    return token


def delete_session(token: Optional[str]) -> None:
    if not token:
        return
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with connect() as db:
        db.execute("DELETE FROM sessions WHERE token_hash = ?", (token_hash,))


def user_for_session(token: Optional[str]) -> Optional[dict]:
    if not token:
        return None
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with connect() as db:
        row = db.execute(
            """
            SELECT users.id, users.name, users.email
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token_hash = ? AND sessions.expires_at > ?
            """,
            (token_hash, _iso(_now())),
        ).fetchone()
    return public_user(row) if row else None


def require_user(air_session: Optional[str] = Cookie(default=None)) -> dict:
    user = user_for_session(air_session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please sign in to continue.",
        )
    return user

