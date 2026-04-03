"""Integration tests for results routes using httpx.AsyncClient + FastAPI test app.

JobResultRepository and AuthService are overridden via dependency_overrides.
No real PostgreSQL or email sending required.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.templating import Jinja2Templates
from httpx import ASGITransport, AsyncClient

from api.deps import get_auth_service, get_job_result_repo
from repositories.job_result import JobResultRow
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
    app.state.templates = Jinja2Templates(
        directory=str(Path(__file__).parent.parent / "templates")
    )
    return app


@pytest.fixture
async def client(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        yield c


def _make_user() -> UserRow:
    return UserRow(id=uuid4(), email="user@example.com", created_at=datetime.now(timezone.utc), last_login=None)


def _make_result(user_id, **overrides) -> JobResultRow:
    defaults = dict(
        id=uuid4(),
        user_id=user_id,
        platform="upwork",
        job_id=f"job-{uuid4().hex[:8]}",
        title="Unity Developer Needed",
        url="https://upwork.com/jobs/123",
        score=8,
        evaluation={"recommendation": "Yes apply", "summary": "Good match", "scratchpad": "...", "evaluation": "Detailed", "flags": "None"},
        status="new",
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return JobResultRow(**defaults)


def _mock_auth_service(user: UserRow | None = None) -> MagicMock:
    svc = MagicMock()
    svc.get_user_from_session = AsyncMock(return_value=user)
    svc.request_magic_link = AsyncMock()
    svc.verify_magic_link = AsyncMock(return_value="tok")
    svc.logout = AsyncMock()
    return svc


def _mock_repo(
    results: list[JobResultRow] | None = None,
    total: int = 0,
    update_result: JobResultRow | None = None,
) -> MagicMock:
    repo = MagicMock()
    repo.find_by_user = AsyncMock(return_value=results or [])
    repo.count_by_user = AsyncMock(return_value=total)
    repo.update_status = AsyncMock(return_value=update_result)
    return repo


# ── GET /results ──────────────────────────────────────────────────────────────

async def test_results_redirects_to_login_for_unauthenticated(client, test_app):
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=None)
    test_app.dependency_overrides[get_job_result_repo] = lambda: _mock_repo()

    resp = await client.get("/results", follow_redirects=False)
    test_app.dependency_overrides.clear()

    assert resp.status_code == 302
    assert resp.headers["location"] == "/auth/login"


async def test_results_returns_200_for_authenticated_user(client, test_app):
    user = _make_user()
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_job_result_repo] = lambda: _mock_repo()

    client.cookies.set("session_token", "valid-token")
    resp = await client.get("/results")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert b"Results" in resp.content


async def test_results_renders_job_results(client, test_app):
    user = _make_user()
    results = [_make_result(user.id, title="AR Developer Role", score=9)]
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_job_result_repo] = lambda: _mock_repo(results=results, total=1)

    client.cookies.set("session_token", "valid-token")
    resp = await client.get("/results")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert b"AR Developer Role" in resp.content
    assert b"1 result found" in resp.content


async def test_results_filters_by_status(client, test_app):
    user = _make_user()
    repo = _mock_repo(results=[], total=0)
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_job_result_repo] = lambda: repo

    client.cookies.set("session_token", "valid-token")
    resp = await client.get("/results?status=new")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    repo.find_by_user.assert_called_once()
    call_kwargs = repo.find_by_user.call_args
    assert call_kwargs.kwargs.get("status") == "new" or call_kwargs[1].get("status") == "new"


async def test_results_filters_by_min_score(client, test_app):
    user = _make_user()
    repo = _mock_repo(results=[], total=0)
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_job_result_repo] = lambda: repo

    client.cookies.set("session_token", "valid-token")
    resp = await client.get("/results?min_score=7")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    call_kwargs = repo.find_by_user.call_args
    assert call_kwargs.kwargs.get("min_score") == 7 or call_kwargs[1].get("min_score") == 7


async def test_results_filters_by_platform(client, test_app):
    user = _make_user()
    repo = _mock_repo(results=[], total=0)
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_job_result_repo] = lambda: repo

    client.cookies.set("session_token", "valid-token")
    resp = await client.get("/results?platform=upwork")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    call_kwargs = repo.find_by_user.call_args
    assert call_kwargs.kwargs.get("platform") == "upwork" or call_kwargs[1].get("platform") == "upwork"


async def test_results_empty_state_no_filters(client, test_app):
    user = _make_user()
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_job_result_repo] = lambda: _mock_repo(results=[], total=0)

    client.cookies.set("session_token", "valid-token")
    resp = await client.get("/results")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert b"No results yet" in resp.content


async def test_results_empty_state_with_filters(client, test_app):
    user = _make_user()
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_job_result_repo] = lambda: _mock_repo(results=[], total=0)

    client.cookies.set("session_token", "valid-token")
    resp = await client.get("/results?status=applied")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert b"No results match your filters" in resp.content


async def test_results_shows_pagination_when_needed(client, test_app):
    user = _make_user()
    results = [_make_result(user.id) for _ in range(50)]
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_job_result_repo] = lambda: _mock_repo(results=results, total=75)

    client.cookies.set("session_token", "valid-token")
    resp = await client.get("/results")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert b"Page 1 of 2" in resp.content


async def test_results_score_badge_colors(client, test_app):
    user = _make_user()
    results = [
        _make_result(user.id, score=10, title="Green Job"),
        _make_result(user.id, score=7, title="Blue Job"),
        _make_result(user.id, score=5, title="Yellow Job"),
        _make_result(user.id, score=3, title="Orange Job"),
        _make_result(user.id, score=1, title="Red Job"),
    ]
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_job_result_repo] = lambda: _mock_repo(results=results, total=5)

    client.cookies.set("session_token", "valid-token")
    resp = await client.get("/results")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    content = resp.text
    assert "score-green" in content
    assert "score-blue" in content
    assert "score-yellow" in content
    assert "score-orange" in content
    assert "score-red" in content


# ── PATCH /results/{id} ─────────────────────────────────────────────────────

def _setup_csrf(client, test_app):
    """Set session cookie and derive a valid CSRF token for test requests."""
    import hashlib
    import hmac as _hmac
    import os

    session_token = "valid-token"
    secret = os.environ["MAGIC_LINK_SECRET"].encode()
    csrf_token = _hmac.new(secret, session_token.encode(), hashlib.sha256).hexdigest()
    client.cookies.set("session_token", session_token)
    client.cookies.set("csrf_token", csrf_token)
    return csrf_token


async def test_patch_result_updates_status_for_owner(client, test_app):
    user = _make_user()
    result = _make_result(user.id)
    updated = _make_result(user.id, id=result.id, status="applied")
    repo = _mock_repo(update_result=updated)

    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_job_result_repo] = lambda: repo

    csrf_token = _setup_csrf(client, test_app)
    resp = await client.patch(
        f"/results/{result.id}",
        data={"status": "applied"},
        headers={"X-CSRF-Token": csrf_token},
    )
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert b"applied" in resp.content
    repo.update_status.assert_called_once_with(result.id, user.id, "applied")


async def test_patch_result_returns_404_for_non_owner(client, test_app):
    user = _make_user()
    repo = _mock_repo(update_result=None)  # repo returns None → not found / not owned

    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_job_result_repo] = lambda: repo

    csrf_token = _setup_csrf(client, test_app)
    resp = await client.patch(
        f"/results/{uuid4()}",
        data={"status": "applied"},
        headers={"X-CSRF-Token": csrf_token},
    )
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 404


async def test_patch_result_returns_422_for_invalid_status(client, test_app):
    user = _make_user()
    repo = _mock_repo()

    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_job_result_repo] = lambda: repo

    csrf_token = _setup_csrf(client, test_app)
    resp = await client.patch(
        f"/results/{uuid4()}",
        data={"status": "invalid_status"},
        headers={"X-CSRF-Token": csrf_token},
    )
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 422


async def test_patch_result_returns_403_without_csrf(client, test_app):
    user = _make_user()
    repo = _mock_repo()

    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_job_result_repo] = lambda: repo

    client.cookies.set("session_token", "valid-token")
    resp = await client.patch(
        f"/results/{uuid4()}",
        data={"status": "applied"},
    )
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 403
