"""Integration tests for auth routes using httpx.AsyncClient + FastAPI test app.

The DB pool is replaced with a mock so no real PostgreSQL is needed here.
AuthService is overridden via app.dependency_overrides — the correct way to
mock FastAPI dependencies (patch() bypasses the DI container).
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
from pathlib import Path

import pytest
from fastapi.templating import Jinja2Templates
from httpx import ASGITransport, AsyncClient

from api.deps import get_auth_service
from repositories.user import UserRow
from services.auth import AuthError


# ── App fixture ───────────────────────────────────────────────────────────────

@pytest.fixture
def test_app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake/fake")
    monkeypatch.setenv("MAGIC_LINK_SECRET", "test-secret")
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("EMAIL_FROM", "test@example.com")
    monkeypatch.setenv("BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("SKIP_EMAIL", "true")

    from main import create_app
    app = create_app()
    app.state.db_pool = MagicMock()
    app.state.templates = Jinja2Templates(
        directory=str(Path(__file__).parent.parent / "templates")
    )
    return app


@pytest.fixture
async def client(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        yield c


def _mock_auth_service(**kwargs) -> MagicMock:
    """Return a MagicMock AuthService with sensible async defaults."""
    svc = MagicMock()
    svc.request_magic_link = kwargs.get("request_magic_link", AsyncMock())
    svc.verify_magic_link = kwargs.get("verify_magic_link", AsyncMock(return_value="tok"))
    svc.get_user_from_session = kwargs.get("get_user_from_session", AsyncMock(return_value=None))
    svc.logout = kwargs.get("logout", AsyncMock())
    return svc


def _make_user(email: str = "user@example.com") -> UserRow:
    return UserRow(id=uuid4(), email=email, created_at=datetime.now(timezone.utc), last_login=None)


# ── GET /auth/login ───────────────────────────────────────────────────────────

async def test_login_page_renders(client, test_app):
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service()
    resp = await client.get("/auth/login")
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert b"pick-ma-job" in resp.content
    assert b'type="email"' in resp.content


async def test_login_page_shows_error_param(client, test_app):
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service()
    resp = await client.get("/auth/login?error=invalid_or_expired")
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert b"invalid or has expired" in resp.content


async def test_login_page_redirects_when_logged_in(client, test_app):
    user = _make_user()
    svc = _mock_auth_service(get_user_from_session=AsyncMock(return_value=user))
    test_app.dependency_overrides[get_auth_service] = lambda: svc

    # Set a session cookie so get_current_user_optional finds it
    client.cookies.set("session_token", "some-valid-token")
    resp = await client.get("/auth/login", follow_redirects=False)
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 302
    assert resp.headers["location"] == "/"


# ── POST /auth/magic-link ─────────────────────────────────────────────────────

async def test_magic_link_post_valid_email_returns_check_email(client, test_app):
    svc = _mock_auth_service(request_magic_link=AsyncMock())
    test_app.dependency_overrides[get_auth_service] = lambda: svc

    resp = await client.post("/auth/magic-link", data={"email": "user@example.com"})
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert b"Check your email" in resp.content
    assert b"user@example.com" in resp.content


async def test_magic_link_post_invalid_email_shows_error(client, test_app):
    svc = _mock_auth_service(
        request_magic_link=AsyncMock(side_effect=AuthError("Invalid email address."))
    )
    test_app.dependency_overrides[get_auth_service] = lambda: svc

    resp = await client.post("/auth/magic-link", data={"email": "not-valid"})
    test_app.dependency_overrides.clear()

    assert resp.status_code == 422
    assert b"Invalid email" in resp.content


async def test_magic_link_post_rate_limited_shows_error(client, test_app):
    svc = _mock_auth_service(
        request_magic_link=AsyncMock(
            side_effect=AuthError("Too many login attempts. Please wait a few minutes and try again.")
        )
    )
    test_app.dependency_overrides[get_auth_service] = lambda: svc

    resp = await client.post("/auth/magic-link", data={"email": "user@example.com"})
    test_app.dependency_overrides.clear()

    assert resp.status_code == 422
    assert b"Too many" in resp.content


async def test_magic_link_post_htmx_error_is_partial(client, test_app):
    """HTMX requests get an inline error snippet, not a full page."""
    svc = _mock_auth_service(
        request_magic_link=AsyncMock(side_effect=AuthError("Invalid email address."))
    )
    test_app.dependency_overrides[get_auth_service] = lambda: svc

    resp = await client.post(
        "/auth/magic-link",
        data={"email": "bad"},
        headers={"HX-Request": "true"},
    )
    test_app.dependency_overrides.clear()

    assert resp.status_code == 422
    assert b"<p" in resp.content
    assert b"<!DOCTYPE" not in resp.content


# ── GET /auth/verify ──────────────────────────────────────────────────────────

async def test_verify_valid_token_sets_cookie_and_redirects(client, test_app):
    svc = _mock_auth_service(verify_magic_link=AsyncMock(return_value="new-session-token"))
    test_app.dependency_overrides[get_auth_service] = lambda: svc

    resp = await client.get("/auth/verify?token=valid-token", follow_redirects=False)
    test_app.dependency_overrides.clear()

    assert resp.status_code == 302
    assert resp.headers["location"] == "/"
    assert "session_token" in resp.cookies


async def test_verify_invalid_token_redirects_to_login_with_error(client, test_app):
    svc = _mock_auth_service(
        verify_magic_link=AsyncMock(side_effect=AuthError("Invalid or expired."))
    )
    test_app.dependency_overrides[get_auth_service] = lambda: svc

    resp = await client.get("/auth/verify?token=bad-token", follow_redirects=False)
    test_app.dependency_overrides.clear()

    assert resp.status_code == 302
    assert "error=invalid_or_expired" in resp.headers["location"]


# ── POST /auth/logout ─────────────────────────────────────────────────────────

async def test_logout_clears_cookie_and_redirects(client, test_app):
    svc = _mock_auth_service(logout=AsyncMock())
    test_app.dependency_overrides[get_auth_service] = lambda: svc

    resp = await client.post(
        "/auth/logout",
        cookies={"session_token": "some-token"},
        follow_redirects=False,
    )
    test_app.dependency_overrides.clear()

    assert resp.status_code == 302
    assert resp.headers["location"] == "/auth/login"
    assert "session_token" in resp.headers.get("set-cookie", "")


async def test_logout_without_session_still_redirects(client, test_app):
    svc = _mock_auth_service(logout=AsyncMock())
    test_app.dependency_overrides[get_auth_service] = lambda: svc

    resp = await client.post("/auth/logout", follow_redirects=False)
    test_app.dependency_overrides.clear()

    assert resp.status_code == 302
    assert resp.headers["location"] == "/auth/login"


# ── get_current_user dependency ───────────────────────────────────────────────

async def test_get_current_user_no_cookie_returns_401(test_app):
    from fastapi import Depends
    from api.deps import get_current_user

    @test_app.get("/protected-test")
    async def _protected(user=Depends(get_current_user)):
        return {"email": user.email}

    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(
        get_user_from_session=AsyncMock(return_value=None)
    )

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        resp = await c.get("/protected-test")

    test_app.dependency_overrides.clear()
    assert resp.status_code == 401


async def test_get_current_user_invalid_session_returns_401(test_app):
    from fastapi import Depends
    from api.deps import get_current_user

    @test_app.get("/protected-test-2")
    async def _protected2(user=Depends(get_current_user)):
        return {"email": user.email}

    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(
        get_user_from_session=AsyncMock(return_value=None)
    )

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        resp = await c.get("/protected-test-2", cookies={"session_token": "expired"})

    test_app.dependency_overrides.clear()
    assert resp.status_code == 401
