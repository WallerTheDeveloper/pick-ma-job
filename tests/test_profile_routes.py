"""Integration tests for profile routes using httpx.AsyncClient + FastAPI test app.

ProfileService and AuthService are overridden via dependency_overrides.
No real PostgreSQL or email sending required.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.templating import Jinja2Templates
from httpx import ASGITransport, AsyncClient

from api.csrf import require_csrf
from api.deps import get_auth_service, get_profile_service
from repositories.profile import ProfileRow
from repositories.user import UserRow
from services.profile import ProfileError


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
    app.state.templates = Jinja2Templates(
        directory=str(Path(__file__).parent.parent / "templates")
    )
    app.dependency_overrides[require_csrf] = lambda: None
    return app


@pytest.fixture
async def client(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        yield c


def _make_user() -> UserRow:
    return UserRow(id=uuid4(), email="user@example.com", created_at=datetime.now(timezone.utc), last_login=None)


def _make_profile_row(user_id) -> ProfileRow:
    return ProfileRow(
        id=uuid4(),
        user_id=user_id,
        role="Unity Developer",
        experience="mid-level",
        rate="€20/hr",
        primary_skills=["Unity", "C#"],
        secondary_skills=["Rust"],
        tertiary_skills=["Vue.js"],
        not_a_good_fit=["Pure frontend"],
        background=["2 years at ZAUBAR"],
        notable_projects=[{"name": "VR App", "description": "Unity XR project"}],
        languages=["English", "Ukrainian"],
        rubric={},
        updated_at=datetime.now(timezone.utc),
    )


def _mock_auth_service(user: UserRow | None = None) -> MagicMock:
    svc = MagicMock()
    svc.get_user_from_session = AsyncMock(return_value=user)
    svc.request_magic_link = AsyncMock()
    svc.verify_magic_link = AsyncMock(return_value="tok")
    svc.logout = AsyncMock()
    return svc


def _mock_profile_service(profile: ProfileRow | None = None, error: ProfileError | None = None) -> MagicMock:
    svc = MagicMock()
    svc.get_or_default = AsyncMock(return_value=profile)
    if error:
        svc.update = AsyncMock(side_effect=error)
    else:
        svc.update = AsyncMock(return_value=profile)
    return svc


# ── GET /profile ──────────────────────────────────────────────────────────────

async def test_profile_page_unauthenticated_returns_401(client, test_app):
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=None)
    resp = await client.get("/profile", follow_redirects=False)
    test_app.dependency_overrides.clear()

    assert resp.status_code == 401


async def test_profile_page_renders_empty_form_for_new_user(client, test_app):
    user = _make_user()
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_profile_service] = lambda: _mock_profile_service(profile=None)

    client.cookies.set("session_token", "valid-token")
    resp = await client.get("/profile")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert b"Profile" in resp.content
    assert b'name="primary_skills"' in resp.content


async def test_profile_page_pre_populates_existing_profile(client, test_app):
    user = _make_user()
    profile = _make_profile_row(user.id)
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_profile_service] = lambda: _mock_profile_service(profile=profile)

    client.cookies.set("session_token", "valid-token")
    resp = await client.get("/profile")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert b"Unity Developer" in resp.content
    assert b"Unity" in resp.content
    assert b"Rust" in resp.content


# ── POST /profile ─────────────────────────────────────────────────────────────

async def test_save_profile_success_shows_saved_banner(client, test_app):
    user = _make_user()
    profile = _make_profile_row(user.id)
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_profile_service] = lambda: _mock_profile_service(profile=profile)

    client.cookies.set("session_token", "valid-token")
    resp = await client.post("/profile", data={
        "role": "Unity Developer",
        "experience": "mid-level",
        "rate": "€20/hr",
        "primary_skills": "Unity\nC#",
        "secondary_skills": "Rust",
        "tertiary_skills": "",
        "not_a_good_fit": "Pure frontend",
        "background": "2 years at ZAUBAR",
        "project_names": "VR App",
        "project_descriptions": "Unity XR project",
        "languages": "English",
    })
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert b"Profile saved" in resp.content


async def test_save_profile_validation_error_shows_error_message(client, test_app):
    user = _make_user()
    profile = _make_profile_row(user.id)
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_profile_service] = lambda: _mock_profile_service(
        profile=profile,
        error=ProfileError("At least one primary skill is required."),
    )

    client.cookies.set("session_token", "valid-token")
    resp = await client.post("/profile", data={
        "primary_skills": "",  # empty — triggers validation error
    })
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 422
    assert b"primary skill" in resp.content


async def test_save_profile_unauthenticated_returns_401(client, test_app):
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=None)
    resp = await client.post("/profile", data={"primary_skills": "Unity"})
    test_app.dependency_overrides.clear()

    assert resp.status_code == 401


async def test_save_profile_parses_multiline_skills(client, test_app):
    """Verify that newline-separated textarea values are split and passed as lists."""
    user = _make_user()
    profile = _make_profile_row(user.id)

    captured = {}

    async def _mock_update(user_id, data):
        captured["data"] = data
        return profile

    profile_svc = _mock_profile_service(profile=profile)
    profile_svc.update = _mock_update

    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_profile_service] = lambda: profile_svc

    client.cookies.set("session_token", "valid-token")
    await client.post("/profile", data={
        "primary_skills": "Unity\nC#\nAR Foundation",
        "secondary_skills": "Rust\nC++",
    })
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert captured["data"].primary_skills == ["Unity", "C#", "AR Foundation"]
    assert captured["data"].secondary_skills == ["Rust", "C++"]


async def test_save_profile_parses_notable_projects(client, test_app):
    """Verify that parallel project name/description textareas are zipped correctly."""
    user = _make_user()
    profile = _make_profile_row(user.id)

    captured = {}

    async def _mock_update(user_id, data):
        captured["data"] = data
        return profile

    profile_svc = _mock_profile_service(profile=profile)
    profile_svc.update = _mock_update

    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_profile_service] = lambda: profile_svc

    client.cookies.set("session_token", "valid-token")
    await client.post("/profile", data={
        "primary_skills": "Unity",
        "project_names": "VR App\nRust Game",
        "project_descriptions": "Unity XR project\nAuthoritative server",
    })
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    projects = captured["data"].notable_projects
    assert len(projects) == 2
    assert projects[0] == {"name": "VR App", "description": "Unity XR project"}
    assert projects[1] == {"name": "Rust Game", "description": "Authoritative server"}
