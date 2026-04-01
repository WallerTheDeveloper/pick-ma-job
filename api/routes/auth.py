"""Auth routes — login page, magic link request, verify, logout."""

import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from api.deps import get_auth_service, get_current_user_optional
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


def _templates(request: Request):
    return request.app.state.templates


# ── Pages ─────────────────────────────────────────────────────────────────────

@router.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    error: str | None = None,
    user: Annotated[UserRow | None, Depends(get_current_user_optional)] = None,
) -> HTMLResponse:
    """Render the login / signup page. Redirect to dashboard if already logged in."""
    if user is not None:
        return RedirectResponse(url="/", status_code=302)
    return _templates(request).TemplateResponse(
        request,
        "login.html",
        {"error": error},
    )


# ── Actions ───────────────────────────────────────────────────────────────────

@router.post("/magic-link", response_class=HTMLResponse)
async def request_magic_link(
    request: Request,
    email: Annotated[str, Form()],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> HTMLResponse:
    """Accept an email address and send a magic link.

    Always returns the check-email page — never reveals whether the address exists.
    Returns an inline HTMX partial if the request came from HTMX, full page otherwise.
    """
    try:
        await auth_service.request_magic_link(email.strip().lower())
    except AuthError as exc:
        is_htmx = request.headers.get("HX-Request") == "true"
        if is_htmx:
            return HTMLResponse(
                content=f'<p class="error">{exc}</p>',
                status_code=422,
            )
        return _templates(request).TemplateResponse(
            request,
            "login.html",
            {"error": str(exc)},
            status_code=422,
        )

    return _templates(request).TemplateResponse(
        request,
        "check_email.html",
        {"email": email.strip().lower()},
    )


@router.get("/verify")
async def verify_magic_link(
    token: str,
    response: Response,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> RedirectResponse:
    """Validate a magic link token, set a session cookie, and redirect to the dashboard."""
    try:
        session_token = await auth_service.verify_magic_link(token)
    except AuthError:
        return RedirectResponse(
            url="/auth/login?error=invalid_or_expired",
            status_code=302,
        )

    redirect = RedirectResponse(url="/", status_code=302)
    redirect.set_cookie(
        key=_SESSION_COOKIE,
        value=session_token,
        max_age=_SESSION_TTL_SECONDS,
        httponly=True,
        secure=_is_secure(),
        samesite="lax",
    )
    return redirect


@router.post("/logout")
async def logout(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> RedirectResponse:
    """Invalidate the current session and clear the session cookie."""
    token = request.cookies.get(_SESSION_COOKIE)
    if token:
        await auth_service.logout(token)

    redirect = RedirectResponse(url="/auth/login", status_code=302)
    redirect.delete_cookie(key=_SESSION_COOKIE)
    return redirect
