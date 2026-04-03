"""Integration tests for pipeline routes using httpx.AsyncClient + FastAPI test app.

RunManager, ProfileService, SearchConfigService, and AuthService are all
overridden via dependency_overrides — no real DB or background tasks run.
"""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from uuid import uuid4

import pytest
from fastapi.templating import Jinja2Templates
from httpx import ASGITransport, AsyncClient

from api.csrf import require_csrf
from api.deps import (
    get_auth_service,
    get_profile_service,
    get_run_manager,
    get_search_config_service,
)
from repositories.profile import ProfileRow
from repositories.search_config import SearchConfigRow
from repositories.user import UserRow
from services.pipeline import PipelineRunResult
from services.run_manager import PipelineRunSnapshot, RunActiveError


# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

def _make_user(**overrides) -> UserRow:
    defaults = dict(
        id=uuid4(),
        email="user@example.com",
        created_at=datetime.now(timezone.utc),
        last_login=None,
    )
    defaults.update(overrides)
    return UserRow(**defaults)


def _make_profile(user_id=None) -> ProfileRow:
    return ProfileRow(
        id=uuid4(),
        user_id=user_id or uuid4(),
        role="Unity Developer",
        experience="mid-level",
        rate="€20/hr",
        primary_skills=["Unity"],
        secondary_skills=[],
        tertiary_skills=[],
        not_a_good_fit=[],
        background=[],
        notable_projects=[],
        languages=["English"],
        rubric={},
        updated_at=datetime.now(timezone.utc),
    )


def _make_search_config(user_id=None) -> SearchConfigRow:
    return SearchConfigRow(
        id=uuid4(),
        user_id=user_id or uuid4(),
        platform="upwork",
        query="unity developer",
        filters={},
        updated_at=datetime.now(timezone.utc),
    )


def _make_result(**overrides) -> PipelineRunResult:
    defaults = dict(
        jobs_found=5,
        jobs_skipped_dedup=1,
        jobs_skipped_filter=0,
        jobs_evaluated=4,
        jobs_stored=4,
        errors=(),
    )
    defaults.update(overrides)
    return PipelineRunResult(**defaults)


def _make_snapshot(user_id, status="pending", **overrides) -> PipelineRunSnapshot:
    run_id = overrides.pop("run_id", uuid4())
    return PipelineRunSnapshot(
        run_id=run_id,
        user_id=user_id,
        status=status,
        started_at=datetime.now(timezone.utc),
        **overrides,
    )


# ---------------------------------------------------------------------------
# Mock service helpers
# ---------------------------------------------------------------------------

def _mock_auth(user: UserRow | None) -> MagicMock:
    svc = MagicMock()
    svc.get_user_from_session = AsyncMock(return_value=user)
    return svc


def _mock_profile_svc(profile: ProfileRow | None) -> MagicMock:
    svc = MagicMock()
    svc.get_or_default = AsyncMock(return_value=profile)
    return svc


def _mock_search_config_svc(
    all_configs: list | None = None,
    by_platform: SearchConfigRow | None = None,
) -> MagicMock:
    svc = MagicMock()
    svc.get_all = AsyncMock(return_value=all_configs or [])
    svc.get_by_platform = AsyncMock(return_value=by_platform)
    return svc


def _mock_run_manager(
    run_id=None,
    active_error: RunActiveError | None = None,
    snapshot: PipelineRunSnapshot | None = None,
) -> MagicMock:
    mgr = MagicMock()
    if active_error:
        mgr.start_run.side_effect = active_error
    else:
        mgr.start_run.return_value = run_id or uuid4()
    mgr.get_run.return_value = snapshot
    return mgr


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def test_app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake/fake")
    monkeypatch.setenv("MAGIC_LINK_SECRET", "test-secret")
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("EMAIL_FROM", "test@example.com")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("APIFY_API_TOKEN", "apify-test")

    from main import create_app
    app = create_app()
    app.state.db_pool = MagicMock()
    app.state.templates = Jinja2Templates(
        directory=str(Path(__file__).parent.parent / "templates")
    )
    app.dependency_overrides[require_csrf] = lambda: None
    return app


def _build_client(test_app, user, profile, search_configs, run_manager_mock):
    """Wire dependency overrides and return a configured AsyncClient."""
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth(user)
    test_app.dependency_overrides[get_profile_service] = lambda: profile
    test_app.dependency_overrides[get_search_config_service] = lambda: search_configs
    test_app.dependency_overrides[get_run_manager] = lambda: run_manager_mock
    return AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test")


