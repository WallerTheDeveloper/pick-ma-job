"""Integration tests for POST /api/run — platform JSON body validation."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from api.csrf import require_csrf
from api.deps import (
    get_current_user,
    get_profile_service,
    get_run_manager,
    get_search_config_service,
)
from repositories.user import UserRow
from services.run_manager import RunActiveError


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
    app.state.run_manager = MagicMock()
    return app


@pytest.fixture
async def client(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        yield c


def _make_user(email: str = "user@example.com") -> UserRow:
    return UserRow(id=uuid4(), email=email, created_at=datetime.now(timezone.utc), last_login=None)


def _fake_search_config(platform: str):
    """Return a minimal search config dict-like object for the given platform."""
    cfg = MagicMock()
    cfg.platform = platform
    return cfg


def _setup_overrides(test_app, *, user=None, profile=None, run_id=None,
                     configs_by_platform=None, all_configs=None):
    """
    Set up dependency_overrides for a pipeline test.

    configs_by_platform: dict[str, config | None] — returned by get_by_platform
    all_configs: list — returned by get_all; defaults to list of configs_by_platform values
    """
    if user is None:
        user = _make_user()

    # Profile service
    profile_svc = MagicMock()
    profile_svc.get_or_default = AsyncMock(return_value=profile if profile is not None else MagicMock())

    # Search config service
    search_config_svc = MagicMock()
    cbp = configs_by_platform or {}
    search_config_svc.get_by_platform = AsyncMock(side_effect=lambda uid, p: cbp.get(p))
    if all_configs is not None:
        search_config_svc.get_all = AsyncMock(return_value=all_configs)
    else:
        search_config_svc.get_all = AsyncMock(return_value=list(cbp.values()))

    # Run manager
    run_mgr = MagicMock()
    run_mgr.start_run = AsyncMock(return_value=run_id or uuid4())

    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[require_csrf] = lambda: None
    test_app.dependency_overrides[get_profile_service] = lambda: profile_svc
    test_app.dependency_overrides[get_search_config_service] = lambda: search_config_svc
    test_app.dependency_overrides[get_run_manager] = lambda: run_mgr

    return run_mgr, search_config_svc


# ── Happy paths ───────────────────────────────────────────────────────────────

async def test_start_run_both_platforms(client, test_app):
    """{"platforms": ["upwork", "linkedin"]} kicks off a run for both platforms."""
    run_id = uuid4()
    run_mgr, _ = _setup_overrides(
        test_app,
        run_id=run_id,
        configs_by_platform={
            "upwork": _fake_search_config("upwork"),
            "linkedin": _fake_search_config("linkedin"),
        },
    )

    resp = await client.post(
        "/api/run",
        json={"platforms": ["upwork", "linkedin"]},
        cookies={"session_token": "tok"},
    )
    test_app.dependency_overrides.clear()

    assert resp.status_code == 202
    assert resp.json()["run_id"] == str(run_id)
    run_mgr.start_run.assert_called_once()
    called_platforms = run_mgr.start_run.call_args[0][1]
    assert sorted(called_platforms) == ["linkedin", "upwork"]


async def test_start_run_single_platform(client, test_app):
    """{"platforms": ["linkedin"]} runs only LinkedIn."""
    run_id = uuid4()
    run_mgr, _ = _setup_overrides(
        test_app,
        run_id=run_id,
        configs_by_platform={"linkedin": _fake_search_config("linkedin")},
    )

    resp = await client.post(
        "/api/run",
        json={"platforms": ["linkedin"]},
        cookies={"session_token": "tok"},
    )
    test_app.dependency_overrides.clear()

    assert resp.status_code == 202
    called_platforms = run_mgr.start_run.call_args[0][1]
    assert called_platforms == ["linkedin"]


async def test_start_run_empty_body_runs_all(client, test_app):
    """Empty body {} or {"platforms": null} runs all configured platforms."""
    run_id = uuid4()
    run_mgr, _ = _setup_overrides(
        test_app,
        run_id=run_id,
        all_configs=[_fake_search_config("upwork"), _fake_search_config("linkedin")],
    )

    resp = await client.post(
        "/api/run",
        json={},
        cookies={"session_token": "tok"},
    )
    test_app.dependency_overrides.clear()

    assert resp.status_code == 202
    called_platforms = run_mgr.start_run.call_args[0][1]
    assert called_platforms is None


async def test_start_run_null_platforms_runs_all(client, test_app):
    """{"platforms": null} runs all configured platforms."""
    run_id = uuid4()
    run_mgr, _ = _setup_overrides(
        test_app,
        run_id=run_id,
        all_configs=[_fake_search_config("upwork")],
    )

    resp = await client.post(
        "/api/run",
        json={"platforms": None},
        cookies={"session_token": "tok"},
    )
    test_app.dependency_overrides.clear()

    assert resp.status_code == 202
    called_platforms = run_mgr.start_run.call_args[0][1]
    assert called_platforms is None


# ── Validation errors ─────────────────────────────────────────────────────────

async def test_start_run_unknown_platform_returns_422(client, test_app):
    """{"platforms": ["notaplatform"]} returns 422."""
    _setup_overrides(test_app, configs_by_platform={})

    resp = await client.post(
        "/api/run",
        json={"platforms": ["notaplatform"]},
        cookies={"session_token": "tok"},
    )
    test_app.dependency_overrides.clear()

    assert resp.status_code == 422
    assert "notaplatform" in resp.json()["detail"].lower() or "Unknown" in resp.json()["detail"]


async def test_start_run_platform_not_configured_returns_400(client, test_app):
    """Requesting a valid platform without a search config returns 400."""
    _setup_overrides(
        test_app,
        configs_by_platform={"linkedin": None},  # config missing
    )

    resp = await client.post(
        "/api/run",
        json={"platforms": ["linkedin"]},
        cookies={"session_token": "tok"},
    )
    test_app.dependency_overrides.clear()

    assert resp.status_code == 400
    assert "linkedin" in resp.json()["detail"]


async def test_start_run_no_configs_at_all_returns_400(client, test_app):
    """When no configs exist and platforms=null, return 400 with helpful message."""
    _setup_overrides(test_app, all_configs=[])

    resp = await client.post(
        "/api/run",
        json={},
        cookies={"session_token": "tok"},
    )
    test_app.dependency_overrides.clear()

    assert resp.status_code == 400
    assert "search config" in resp.json()["detail"].lower()


async def test_start_run_conflict_when_run_active(client, test_app):
    """Returns 409 when another run is already active."""
    run_mgr, _ = _setup_overrides(
        test_app,
        all_configs=[_fake_search_config("upwork")],
    )
    run_mgr.start_run.side_effect = RunActiveError("A run is already in progress.")

    resp = await client.post(
        "/api/run",
        json={},
        cookies={"session_token": "tok"},
    )
    test_app.dependency_overrides.clear()

    assert resp.status_code == 409
    assert "already" in resp.json()["detail"].lower()


# ── Cancel run endpoint ──────────────────────────────────────────────────────

async def test_cancel_run_returns_200_for_running_run(client, test_app):
    """POST /api/run/{run_id}/cancel returns 200 when run is active."""
    run_id = uuid4()
    run_mgr, _ = _setup_overrides(test_app, all_configs=[_fake_search_config("upwork")])
    run_mgr.cancel_run = AsyncMock()

    resp = await client.post(
        f"/api/run/{run_id}/cancel",
        cookies={"session_token": "tok"},
    )
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    run_mgr.cancel_run.assert_called_once()


async def test_cancel_run_returns_404_for_unknown_run(client, test_app):
    """POST /api/run/{run_id}/cancel returns 404 when run doesn't exist."""
    from core.exceptions import NotFoundError
    from services.run_manager import RunNotActiveError

    run_mgr, _ = _setup_overrides(test_app, all_configs=[_fake_search_config("upwork")])
    run_mgr.cancel_run = AsyncMock(side_effect=NotFoundError("Run not found."))

    resp = await client.post(
        f"/api/run/{uuid4()}/cancel",
        cookies={"session_token": "tok"},
    )
    test_app.dependency_overrides.clear()

    assert resp.status_code == 404


async def test_cancel_run_returns_409_for_completed_run(client, test_app):
    """POST /api/run/{run_id}/cancel returns 409 when run is already completed."""
    from services.run_manager import RunNotActiveError

    run_mgr, _ = _setup_overrides(test_app, all_configs=[_fake_search_config("upwork")])
    run_mgr.cancel_run = AsyncMock(side_effect=RunNotActiveError("Run is not active."))

    resp = await client.post(
        f"/api/run/{uuid4()}/cancel",
        cookies={"session_token": "tok"},
    )
    test_app.dependency_overrides.clear()

    assert resp.status_code == 409
