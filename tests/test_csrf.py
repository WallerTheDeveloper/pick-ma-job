"""Tests for CSRF token utilities and enforcement on mutating API routes."""

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from api.csrf import derive_csrf_token, require_csrf
from api.deps import get_auth_service, get_search_config_service, get_profile_service


# ── Unit tests: derive_csrf_token ─────────────────────────────────────────────

def test_derive_csrf_token_is_deterministic(monkeypatch):
    monkeypatch.setenv("MAGIC_LINK_SECRET", "test-secret")
    token1 = derive_csrf_token("session-abc")
    token2 = derive_csrf_token("session-abc")
    assert token1 == token2


def test_derive_csrf_token_differs_for_different_sessions(monkeypatch):
    monkeypatch.setenv("MAGIC_LINK_SECRET", "test-secret")
    assert derive_csrf_token("session-abc") != derive_csrf_token("session-xyz")


def test_derive_csrf_token_differs_for_different_secrets(monkeypatch):
    monkeypatch.setenv("MAGIC_LINK_SECRET", "secret-A")
    token_a = derive_csrf_token("session-abc")
    monkeypatch.setenv("MAGIC_LINK_SECRET", "secret-B")
    token_b = derive_csrf_token("session-abc")
    assert token_a != token_b


def test_derive_csrf_token_returns_hex_string(monkeypatch):
    monkeypatch.setenv("MAGIC_LINK_SECRET", "test-secret")
    token = derive_csrf_token("session-abc")
    # SHA-256 hex digest is always 64 characters
    assert len(token) == 64
    assert all(c in "0123456789abcdef" for c in token)


# ── Integration fixtures ───────────────────────────────────────────────────────

from repositories.user import UserRow


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
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as c:
        yield c


def _make_user() -> UserRow:
    return UserRow(
        id=uuid4(),
        email="user@example.com",
        created_at=datetime.now(timezone.utc),
        last_login=None,
    )


def _mock_auth_service(user: UserRow | None = None) -> MagicMock:
    svc = MagicMock()
    svc.get_user_from_session = AsyncMock(return_value=user)
    return svc


def _mock_search_config_service(delete_result: bool = True) -> MagicMock:
    svc = MagicMock()
    svc.get_all = AsyncMock(return_value=[])
    svc.delete = AsyncMock(return_value=delete_result)
    svc.upsert = AsyncMock(return_value=None)
    return svc


def _mock_profile_service() -> MagicMock:
    svc = MagicMock()
    svc.get_or_default = AsyncMock(return_value=None)
    svc.update = AsyncMock(return_value=None)
    return svc


# ── CSRF enforcement: DELETE /api/search-configs/{id} ────────────────────────

async def test_delete_without_csrf_token_returns_403(client, test_app):
    user = _make_user()
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_search_config_service] = lambda: _mock_search_config_service()

    client.cookies.set("session_token", "valid-token")
    resp = await client.delete(f"/api/search-configs/{uuid4()}")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 403
    assert "CSRF" in resp.json()["detail"]


async def test_delete_with_wrong_csrf_token_returns_403(client, test_app, monkeypatch):
    monkeypatch.setenv("MAGIC_LINK_SECRET", "test-secret")
    user = _make_user()
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_search_config_service] = lambda: _mock_search_config_service()

    client.cookies.set("session_token", "valid-token")
    resp = await client.delete(
        f"/api/search-configs/{uuid4()}",
        headers={"X-CSRF-Token": "wrong-token"},
    )
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 403


async def test_delete_with_valid_csrf_token_succeeds(client, test_app, monkeypatch):
    monkeypatch.setenv("MAGIC_LINK_SECRET", "test-secret")
    user = _make_user()
    session_token = "valid-token"
    csrf_token = derive_csrf_token(session_token)

    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_search_config_service] = lambda: _mock_search_config_service()

    client.cookies.set("session_token", session_token)
    resp = await client.delete(
        f"/api/search-configs/{uuid4()}",
        headers={"X-CSRF-Token": csrf_token},
    )
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200


# ── CSRF enforcement: POST /api/search-configs ──────────────────────────────

async def test_post_search_config_without_csrf_returns_403(client, test_app):
    user = _make_user()
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_search_config_service] = lambda: _mock_search_config_service()

    client.cookies.set("session_token", "valid-token")
    resp = await client.post(
        "/api/search-configs",
        json={"platform": "upwork", "query": "unity"},
    )
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 403


async def test_post_search_config_with_valid_csrf_succeeds(client, test_app, monkeypatch):
    monkeypatch.setenv("MAGIC_LINK_SECRET", "test-secret")
    user = _make_user()
    session_token = "valid-token"
    csrf_token = derive_csrf_token(session_token)

    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_search_config_service] = lambda: _mock_search_config_service()

    client.cookies.set("session_token", session_token)
    resp = await client.post(
        "/api/search-configs",
        json={"platform": "upwork", "query": "unity"},
        headers={"X-CSRF-Token": csrf_token},
    )
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 201


# ── CSRF enforcement: POST /api/profile ────────────────────────────────────

async def test_post_profile_without_csrf_returns_403(client, test_app):
    user = _make_user()
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_profile_service] = lambda: _mock_profile_service()

    client.cookies.set("session_token", "valid-token")
    resp = await client.post("/api/profile", json={"role": "Unity Developer"})
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 403


# ── CSRF not enforced for GET requests ───────────────────────────────────────

async def test_get_search_configs_without_csrf_succeeds(client, test_app):
    """GET requests must never require a CSRF token."""
    user = _make_user()
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_search_config_service] = lambda: _mock_search_config_service()

    client.cookies.set("session_token", "valid-token")
    resp = await client.get("/api/search-configs")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200


# ── CSRF passes through when no session cookie present (let 401 fire) ─────────

async def test_delete_without_session_cookie_returns_401_not_403(client, test_app):
    """Unauthenticated requests should get 401 from get_current_user, not 403 from CSRF."""
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=None)
    test_app.dependency_overrides[get_search_config_service] = lambda: _mock_search_config_service()

    resp = await client.delete(f"/api/search-configs/{uuid4()}")
    test_app.dependency_overrides.clear()

    assert resp.status_code == 401
