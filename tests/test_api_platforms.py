"""Unit tests for GET /api/platforms — registry-driven platform list."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from api.deps import get_current_user, get_search_config_service
from repositories.user import UserRow


# ── Fixtures ──────────────────────────────────────────────────────────────────

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


def _make_user(email: str = "user@example.com") -> UserRow:
    return UserRow(id=uuid4(), email=email, created_at=datetime.now(timezone.utc), last_login=None)


def _fake_config(platform: str):
    cfg = MagicMock()
    cfg.platform = platform
    return cfg


def _setup_overrides(test_app, *, user=None, configs=None):
    """Wire dependency_overrides for a platforms test.

    configs: list of config objects returned by search_config_svc.get_all
    """
    if user is None:
        user = _make_user()

    search_config_svc = MagicMock()
    search_config_svc.get_all = AsyncMock(return_value=configs or [])

    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[get_search_config_service] = lambda: search_config_svc

    return user, search_config_svc


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_platforms_reflects_registry(client, test_app):
    """Response lists every platform from the scraper registry."""
    _setup_overrides(test_app, configs=[])

    with patch("api.routes.api_platforms.list_platforms", return_value=["upwork", "linkedin"]):
        resp = await client.get("/api/platforms")

    assert resp.status_code == 200
    data = resp.json()
    slugs = {p["slug"] for p in data["platforms"]}
    assert slugs == {"upwork", "linkedin"}


@pytest.mark.asyncio
async def test_has_config_true_when_configured(client, test_app):
    """has_config is True for platforms the user has configured."""
    user = _make_user()
    _setup_overrides(test_app, user=user, configs=[_fake_config("upwork")])

    with patch("api.routes.api_platforms.list_platforms", return_value=["upwork", "linkedin"]):
        resp = await client.get("/api/platforms")

    assert resp.status_code == 200
    platforms = {p["slug"]: p["has_config"] for p in resp.json()["platforms"]}
    assert platforms["upwork"] is True
    assert platforms["linkedin"] is False


@pytest.mark.asyncio
async def test_has_config_false_when_no_configs(client, test_app):
    """has_config is False for all platforms when user has no configs."""
    _setup_overrides(test_app, configs=[])

    with patch("api.routes.api_platforms.list_platforms", return_value=["upwork", "linkedin"]):
        resp = await client.get("/api/platforms")

    assert resp.status_code == 200
    assert all(not p["has_config"] for p in resp.json()["platforms"])


@pytest.mark.asyncio
async def test_has_config_true_for_all_when_all_configured(client, test_app):
    """has_config is True for all platforms when every one is configured."""
    _setup_overrides(
        test_app,
        configs=[_fake_config("upwork"), _fake_config("linkedin")],
    )

    with patch("api.routes.api_platforms.list_platforms", return_value=["upwork", "linkedin"]):
        resp = await client.get("/api/platforms")

    assert resp.status_code == 200
    assert all(p["has_config"] for p in resp.json()["platforms"])


@pytest.mark.asyncio
async def test_unauthenticated_returns_401(client, test_app):
    """Endpoint requires authentication."""
    # No overrides — get_current_user raises 401 naturally
    resp = await client.get("/api/platforms")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_empty_registry(client, test_app):
    """Empty registry returns an empty list."""
    _setup_overrides(test_app, configs=[])

    with patch("api.routes.api_platforms.list_platforms", return_value=[]):
        resp = await client.get("/api/platforms")

    assert resp.status_code == 200
    assert resp.json()["platforms"] == []