# ---------------------------------------------------------------------------
# POST /run — auth
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_run_requires_auth(test_app):
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth(None)
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        resp = await c.post("/run", cookies={"session_token": "bad"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# POST /run — pre-validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_run_400_when_profile_missing(test_app):
    user = _make_user()
    profile_svc = _mock_profile_svc(profile=None)
    search_svc = _mock_search_config_svc()
    mgr = _mock_run_manager()

    async with _build_client(test_app, user, profile_svc, search_svc, mgr) as c:
        resp = await c.post("/run", cookies={"session_token": "valid"})

    assert resp.status_code == 400
    assert "Profile not configured" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_post_run_400_when_no_search_configs(test_app):
    user = _make_user()
    profile_svc = _mock_profile_svc(profile=_make_profile(user.id))
    search_svc = _mock_search_config_svc(all_configs=[])
    mgr = _mock_run_manager()

    async with _build_client(test_app, user, profile_svc, search_svc, mgr) as c:
        resp = await c.post("/run", cookies={"session_token": "valid"})

    assert resp.status_code == 400
    assert "search config" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_post_run_400_when_platform_config_missing(test_app):
    user = _make_user()
    profile_svc = _mock_profile_svc(profile=_make_profile(user.id))
    search_svc = _mock_search_config_svc(by_platform=None)
    mgr = _mock_run_manager()

    async with _build_client(test_app, user, profile_svc, search_svc, mgr) as c:
        resp = await c.post("/run?platform=upwork", cookies={"session_token": "valid"})

    assert resp.status_code == 400
    assert "upwork" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# POST /run — conflict
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_run_409_when_run_already_active(test_app):
    user = _make_user()
    profile_svc = _mock_profile_svc(profile=_make_profile(user.id))
    search_svc = _mock_search_config_svc(all_configs=[_make_search_config(user.id)])
    mgr = _mock_run_manager(active_error=RunActiveError("Already running."))

    async with _build_client(test_app, user, profile_svc, search_svc, mgr) as c:
        resp = await c.post("/run", cookies={"session_token": "valid"})

    assert resp.status_code == 409
    assert "Already running" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# POST /run — success
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_run_202_returns_run_id(test_app):
    user = _make_user()
    run_id = uuid4()
    profile_svc = _mock_profile_svc(profile=_make_profile(user.id))
    search_svc = _mock_search_config_svc(all_configs=[_make_search_config(user.id)])
    mgr = _mock_run_manager(run_id=run_id)

    async with _build_client(test_app, user, profile_svc, search_svc, mgr) as c:
        resp = await c.post("/run", cookies={"session_token": "valid"})

    assert resp.status_code == 202
    assert resp.json()["run_id"] == str(run_id)


@pytest.mark.asyncio
async def test_post_run_passes_platform_to_run_manager(test_app):
    user = _make_user()
    run_id = uuid4()
    profile_svc = _mock_profile_svc(profile=_make_profile(user.id))
    search_svc = _mock_search_config_svc(by_platform=_make_search_config(user.id))
    mgr = _mock_run_manager(run_id=run_id)

    async with _build_client(test_app, user, profile_svc, search_svc, mgr) as c:
        resp = await c.post("/run?platform=upwork", cookies={"session_token": "valid"})

    assert resp.status_code == 202
    mgr.start_run.assert_called_once()
    _, _, platform_arg = mgr.start_run.call_args[0]
    assert platform_arg == "upwork"


@pytest.mark.asyncio
async def test_post_run_no_platform_passes_none_to_run_manager(test_app):
    user = _make_user()
    profile_svc = _mock_profile_svc(profile=_make_profile(user.id))
    search_svc = _mock_search_config_svc(all_configs=[_make_search_config(user.id)])
    mgr = _mock_run_manager()

    async with _build_client(test_app, user, profile_svc, search_svc, mgr) as c:
        await c.post("/run", cookies={"session_token": "valid"})

    _, _, platform_arg = mgr.start_run.call_args[0]
    assert platform_arg is None


# ---------------------------------------------------------------------------
# GET /run/{run_id}/status — auth
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_status_requires_auth(test_app):
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth(None)
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        resp = await c.get(f"/run/{uuid4()}/status", cookies={"session_token": "bad"})
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# GET /run/{run_id}/status — not found / isolation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_status_404_for_unknown_run(test_app):
    user = _make_user()
    mgr = _mock_run_manager(snapshot=None)
    profile_svc = _mock_profile_svc(None)
    search_svc = _mock_search_config_svc()

    async with _build_client(test_app, user, profile_svc, search_svc, mgr) as c:
        resp = await c.get(f"/run/{uuid4()}/status", cookies={"session_token": "valid"})

    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_status_404_for_different_users_run(test_app):
    user = _make_user()
    other_user_id = uuid4()
    snapshot = _make_snapshot(user_id=other_user_id, status="running")
    mgr = _mock_run_manager(snapshot=snapshot)
    profile_svc = _mock_profile_svc(None)
    search_svc = _mock_search_config_svc()

    async with _build_client(test_app, user, profile_svc, search_svc, mgr) as c:
        resp = await c.get(f"/run/{snapshot.run_id}/status", cookies={"session_token": "valid"})

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /run/{run_id}/status — success states
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_status_pending(test_app):
    user = _make_user()
    snapshot = _make_snapshot(user_id=user.id, status="pending")
    mgr = _mock_run_manager(snapshot=snapshot)
    profile_svc = _mock_profile_svc(None)
    search_svc = _mock_search_config_svc()

    async with _build_client(test_app, user, profile_svc, search_svc, mgr) as c:
        resp = await c.get(f"/run/{snapshot.run_id}/status", cookies={"session_token": "valid"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending"
    assert body["result"] is None
    assert body["error"] is None
    assert body["run_id"] == str(snapshot.run_id)


@pytest.mark.asyncio
async def test_get_status_running(test_app):
    user = _make_user()
    snapshot = _make_snapshot(user_id=user.id, status="running")
    mgr = _mock_run_manager(snapshot=snapshot)
    profile_svc = _mock_profile_svc(None)
    search_svc = _mock_search_config_svc()

    async with _build_client(test_app, user, profile_svc, search_svc, mgr) as c:
        resp = await c.get(f"/run/{snapshot.run_id}/status", cookies={"session_token": "valid"})

    assert resp.status_code == 200
    assert resp.json()["status"] == "running"


@pytest.mark.asyncio
async def test_get_status_completed_includes_result(test_app):
    user = _make_user()
    result = _make_result(jobs_found=10, jobs_stored=7)
    snapshot = _make_snapshot(
        user_id=user.id,
        status="completed",
        result=result,
        completed_at=datetime.now(timezone.utc),
    )
    mgr = _mock_run_manager(snapshot=snapshot)
    profile_svc = _mock_profile_svc(None)
    search_svc = _mock_search_config_svc()

    async with _build_client(test_app, user, profile_svc, search_svc, mgr) as c:
        resp = await c.get(f"/run/{snapshot.run_id}/status", cookies={"session_token": "valid"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["result"]["jobs_found"] == 10
    assert body["result"]["jobs_stored"] == 7
    assert body["result"]["errors"] == []
    assert body["completed_at"] is not None


@pytest.mark.asyncio
async def test_get_status_completed_with_errors_in_result(test_app):
    user = _make_user()
    result = _make_result(errors=("Evaluation failed for 'Job A': timeout",))
    snapshot = _make_snapshot(user_id=user.id, status="completed", result=result)
    mgr = _mock_run_manager(snapshot=snapshot)
    profile_svc = _mock_profile_svc(None)
    search_svc = _mock_search_config_svc()

    async with _build_client(test_app, user, profile_svc, search_svc, mgr) as c:
        resp = await c.get(f"/run/{snapshot.run_id}/status", cookies={"session_token": "valid"})

    body = resp.json()
    assert body["result"]["errors"] == ["Evaluation failed for 'Job A': timeout"]


@pytest.mark.asyncio
async def test_get_status_failed_includes_error_message(test_app):
    user = _make_user()
    snapshot = _make_snapshot(
        user_id=user.id,
        status="failed",
        error="Profile not configured.",
        completed_at=datetime.now(timezone.utc),
    )
    mgr = _mock_run_manager(snapshot=snapshot)
    profile_svc = _mock_profile_svc(None)
    search_svc = _mock_search_config_svc()

    async with _build_client(test_app, user, profile_svc, search_svc, mgr) as c:
        resp = await c.get(f"/run/{snapshot.run_id}/status", cookies={"session_token": "valid"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "failed"
    assert body["error"] == "Profile not configured."
    assert body["result"] is None


# ---------------------------------------------------------------------------
# HTMX — POST /run returns HTML partial
# ---------------------------------------------------------------------------

_HX_HEADERS = {"HX-Request": "true"}


@pytest.mark.asyncio
async def test_post_run_htmx_returns_html_on_success(test_app):
    user = _make_user()
    run_id = uuid4()
    profile_svc = _mock_profile_svc(profile=_make_profile(user.id))
    search_svc = _mock_search_config_svc(all_configs=[_make_search_config(user.id)])
    mgr = _mock_run_manager(run_id=run_id)

    async with _build_client(test_app, user, profile_svc, search_svc, mgr) as c:
        resp = await c.post("/run", cookies={"session_token": "valid"}, headers=_HX_HEADERS)

    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert str(run_id) in resp.text
    assert "run-widget" in resp.text


@pytest.mark.asyncio
async def test_post_run_htmx_returns_error_partial_on_missing_profile(test_app):
    user = _make_user()
    profile_svc = _mock_profile_svc(profile=None)
    search_svc = _mock_search_config_svc()
    mgr = _mock_run_manager()

    async with _build_client(test_app, user, profile_svc, search_svc, mgr) as c:
        resp = await c.post("/run", cookies={"session_token": "valid"}, headers=_HX_HEADERS)

    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Profile not configured" in resp.text


@pytest.mark.asyncio
async def test_post_run_htmx_returns_error_partial_on_conflict(test_app):
    user = _make_user()
    profile_svc = _mock_profile_svc(profile=_make_profile(user.id))
    search_svc = _mock_search_config_svc(all_configs=[_make_search_config(user.id)])
    mgr = _mock_run_manager(active_error=RunActiveError("Already running."))

    async with _build_client(test_app, user, profile_svc, search_svc, mgr) as c:
        resp = await c.post("/run", cookies={"session_token": "valid"}, headers=_HX_HEADERS)

    assert resp.status_code == 200
    assert "Already running" in resp.text


# ---------------------------------------------------------------------------
# HTMX — GET /run/{run_id}/status returns HTML partial
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_status_htmx_returns_html(test_app):
    user = _make_user()
    snapshot = _make_snapshot(user_id=user.id, status="running")
    mgr = _mock_run_manager(snapshot=snapshot)
    profile_svc = _mock_profile_svc(None)
    search_svc = _mock_search_config_svc()

    async with _build_client(test_app, user, profile_svc, search_svc, mgr) as c:
        resp = await c.get(
            f"/run/{snapshot.run_id}/status",
            cookies={"session_token": "valid"},
            headers=_HX_HEADERS,
        )

    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "run-widget" in resp.text


@pytest.mark.asyncio
async def test_get_status_htmx_completed_has_no_poll_trigger(test_app):
    user = _make_user()
    result = _make_result()
    snapshot = _make_snapshot(user_id=user.id, status="completed", result=result)
    mgr = _mock_run_manager(snapshot=snapshot)
    profile_svc = _mock_profile_svc(None)
    search_svc = _mock_search_config_svc()

    async with _build_client(test_app, user, profile_svc, search_svc, mgr) as c:
        resp = await c.get(
            f"/run/{snapshot.run_id}/status",
            cookies={"session_token": "valid"},
            headers=_HX_HEADERS,
        )

    assert resp.status_code == 200
    assert "hx-trigger" not in resp.text


@pytest.mark.asyncio
async def test_get_status_htmx_running_has_poll_trigger(test_app):
    user = _make_user()
    snapshot = _make_snapshot(user_id=user.id, status="running")
    mgr = _mock_run_manager(snapshot=snapshot)
    profile_svc = _mock_profile_svc(None)
    search_svc = _mock_search_config_svc()

    async with _build_client(test_app, user, profile_svc, search_svc, mgr) as c:
        resp = await c.get(
            f"/run/{snapshot.run_id}/status",
            cookies={"session_token": "valid"},
            headers=_HX_HEADERS,
        )

    assert "hx-trigger" in resp.text
    assert "every 2s" in resp.text


@pytest.mark.asyncio
async def test_get_status_htmx_404_returns_error_partial(test_app):
    user = _make_user()
    mgr = _mock_run_manager(snapshot=None)
    profile_svc = _mock_profile_svc(None)
    search_svc = _mock_search_config_svc()

    async with _build_client(test_app, user, profile_svc, search_svc, mgr) as c:
        resp = await c.get(
            f"/run/{uuid4()}/status",
            cookies={"session_token": "valid"},
            headers=_HX_HEADERS,
        )

    assert resp.status_code == 200
    assert "Run not found" in resp.text


# ---------------------------------------------------------------------------
# GET / — dashboard
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dashboard_redirects_unauthenticated(test_app):
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth(None)
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test", follow_redirects=False
    ) as c:
        resp = await c.get("/")
    assert resp.status_code == 302
    assert "/auth/login" in resp.headers["location"]


@pytest.mark.asyncio
async def test_dashboard_renders_for_authenticated_user(test_app):
    user = _make_user()
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth(user)
    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as c:
        resp = await c.get("/", cookies={"session_token": "valid"})
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert "Dashboard" in resp.text
    assert "run-widget" in resp.text
