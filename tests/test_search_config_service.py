"""Unit tests for SearchConfigService — SearchConfigRepository is mocked."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from repositories.search_config import SearchConfigRow
from services.search_config import SearchConfigData, SearchConfigError, SearchConfigService


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_row(**overrides) -> SearchConfigRow:
    defaults = dict(
        id=uuid4(),
        user_id=uuid4(),
        platform="upwork",
        query="unity developer",
        filters={"jobType": ["fixed", "hourly"]},
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return SearchConfigRow(**defaults)


def _make_service(repo=None) -> SearchConfigService:
    return SearchConfigService(search_config_repo=repo or MagicMock())


def _valid_data(**overrides) -> SearchConfigData:
    defaults = dict(
        platform="upwork",
        query="unity developer",
        filters={"jobType": ["fixed", "hourly"]},
    )
    defaults.update(overrides)
    return SearchConfigData(**defaults)


# ── get_all ───────────────────────────────────────────────────────────────────

async def test_get_all_delegates_to_repo():
    repo = MagicMock()
    user_id = uuid4()
    rows = [_make_row(user_id=user_id), _make_row(user_id=user_id, platform="linkedin")]
    repo.find_by_user_id = AsyncMock(return_value=rows)

    svc = _make_service(repo)
    result = await svc.get_all(user_id)

    assert result == rows
    repo.find_by_user_id.assert_awaited_once_with(user_id)


async def test_get_all_returns_empty_list_when_no_configs():
    repo = MagicMock()
    repo.find_by_user_id = AsyncMock(return_value=[])

    svc = _make_service(repo)
    result = await svc.get_all(uuid4())

    assert result == []


# ── get_by_platform ───────────────────────────────────────────────────────────

async def test_get_by_platform_returns_row_when_found():
    repo = MagicMock()
    user_id = uuid4()
    row = _make_row(user_id=user_id, platform="upwork")
    repo.find_by_user_and_platform = AsyncMock(return_value=row)

    svc = _make_service(repo)
    result = await svc.get_by_platform(user_id, "upwork")

    assert result is row
    repo.find_by_user_and_platform.assert_awaited_once_with(user_id, "upwork")


async def test_get_by_platform_returns_none_when_missing():
    repo = MagicMock()
    repo.find_by_user_and_platform = AsyncMock(return_value=None)

    svc = _make_service(repo)
    result = await svc.get_by_platform(uuid4(), "upwork")

    assert result is None


# ── upsert ────────────────────────────────────────────────────────────────────

async def test_upsert_calls_repo_with_correct_data():
    repo = MagicMock()
    user_id = uuid4()
    row = _make_row(user_id=user_id)
    repo.upsert = AsyncMock(return_value=row)

    svc = _make_service(repo)
    data = _valid_data()
    result = await svc.upsert(user_id, data)

    assert result is row
    repo.upsert.assert_awaited_once_with(
        user_id=user_id,
        platform="upwork",
        query="unity developer",
        filters={"jobType": ["fixed", "hourly"]},
    )


async def test_upsert_converts_empty_query_to_none():
    repo = MagicMock()
    row = _make_row(query=None)
    repo.upsert = AsyncMock(return_value=row)

    svc = _make_service(repo)
    await svc.upsert(uuid4(), _valid_data(query=""))

    call_kwargs = repo.upsert.call_args.kwargs
    assert call_kwargs["query"] is None


async def test_upsert_accepts_empty_filters():
    repo = MagicMock()
    row = _make_row(filters={})
    repo.upsert = AsyncMock(return_value=row)

    svc = _make_service(repo)
    await svc.upsert(uuid4(), _valid_data(filters={}))

    call_kwargs = repo.upsert.call_args.kwargs
    assert call_kwargs["filters"] == {}


async def test_upsert_raises_for_unknown_platform():
    svc = _make_service()

    with pytest.raises(SearchConfigError, match="Unknown platform"):
        await svc.upsert(uuid4(), _valid_data(platform="fiverr"))


async def test_upsert_raises_when_filters_not_a_dict():
    svc = _make_service()

    with pytest.raises(SearchConfigError, match="JSON object"):
        await svc.upsert(uuid4(), SearchConfigData(platform="upwork", query="dev", filters="bad"))  # type: ignore[arg-type]


async def test_upsert_accepts_none_query():
    repo = MagicMock()
    row = _make_row(query=None)
    repo.upsert = AsyncMock(return_value=row)

    svc = _make_service(repo)
    result = await svc.upsert(uuid4(), _valid_data(query=None))

    assert result is row


# ── delete ────────────────────────────────────────────────────────────────────

async def test_delete_delegates_to_repo():
    repo = MagicMock()
    repo.delete = AsyncMock(return_value=None)
    config_id = uuid4()

    svc = _make_service(repo)
    await svc.delete(config_id)

    repo.delete.assert_awaited_once_with(config_id)
