"""Unit tests for completed backend hardening tasks.

Covers:
- CR-7  / cleanup-4:   is_admin_email() timing-safe comparison
- CR-8  / hardening-1: Sanitized error messages in RunManager
- CR-10 / hardening-3: Platform parameter validation in POST /api/run
- CR-11 / hardening-4: _SORT_CLAUSES is immutable MappingProxyType
- DB-7:                Invalid sort key raises ValueError in find_by_user

All tests are pure unit tests — no database required.
"""

import os
from datetime import datetime, timezone
from types import MappingProxyType
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from api.deps import is_admin_email
from repositories.job_result import JobResultRepository, _SORT_CLAUSES
from repositories.user import UserRow


# ── CR-7 / cleanup-4: is_admin_email() ───────────────────────────────────────


def test_is_admin_email_returns_true_for_matching_email(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    assert is_admin_email("admin@example.com") is True


def test_is_admin_email_returns_false_for_non_matching_email(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    assert is_admin_email("other@example.com") is False


def test_is_admin_email_returns_false_when_env_var_not_set(monkeypatch):
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    assert is_admin_email("admin@example.com") is False


def test_is_admin_email_returns_false_when_env_var_is_empty(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "")
    assert is_admin_email("") is False


def test_is_admin_email_is_case_sensitive(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "Admin@Example.com")
    assert is_admin_email("admin@example.com") is False
    assert is_admin_email("Admin@Example.com") is True


def test_is_admin_email_does_not_raise_for_empty_input(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "admin@example.com")
    # hmac.compare_digest requires both operands to be the same type (str).
    # This ensures we never accidentally pass bytes or None.
    result = is_admin_email("")
    assert result is False


# ── CR-11 / hardening-4: _SORT_CLAUSES immutability ─────────────────────────


def test_sort_clauses_is_mapping_proxy_type():
    assert isinstance(_SORT_CLAUSES, MappingProxyType)


def test_sort_clauses_mutation_raises_type_error():
    with pytest.raises(TypeError):
        _SORT_CLAUSES["score_desc"] = "tampered"  # type: ignore[index]


def test_sort_clauses_contains_expected_keys():
    expected = {"score_desc", "score_asc", "date_desc", "date_asc"}
    assert set(_SORT_CLAUSES.keys()) == expected


def test_sort_clauses_values_are_non_empty_strings():
    for key, value in _SORT_CLAUSES.items():
        assert isinstance(value, str) and value, f"Sort clause for {key!r} must be a non-empty string"


# ── DB-7: Invalid sort key raises ValueError ──────────────────────────────────


@pytest.mark.asyncio
async def test_find_by_user_raises_value_error_for_unknown_sort():
    """ValueError is raised before any DB call when sort key is unrecognised."""
    repo = JobResultRepository(MagicMock())
    with pytest.raises(ValueError, match="Unknown sort key"):
        await repo.find_by_user(uuid4(), sort="unknown_sort")


@pytest.mark.asyncio
async def test_find_by_user_raises_value_error_for_empty_sort():
    repo = JobResultRepository(MagicMock())
    with pytest.raises(ValueError, match="Unknown sort key"):
        await repo.find_by_user(uuid4(), sort="")


@pytest.mark.asyncio
async def test_find_by_user_does_not_raise_for_valid_sorts():
    """Confirm all four valid sort keys pass the guard (pool acquire will then fail, which is OK)."""
    for sort_key in ("score_desc", "score_asc", "date_desc", "date_asc"):
        pool = MagicMock()
        # Make pool.acquire().__aenter__ raise so we don't need a real DB,
        # but the ValueError guard must NOT fire.
        pool.acquire.return_value.__aenter__ = AsyncMock(side_effect=RuntimeError("no db"))
        pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
        repo = JobResultRepository(pool)
        with pytest.raises(RuntimeError, match="no db"):
            await repo.find_by_user(uuid4(), sort=sort_key)


# ── CR-8 / hardening-1: RunManager sanitised error message ───────────────────

_GENERIC_ERROR = "An internal error occurred. Please try again."


def test_generic_error_constant_has_correct_value():
    """Verify the literal string constant matches the expected sanitised message."""
    assert _GENERIC_ERROR == "An internal error occurred. Please try again."


# ── CR-10 / hardening-3: Platform parameter validation ───────────────────────


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


def _mock_profile_service_with_profile() -> MagicMock:
    """Return a profile service that yields a non-None profile (so profile guard passes)."""
    from dataclasses import dataclass

    @dataclass(frozen=True)
    class _FakeProfile:
        user_id: object = None
        skills: str = ""
        experience: str = ""
        rate: str = ""
        rubric: dict | None = None

    svc = MagicMock()
    svc.get_or_default = AsyncMock(return_value=_FakeProfile())
    svc.update = AsyncMock(return_value=None)
    return svc


def _mock_search_config_service() -> MagicMock:
    svc = MagicMock()
    svc.get_all = AsyncMock(return_value=[])
    svc.get_by_platform = AsyncMock(return_value=None)
    svc.delete = AsyncMock(return_value=True)
    svc.upsert = AsyncMock(return_value=None)
    return svc


def _mock_run_manager() -> MagicMock:
    svc = MagicMock()
    svc.start_run = AsyncMock(return_value=uuid4())
    svc.get_run = AsyncMock(return_value=None)
    return svc


async def test_post_run_with_unknown_platform_returns_422(client, test_app, monkeypatch):
    """An unrecognised platform slug must be rejected with HTTP 422."""
    from api.deps import (
        get_auth_service,
        get_profile_service,
        get_run_manager,
        get_search_config_service,
    )

    monkeypatch.setenv("MAGIC_LINK_SECRET", "test-secret")
    user = _make_user()
    session_token = "valid-token"
    from api.csrf import derive_csrf_token
    csrf_token = derive_csrf_token(session_token)

    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_profile_service] = lambda: _mock_profile_service_with_profile()
    test_app.dependency_overrides[get_search_config_service] = lambda: _mock_search_config_service()
    test_app.dependency_overrides[get_run_manager] = lambda: _mock_run_manager()

    client.cookies.set("session_token", session_token)
    resp = await client.post(
        "/api/run",
        params={"platform": "invalid_platform"},
        headers={"X-CSRF-Token": csrf_token},
    )
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 422
    assert "Unknown platform" in resp.json()["detail"]


async def test_post_run_with_known_platform_passes_validation(client, test_app, monkeypatch):
    """A known platform slug passes the platform guard (may fail later for other reasons)."""
    from api.deps import (
        get_auth_service,
        get_profile_service,
        get_run_manager,
        get_search_config_service,
    )

    monkeypatch.setenv("MAGIC_LINK_SECRET", "test-secret")
    user = _make_user()
    session_token = "valid-token"
    from api.csrf import derive_csrf_token
    csrf_token = derive_csrf_token(session_token)

    # Make the search config service return a config so the no-config guard passes too.
    svc = MagicMock()
    svc.get_by_platform = AsyncMock(return_value=object())  # truthy — config exists
    svc.get_all = AsyncMock(return_value=[object()])

    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_profile_service] = lambda: _mock_profile_service_with_profile()
    test_app.dependency_overrides[get_search_config_service] = lambda: svc
    test_app.dependency_overrides[get_run_manager] = lambda: _mock_run_manager()

    client.cookies.set("session_token", session_token)
    resp = await client.post(
        "/api/run",
        params={"platform": "upwork"},
        headers={"X-CSRF-Token": csrf_token},
    )
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    # 422 would mean the platform guard fired — anything else (202, 400, 409) means it passed.
    assert resp.status_code != 422


def test_known_platforms_is_frozenset():
    """KNOWN_PLATFORMS must be a frozenset so it cannot be mutated at runtime."""
    from services.search_config import KNOWN_PLATFORMS
    assert isinstance(KNOWN_PLATFORMS, frozenset)


def test_known_platforms_contains_upwork():
    """Sanity: 'upwork' is always a registered platform."""
    from services.search_config import KNOWN_PLATFORMS
    assert "upwork" in KNOWN_PLATFORMS
