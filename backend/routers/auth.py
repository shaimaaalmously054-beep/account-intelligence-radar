"""Authentication API."""

from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from models.schemas import AuthRequest, RegisterRequest, UserResponse
from services.auth_service import (
    SESSION_COOKIE,
    authenticate,
    create_session,
    create_user,
    delete_session,
    require_user,
)


router = APIRouter()


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=14 * 24 * 60 * 60,
        httponly=True,
        secure=os.getenv("COOKIE_SECURE", "false").lower() == "true",
        samesite="lax",
        path="/",
    )


@router.post("/register", response_model=UserResponse, status_code=201)
def register(body: RegisterRequest, response: Response):
    try:
        user = create_user(body.name, body.email, body.password)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    _set_session_cookie(response, create_session(user["id"]))
    return user


@router.post("/login", response_model=UserResponse)
def login(body: AuthRequest, response: Response):
    user = authenticate(body.email, body.password)
    if not user:
        raise HTTPException(401, "Email or password is incorrect.")
    _set_session_cookie(response, create_session(user["id"]))
    return user


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response):
    delete_session(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=UserResponse)
def me(user: dict = Depends(require_user)):
    return user

