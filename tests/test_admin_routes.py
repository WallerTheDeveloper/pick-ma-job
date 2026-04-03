"""Integration tests for admin routes.

Tests verify:
- Admin user gets 200 on GET /admin/users
- Non-admin authenticated user gets 403
- Unauthenticated user gets 401
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.templating import Jinja2Templates
from httpx import ASGITransport, AsyncClient

from api.deps import get_auth_service, get_db_pool
from repositories.user import UserRow, UserStatsRow


# ── Fixtures ──────────────────────────────────────────────────────────────────

ADMIN_EMAIL = "admin@example.com"


@pytest.fixture
def test_app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake/fake")
    monkeypatch.setenv("MAGIC_LINK_SECRET", "test-secret")
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("EMAIL_FROM", "test@example.com")
    monkeypatch.setenv("BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("SKIP_EMAIL", "true")
    monkeypatch.setenv("ADMIN_EMAIL", ADMIN_EMAIL)

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


def _make_admin() -> UserRow:
    return UserRow(id=uuid4(), email=ADMIN_EMAIL, created_at=datetime.now(timezone.utc), last_login=None)


def _make_user() -> UserRow:
    return UserRow(id=uuid4(), email="regular@example.com", created_at=datetime.now(timezone.utc), last_login=None)


def _mock_auth_service(user: UserRow | None = None) -> MagicMock:
    svc = MagicMock()
    svc.get_user_from_session = AsyncMock(return_value=user)
    svc.request_magic_link = AsyncMock()
    svc.verify_magic_link = AsyncMock(return_value="tok")
    svc.logout = AsyncMock()
    return svc


def _mock_pool_with_users(users: list[UserStatsRow]) -> MagicMock:
    """Return a pool mock whose .acquire() → conn.fetch() returns user stat rows."""
    rows = []
    for u in users:
        row = MagicMock()
        row.__getitem__ = lambda self, key, _u=u: getattr(_u, key)
        rows.append(row)

    conn = AsyncMock()
    conn.fetch = AsyncMock(return_value=rows)

    pool = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    pool.acquire = MagicMock(return_value=ctx)
    return pool


# ── Tests ─────────────────────────────────────────────────────────────────────

async def test_admin_users_returns_200_for_admin(client, test_app):
    admin = _make_admin()
    stats = [
        UserStatsRow(id=admin.id, email=admin.email, created_at=admin.created_at, last_login=None, job_count=5),
    ]
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=admin)
    test_app.dependency_overrides[get_db_pool] = lambda: _mock_pool_with_users(stats)

    client.cookies.set("session_token", "valid-token")
    resp = await client.get("/admin/users")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert b"admin@example.com" in resp.content
    assert b"Admin" in resp.content


async def test_admin_users_returns_403_for_non_admin(client, test_app):
    user = _make_user()
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)

    client.cookies.set("session_token", "valid-token")
    resp = await client.get("/admin/users")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 403


async def test_admin_users_returns_401_for_unauthenticated(client, test_app):
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=None)

    resp = await client.get("/admin/users")
    test_app.dependency_overrides.clear()

    assert resp.status_code == 401


async def test_admin_users_returns_403_when_admin_email_not_set(client, test_app, monkeypatch):
    """When ADMIN_EMAIL is not set, all users get 403."""
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    admin = _make_admin()
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=admin)

    client.cookies.set("session_token", "valid-token")
    resp = await client.get("/admin/users")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 403


async def test_admin_users_shows_user_table(client, test_app):
    admin = _make_admin()
    other = _make_user()
    stats = [
        UserStatsRow(id=admin.id, email=admin.email, created_at=admin.created_at, last_login=None, job_count=5),
        UserStatsRow(id=other.id, email=other.email, created_at=other.created_at, last_login=None, job_count=12),
    ]
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=admin)
    test_app.dependency_overrides[get_db_pool] = lambda: _mock_pool_with_users(stats)

    client.cookies.set("session_token", "valid-token")
    resp = await client.get("/admin/users")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert b"regular@example.com" in resp.content
    assert b"12" in resp.content
