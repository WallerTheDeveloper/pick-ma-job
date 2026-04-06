"""Auth routes — login page, magic link request, verify, logout.

Supports both HTML (Jinja2/HTMX) and JSON (React SPA) responses.
JSON mode is activated when Content-Type is application/json or the request
accepts JSON but not HTML.
"""

import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from api.csrf import CSRF_COOKIE, derive_csrf_token
from api.deps import get_auth_service, get_current_user, get_current_user_optional
from api.schemas import AuthMeResponse, OkResponse, UserInfo
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


def _wants_json(request: Request) -> bool:
    """Return True if the request is from a JSON client (React SPA)."""
    content_type = request.headers.get("content-type", "")
    accept = request.headers.get("accept", "")
    return "application/json" in content_type or (
        "application/json" in accept and "text/html" not in accept
    )


def _make_user_info(user: UserRow) -> UserInfo:
    """Build a UserInfo response from a UserRow."""
    admin_email = os.environ.get("ADMIN_EMAIL", "").strip()
    is_admin = bool(admin_email and user.email == admin_email)
    return UserInfo(id=user.id, email=user.email, is_admin=is_admin)


# ── JSON API ─────────────────────────────────────────────────────────────────

@router.get("/me")
async def auth_me(
    user: Annotated[UserRow, Depends(get_current_user)],
) -> AuthMeResponse:
    """Return the current authenticated user. Used by the React SPA to check auth state."""
    return AuthMeResponse(user=_make_user_info(user))


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

@router.post("/magic-link", response_model=None)
async def request_magic_link(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> HTMLResponse | JSONResponse:
    """Accept an email address and send a magic link.

    JSON mode (React SPA): expects ``{"email": "..."}`` body, returns ``{"ok": true}``.
    HTML mode (HTMX/form): expects form-encoded body, returns template response.
    Always returns success — never reveals whether the address exists.
    """
    if _wants_json(request):
        body = await request.json()
        email = str(body.get("email", "")).strip().lower()
        if not email:
            return JSONResponse({"ok": False, "error": "Email is required"}, status_code=422)
        try:
            await auth_service.request_magic_link(email)
        except AuthError as exc:
            return JSONResponse({"ok": False, "error": str(exc)}, status_code=429)
        return JSONResponse({"ok": True})

    # ── HTML / HTMX mode ─────────────────────────────────────────────────
    form = await request.form()
    email = str(form.get("email", "")).strip().lower()

    try:
        await auth_service.request_magic_link(email)
    except AuthError as exc:
        is_htmx = request.headers.get("HX-Request") == "true"
        if is_htmx:
            return HTMLResponse(
                content=f'<p class="error">{exc}</p>',
                status_code=200,
            )
        return _templates(request).TemplateResponse(
            request,
            "login.html",
            {"error": str(exc)},
            status_code=429,
        )

    return _templates(request).TemplateResponse(
        request,
        "check_email.html",
        {"email": email},
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
    redirect.set_cookie(
        key=CSRF_COOKIE,
        value=derive_csrf_token(session_token),
        max_age=_SESSION_TTL_SECONDS,
        httponly=False,
        secure=_is_secure(),
        samesite="lax",
    )
    return redirect


@router.post("/logout")
async def logout(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> Response:
    """Invalidate the current session and clear the session cookie.

    JSON mode (React SPA): returns ``{"ok": true}``.
    HTMX mode: returns ``HX-Redirect`` header.
    """
    token = request.cookies.get(_SESSION_COOKIE)
    if token:
        await auth_service.logout(token)

    is_htmx = request.headers.get("HX-Request") == "true"

    if is_htmx:
        response = Response(status_code=200)
        response.headers["HX-Redirect"] = "/auth/login"
    else:
        response = JSONResponse({"ok": True})

    response.delete_cookie(key=_SESSION_COOKIE)
    response.delete_cookie(key=CSRF_COOKIE)
    return response
