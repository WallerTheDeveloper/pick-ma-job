"""Integration tests for search config routes using httpx.AsyncClient + FastAPI test app.

SearchConfigService and AuthService are overridden via dependency_overrides.
No real PostgreSQL required.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.templating import Jinja2Templates
from httpx import ASGITransport, AsyncClient

from api.deps import get_auth_service, get_search_config_service
from repositories.search_config import SearchConfigRow
from repositories.user import UserRow
from services.search_config import SearchConfigData, SearchConfigError


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
    return UserRow(
        id=uuid4(),
        email="user@example.com",
        created_at=datetime.now(timezone.utc),
        last_login=None,
    )


def _make_config_row(user_id=None, **overrides) -> SearchConfigRow:
    defaults = dict(
        id=uuid4(),
        user_id=user_id or uuid4(),
        platform="upwork",
        query="unity developer",
        filters={"jobType": ["fixed", "hourly"]},
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return SearchConfigRow(**defaults)


def _mock_auth_service(user: UserRow | None = None) -> MagicMock:
    svc = MagicMock()
    svc.get_user_from_session = AsyncMock(return_value=user)
    return svc


def _mock_search_config_service(
    configs: list[SearchConfigRow] | None = None,
    upsert_result: SearchConfigRow | None = None,
    upsert_error: SearchConfigError | None = None,
    delete_result: bool = True,
) -> MagicMock:
    svc = MagicMock()
    svc.get_all = AsyncMock(return_value=configs or [])
    svc.delete = AsyncMock(return_value=delete_result)
    if upsert_error:
        svc.upsert = AsyncMock(side_effect=upsert_error)
    else:
        svc.upsert = AsyncMock(return_value=upsert_result)
    return svc


# ── GET /search-config ────────────────────────────────────────────────────────

async def test_get_page_unauthenticated_returns_401(client, test_app):
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=None)
    resp = await client.get("/search-config")
    test_app.dependency_overrides.clear()

    assert resp.status_code == 401


async def test_get_page_empty_state(client, test_app):
    user = _make_user()
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_search_config_service] = lambda: _mock_search_config_service(configs=[])

    client.cookies.set("session_token", "valid-token")
    resp = await client.get("/search-config")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert b"No platforms configured yet" in resp.content


async def test_get_page_shows_existing_configs(client, test_app):
    user = _make_user()
    configs = [
        _make_config_row(user_id=user.id, platform="upwork", query="unity developer"),
        _make_config_row(user_id=user.id, platform="linkedin", query="AR developer"),
    ]
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_search_config_service] = lambda: _mock_search_config_service(configs=configs)

    client.cookies.set("session_token", "valid-token")
    resp = await client.get("/search-config")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert b"upwork" in resp.content
    assert b"unity developer" in resp.content
    assert b"linkedin" in resp.content
    assert b"AR developer" in resp.content


async def test_get_page_shows_platform_select(client, test_app):
    user = _make_user()
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_search_config_service] = lambda: _mock_search_config_service()

    client.cookies.set("session_token", "valid-token")
    resp = await client.get("/search-config")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert b'name="platform"' in resp.content
    assert b'name="query"' in resp.content
    assert b'name="filters_json"' in resp.content


# ── POST /search-config ───────────────────────────────────────────────────────

async def test_post_unauthenticated_returns_401(client, test_app):
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=None)
    resp = await client.post("/search-config", data={"platform": "upwork"})
    test_app.dependency_overrides.clear()

    assert resp.status_code == 401


async def test_post_success_shows_saved_banner(client, test_app):
    user = _make_user()
    row = _make_config_row(user_id=user.id)
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_search_config_service] = lambda: _mock_search_config_service(
        configs=[row], upsert_result=row
    )

    client.cookies.set("session_token", "valid-token")
    resp = await client.post("/search-config", data={
        "platform": "upwork",
        "query": "unity developer",
        "filters_json": '{"jobType": ["fixed"]}',
    })
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert b"Search config saved" in resp.content


async def test_post_invalid_json_filters_returns_422(client, test_app):
    user = _make_user()
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_search_config_service] = lambda: _mock_search_config_service()

    client.cookies.set("session_token", "valid-token")
    resp = await client.post("/search-config", data={
        "platform": "upwork",
        "query": "unity developer",
        "filters_json": "{not valid json",
    })
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 422
    assert b"Filters must be valid JSON" in resp.content


async def test_post_service_error_returns_422(client, test_app):
    user = _make_user()
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_search_config_service] = lambda: _mock_search_config_service(
        upsert_error=SearchConfigError("Unknown platform 'fiverr'.")
    )

    client.cookies.set("session_token", "valid-token")
    resp = await client.post("/search-config", data={"platform": "fiverr"})
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 422
    assert b"fiverr" in resp.content


async def test_post_empty_filters_passes_empty_dict(client, test_app):
    user = _make_user()
    row = _make_config_row(user_id=user.id, filters={})
    captured = {}

    async def _mock_upsert(user_id, data):
        captured["data"] = data
        return row

    svc = _mock_search_config_service(configs=[row], upsert_result=row)
    svc.upsert = _mock_upsert

    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_search_config_service] = lambda: svc

    client.cookies.set("session_token", "valid-token")
    await client.post("/search-config", data={"platform": "upwork", "filters_json": ""})
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert captured["data"].filters == {}


async def test_post_strips_whitespace_from_query(client, test_app):
    user = _make_user()
    row = _make_config_row(user_id=user.id)
    captured = {}

    async def _mock_upsert(user_id, data):
        captured["data"] = data
        return row

    svc = _mock_search_config_service(configs=[row])
    svc.upsert = _mock_upsert

    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_search_config_service] = lambda: svc

    client.cookies.set("session_token", "valid-token")
    await client.post("/search-config", data={"platform": "upwork", "query": "  unity developer  "})
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert captured["data"].query == "unity developer"


async def test_post_empty_query_becomes_none(client, test_app):
    user = _make_user()
    row = _make_config_row(user_id=user.id, query=None)
    captured = {}

    async def _mock_upsert(user_id, data):
        captured["data"] = data
        return row

    svc = _mock_search_config_service(configs=[row])
    svc.upsert = _mock_upsert

    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_search_config_service] = lambda: svc

    client.cookies.set("session_token", "valid-token")
    await client.post("/search-config", data={"platform": "upwork", "query": ""})
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert captured["data"].query is None


async def test_post_passes_parsed_filters_to_service(client, test_app):
    user = _make_user()
    row = _make_config_row(user_id=user.id)
    captured = {}

    async def _mock_upsert(user_id, data):
        captured["data"] = data
        return row

    svc = _mock_search_config_service(configs=[row])
    svc.upsert = _mock_upsert

    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_search_config_service] = lambda: svc

    filters = {"jobType": ["fixed", "hourly"], "paymentVerified": True}
    client.cookies.set("session_token", "valid-token")
    await client.post("/search-config", data={
        "platform": "upwork",
        "filters_json": json.dumps(filters),
    })
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert captured["data"].filters == filters


# ── DELETE /search-config/{config_id} ────────────────────────────────────────

async def test_delete_unauthenticated_returns_401(client, test_app):
    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=None)
    resp = await client.delete(f"/search-config/{uuid4()}")
    test_app.dependency_overrides.clear()

    assert resp.status_code == 401


async def test_delete_calls_service_and_returns_empty_body(client, test_app):
    user = _make_user()
    config_id = uuid4()
    svc = _mock_search_config_service()

    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_search_config_service] = lambda: svc

    client.cookies.set("session_token", "valid-token")
    resp = await client.delete(f"/search-config/{config_id}")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.content == b""
    svc.delete.assert_awaited_once_with(config_id, user.id)


async def test_delete_another_users_config_returns_404(client, test_app):
    user = _make_user()
    config_id = uuid4()
    svc = _mock_search_config_service(delete_result=False)

    test_app.dependency_overrides[get_auth_service] = lambda: _mock_auth_service(user=user)
    test_app.dependency_overrides[get_search_config_service] = lambda: svc

    client.cookies.set("session_token", "valid-token")
    resp = await client.delete(f"/search-config/{config_id}")
    client.cookies.clear()
    test_app.dependency_overrides.clear()

    assert resp.status_code == 404
