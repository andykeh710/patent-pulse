"""Sprint 6 — Magic-link auth endpoints."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import APIRouter, Cookie, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select

from app.api.deps import get_db
from app.auth.magic_link import create_token_for_email, verify_token
from app.config import settings
from app.core.ai_models import User
from app.middleware.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter()

SESSION_COOKIE_NAME = "auth_session"
SESSION_TTL_DAYS = 30


# ── schemas ──────────────────────────────────────────────────────────


class RequestLinkBody(BaseModel):
    email: str


class UserResponse(BaseModel):
    id: str
    email: str | None = None
    display_name: str | None = None


# ── helpers ──────────────────────────────────────────────────────────


def _issue_session_jwt(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": user_id,
            "iat": now,
            "exp": now + timedelta(days=SESSION_TTL_DAYS),
        },
        settings.auth_secret_key,
        algorithm="HS256",
    )


def _set_session_cookie(response: JSONResponse | RedirectResponse, user_id: str) -> None:
    """Attach a 30-day HttpOnly session cookie."""
    token = _issue_session_jwt(user_id)
    secure = settings.environment == "production"
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=secure,
        samesite="lax",
        max_age=60 * 60 * 24 * SESSION_TTL_DAYS,
        path="/",
    )


async def _get_or_create_user(session, email: str) -> User:
    """Find or create a user by email, returning the User row."""
    result = await session.execute(
        select(User).where(User.email == email.strip().lower())
    )
    user = result.scalar_one_or_none()
    if not user:
        user = User(
            email=email.strip().lower(),
            # User.id is auto-generated (VARCHAR from the users table).
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


# ── endpoints ────────────────────────────────────────────────────────


@router.post("/request-link")
async def request_link(
    body: RequestLinkBody,
    request: Request,
    session=Depends(get_db),
):
    """Request a magic-link email. Always returns 202."""
    email = body.email.strip().lower() if body.email else ""

    # Always respond 202 to avoid user-enumeration disclosure.
    if not email or "@" not in email:
        return JSONResponse(status_code=202, content={"ok": True})

    try:
        user = await _get_or_create_user(session, email)
        raw_token, _ = await create_token_for_email(session, user.id, email)

        magic_link = f"{settings.magic_link_base_url}/login/verify?token={raw_token}"

        # Dev mode: log the magic link so the developer can test.
        if settings.email_send_mode == "dev" or settings.environment != "production":
            logger.info("🔑 Magic link for %s: %s", email, magic_link)

        # FUTURE (S6-5): send via Resend.
        # For now, devs use the logged link.

    except Exception as e:
        logger.error("Magic-link request failed for %s: %s", email, e)
        # Still return 202 — don't expose errors.

    return JSONResponse(status_code=202, content={"ok": True})


@router.get("/verify")
@limiter.exempt
async def verify(
    token: str,
    session=Depends(get_db),
):
    """Verify a magic-link token and set a session cookie."""
    if not token:
        raise HTTPException(status_code=400, detail="Missing token")

    token_row = await verify_token(session, token)
    if not token_row:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    response = RedirectResponse(url="/", status_code=302)
    _set_session_cookie(response, token_row.user_id)
    return response


@router.get("/me", response_model=UserResponse)
async def me(
    auth_session: str = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    session=Depends(get_db),
):
    """Return the current user from the session cookie."""
    if not auth_session:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(
            auth_session, settings.auth_secret_key, algorithms=["HS256"]
        )
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid session")

    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    return UserResponse(
        id=user.id,
        email=user.email,
        display_name=getattr(user, "display_name", None),
    )


@router.post("/logout")
async def logout():
    """Clear the session cookie."""
    response = JSONResponse(content={"ok": True})
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return response
