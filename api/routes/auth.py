"""Auth routes — magic link request, verify, logout, and session check.

All responses are JSON except /verify which redirects (works for both SPA and direct visits).
"""

import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse, RedirectResponse

from api.csrf import CSRF_COOKIE, derive_csrf_token
from api.deps import get_auth_service, get_current_user, is_admin_email
from api.limiter import limiter
from api.schemas import AuthMeResponse, UserInfo
from repositories.user import UserRow
from services.auth import AuthError, AuthService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

_SESSION_COOKIE = "session_token"
_SESSION_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days


def _is_secure() -> bool:
    """Use Secure cookie flag only when not on localhost."""
    base_url = os.environ.get("BASE_URL", "http://localhost:8000")
    return not base_url.startswith("http://localhost")


def _make_user_info(user: UserRow) -> UserInfo:
    """Build a UserInfo response from a UserRow."""
    return UserInfo(id=user.id, email=user.email, is_admin=is_admin_email(user.email))


# ── Session check ────────────────────────────────────────────────────────────

@router.get("/me")
async def auth_me(
    user: Annotated[UserRow, Depends(get_current_user)],
) -> AuthMeResponse:
    """Return the current authenticated user. Used by the React SPA to check auth state."""
    return AuthMeResponse(user=_make_user_info(user))


# ── Magic link ───────────────────────────────────────────────────────────────

@router.post("/magic-link")
@limiter.limit("5/minute")
async def request_magic_link(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> JSONResponse:
    """Accept an email address and send a magic link.

    Expects ``{"email": "..."}`` JSON body, returns ``{"ok": true}``.
    Always returns success — never reveals whether the address exists.
    """
    body = await request.json()
    email = str(body.get("email", "")).strip().lower()
    if not email:
        return JSONResponse({"ok": False, "error": "Email is required"}, status_code=422)
    try:
        await auth_service.request_magic_link(email)
    except AuthError as exc:
        return JSONResponse({"ok": False, "error": str(exc)}, status_code=429)
    return JSONResponse({"ok": True})


# ── Verify ───────────────────────────────────────────────────────────────────

@router.get("/verify")
async def verify_magic_link(
    token: str,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> RedirectResponse:
    """Validate a magic link token, set a session cookie, and redirect to the SPA."""
    try:
        session_token = await auth_service.verify_magic_link(token)
    except AuthError:
        return RedirectResponse(
            url="/?error=invalid_or_expired",
            status_code=302,
        )

    redirect = RedirectResponse(url="/dashboard", status_code=302)
    redirect.set_cookie(
        key=_SESSION_COOKIE,
        value=session_token,
        max_age=_SESSION_TTL_SECONDS,
        httponly=True,
        secure=_is_secure(),
        samesite="lax",
    )
    redirect.set_cookie(
        key=CSRF_COOKIE,
        value=derive_csrf_token(session_token),
        max_age=_SESSION_TTL_SECONDS,
        httponly=False,
        secure=_is_secure(),
        samesite="lax",
    )
    return redirect


# ── Logout ───────────────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> JSONResponse:
    """Invalidate the current session and clear the session cookie."""
    token = request.cookies.get(_SESSION_COOKIE)
    if token:
        await auth_service.logout(token)

    response = JSONResponse({"ok": True})
    response.delete_cookie(
        key=_SESSION_COOKIE,
        path="/",
        httponly=True,
        samesite="lax",
        secure=_is_secure(),
    )
    response.delete_cookie(
        key=CSRF_COOKIE,
        path="/",
        httponly=False,
        samesite="lax",
        secure=_is_secure(),
    )
    return response
