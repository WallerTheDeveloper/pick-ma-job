"""Integration tests for /api/company-blacklist endpoints."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from api.csrf import require_csrf
from api.deps import get_company_blacklist_service, get_current_user, get_db_pool
from repositories.company_blacklist import CompanyBlacklistEntry
from repositories.user import UserRow
from services.company_blacklist import CompanyBlacklistError, CompanyBlacklistService


def _make_user(email: str = "user@example.com") -> UserRow:
    return UserRow(id=uuid4(), email=email, created_at=datetime.now(timezone.utc), last_login=None)


def _make_entry(name: str = "Google") -> CompanyBlacklistEntry:
    return CompanyBlacklistEntry(
        id=uuid4(),
        user_id=uuid4(),
        name=name,
        name_lower=name.lower(),
        created_at=datetime.now(timezone.utc),
    )


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
    app.state.run_manager = MagicMock()
    return app


@pytest.fixture
async def client(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        yield c


def _override_auth(test_app, user: UserRow):
    test_app.dependency_overrides[get_current_user] = lambda: user


def _override_service(test_app, service: CompanyBlacklistService):
    test_app.dependency_overrides[get_company_blacklist_service] = lambda: service


def _skip_csrf(test_app):
    test_app.dependency_overrides[require_csrf] = lambda: None


def _clear_overrides(test_app):
    test_app.dependency_overrides.clear()


# ── GET /api/company-blacklist ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_blacklist_authenticated_returns_200(test_app, client):
    user = _make_user()
    service = AsyncMock(spec=CompanyBlacklistService)
    service.list.return_value = [_make_entry("Google"), _make_entry("Meta")]

    _override_auth(test_app, user)
    _override_service(test_app, service)
    try:
        resp = await client.get("/api/company-blacklist")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["entries"]) == 2
        assert data["entries"][0]["name"] == "Google"
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_get_blacklist_unauthenticated_returns_401(test_app, client):
    resp = await client.get("/api/company-blacklist")
    assert resp.status_code == 401


# ── POST /api/company-blacklist ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_post_blacklist_valid_returns_201(test_app, client):
    user = _make_user()
    entry = _make_entry("Google")
    service = AsyncMock(spec=CompanyBlacklistService)
    service.add.return_value = entry

    _override_auth(test_app, user)
    _override_service(test_app, service)
    _skip_csrf(test_app)
    try:
        resp = await client.post("/api/company-blacklist", json={"name": "Google"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["entry"]["name"] == "Google"
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_post_blacklist_duplicate_returns_409(test_app, client):
    user = _make_user()
    service = AsyncMock(spec=CompanyBlacklistService)
    service.add.side_effect = CompanyBlacklistError("Company already blacklisted")

    _override_auth(test_app, user)
    _override_service(test_app, service)
    _skip_csrf(test_app)
    try:
        resp = await client.post("/api/company-blacklist", json={"name": "Google"})
        assert resp.status_code == 409
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_post_blacklist_short_name_returns_422(test_app, client):
    user = _make_user()
    service = AsyncMock(spec=CompanyBlacklistService)

    _override_auth(test_app, user)
    _override_service(test_app, service)
    _skip_csrf(test_app)
    try:
        resp = await client.post("/api/company-blacklist", json={"name": "AB"})
        assert resp.status_code == 422
        service.add.assert_not_called()
    finally:
        _clear_overrides(test_app)


# ── DELETE /api/company-blacklist/{id} ────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_blacklist_own_entry_returns_204(test_app, client):
    user = _make_user()
    service = AsyncMock(spec=CompanyBlacklistService)
    service.remove.return_value = None

    _override_auth(test_app, user)
    _override_service(test_app, service)
    _skip_csrf(test_app)
    try:
        entry_id = uuid4()
        resp = await client.delete(f"/api/company-blacklist/{entry_id}")
        assert resp.status_code == 204
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_delete_blacklist_foreign_entry_returns_404(test_app, client):
    user = _make_user()
    service = AsyncMock(spec=CompanyBlacklistService)
    service.remove.side_effect = CompanyBlacklistError("Entry not found")

    _override_auth(test_app, user)
    _override_service(test_app, service)
    _skip_csrf(test_app)
    try:
        entry_id = uuid4()
        resp = await client.delete(f"/api/company-blacklist/{entry_id}")
        assert resp.status_code == 404
    finally:
        _clear_overrides(test_app)
