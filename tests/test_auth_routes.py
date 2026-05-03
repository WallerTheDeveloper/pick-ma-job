"""Integration tests for auth routes using httpx.AsyncClient + FastAPI test app.

The DB pool is replaced with a mock so no real PostgreSQL is needed here.
AuthService is overridden via app.dependency_overrides — the correct way to
mock FastAPI dependencies (patch() bypasses the DI container).
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
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


# ── GET /auth/me ─────────────────────────────────────────────────────────────

async def test_auth_me_returns_user_when_authenticated(client, test_app):
    user = _make_user()
    svc = _mock_auth_service(get_user_from_session=AsyncMock(return_value=user))
    test_app.dependency_overrides[get_auth_service] = lambda: svc

    client.cookies.set("session_token", "valid-token")
    resp = await client.get("/auth/me")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["email"] == "user@example.com"
    assert data["user"]["id"] is not None


async def test_auth_me_returns_401_when_not_authenticated(client, test_app):
    svc = _mock_auth_service(get_user_from_session=AsyncMock(return_value=None))
    test_app.dependency_overrides[get_auth_service] = lambda: svc

    resp = await client.get("/auth/me")
    test_app.dependency_overrides.clear()

    assert resp.status_code == 401


# ── POST /auth/magic-link ─────────────────────────────────────────────────────

async def test_magic_link_post_valid_email_returns_ok(client, test_app):
    svc = _mock_auth_service(request_magic_link=AsyncMock())
    test_app.dependency_overrides[get_auth_service] = lambda: svc

    resp = await client.post(
        "/auth/magic-link",
        json={"email": "user@example.com"},
    )
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["ok"] is True


async def test_magic_link_post_empty_email_returns_422(client, test_app):
    svc = _mock_auth_service()
    test_app.dependency_overrides[get_auth_service] = lambda: svc

    resp = await client.post("/auth/magic-link", json={"email": ""})
    test_app.dependency_overrides.clear()

    assert resp.status_code == 422
    assert resp.json()["ok"] is False


async def test_magic_link_post_rate_limited_returns_429(client, test_app):
    svc = _mock_auth_service(
        request_magic_link=AsyncMock(
            side_effect=AuthError("Too many login attempts.")
        )
    )
    test_app.dependency_overrides[get_auth_service] = lambda: svc

    resp = await client.post(
        "/auth/magic-link",
        json={"email": "user@example.com"},
    )
    test_app.dependency_overrides.clear()

    assert resp.status_code == 429
    assert resp.json()["ok"] is False


# ── GET /auth/verify ──────────────────────────────────────────────────────────

async def test_verify_valid_token_sets_cookie_and_redirects(client, test_app, monkeypatch):
    svc = _mock_auth_service(verify_magic_link=AsyncMock(return_value="new-session-token"))
    test_app.dependency_overrides[get_auth_service] = lambda: svc
    monkeypatch.delenv("FRONTEND_URL", raising=False)

    resp = await client.get("/auth/verify?token=valid-token", follow_redirects=False)
    test_app.dependency_overrides.clear()

    assert resp.status_code == 302
    assert resp.headers["location"] == "/dashboard"
    assert "session_token" in resp.cookies


async def test_verify_valid_token_cookies_have_path_root(client, test_app, monkeypatch):
    svc = _mock_auth_service(verify_magic_link=AsyncMock(return_value="new-session-token"))
    test_app.dependency_overrides[get_auth_service] = lambda: svc
    monkeypatch.delenv("FRONTEND_URL", raising=False)

    resp = await client.get("/auth/verify?token=valid-token", follow_redirects=False)
    test_app.dependency_overrides.clear()

    set_cookie_headers = resp.headers.get_list("set-cookie")
    assert len(set_cookie_headers) == 2, "Expected two Set-Cookie headers"
    for header in set_cookie_headers:
        assert "Path=/" in header, f"Cookie missing Path=/: {header}"


async def test_verify_invalid_token_redirects_with_error(client, test_app):
    svc = _mock_auth_service(
        verify_magic_link=AsyncMock(side_effect=AuthError("Invalid or expired."))
    )
    test_app.dependency_overrides[get_auth_service] = lambda: svc

    resp = await client.get("/auth/verify?token=bad-token", follow_redirects=False)
    test_app.dependency_overrides.clear()

    assert resp.status_code == 302
    assert "error=invalid_or_expired" in resp.headers["location"]


async def test_verify_redirects_to_frontend_url_when_set(client, test_app, monkeypatch):
    svc = _mock_auth_service(verify_magic_link=AsyncMock(return_value="new-session-token"))
    test_app.dependency_overrides[get_auth_service] = lambda: svc
    monkeypatch.setenv("FRONTEND_URL", "http://localhost:5173")

    resp = await client.get("/auth/verify?token=valid-token", follow_redirects=False)
    test_app.dependency_overrides.clear()

    assert resp.status_code == 302
    assert resp.headers["location"] == "http://localhost:5173/dashboard"


# ── POST /auth/logout ─────────────────────────────────────────────────────────

async def test_logout_returns_json_ok(client, test_app):
    svc = _mock_auth_service(logout=AsyncMock())
    test_app.dependency_overrides[get_auth_service] = lambda: svc

    resp = await client.post(
        "/auth/logout",
        cookies={"session_token": "some-token"},
    )
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["ok"] is True


async def test_logout_without_session_still_returns_ok(client, test_app):
    svc = _mock_auth_service(logout=AsyncMock())
    test_app.dependency_overrides[get_auth_service] = lambda: svc

    resp = await client.post("/auth/logout")
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["ok"] is True


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
