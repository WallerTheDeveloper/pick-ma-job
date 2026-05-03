"""Unit tests for services.auto_list_service.AutoListService.

All external I/O is mocked — only the service logic is tested.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from repositories.job_list import JobListRow
from services.auto_list_service import AutoListService

_USER_ID = uuid4()
_RUN_ID = uuid4()


def _make_list_row(name: str, list_id=None) -> JobListRow:
    return JobListRow(
        id=list_id or uuid4(),
        user_id=_USER_ID,
        name=name,
        created_at=datetime(2026, 5, 3, tzinfo=timezone.utc),
    )


# ---------------------------------------------------------------------------
# create_for_run — happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_for_run_creates_new_list():
    job_list_repo = AsyncMock()
    job_list_repo.find_by_user.return_value = []
    job_list_repo.create.return_value = _make_list_row("upwork-2026-05-03-abcd1234")

    svc = AutoListService(job_list_repo)
    job_ids = [uuid4(), uuid4()]

    result = await svc.create_for_run(_USER_ID, _RUN_ID, job_ids, "upwork")

    assert result is not None
    job_list_repo.create.assert_awaited_once()
    job_list_repo.add_items.assert_awaited_once()
    # Verify name format: {platform}-{date}-{run_id[:8]}
    call_args = job_list_repo.create.call_args
    list_name = call_args[0][1]
    assert list_name.startswith("upwork-")
    assert str(_RUN_ID)[:8] in list_name


@pytest.mark.asyncio
async def test_create_for_run_returns_list_id():
    expected_id = uuid4()
    job_list_repo = AsyncMock()
    job_list_repo.find_by_user.return_value = []
    job_list_repo.create.return_value = _make_list_row("upwork-2026-05-03-abcd1234", list_id=expected_id)

    svc = AutoListService(job_list_repo)
    result = await svc.create_for_run(_USER_ID, _RUN_ID, [uuid4()], "upwork")

    assert result == expected_id


# ---------------------------------------------------------------------------
# create_for_run — idempotency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_for_run_appends_to_existing_list():
    existing_list = _make_list_row(f"upwork-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-{str(_RUN_ID)[:8]}")
    job_list_repo = AsyncMock()
    job_list_repo.find_by_user.return_value = [existing_list]

    svc = AutoListService(job_list_repo)
    job_ids = [uuid4(), uuid4()]

    result = await svc.create_for_run(_USER_ID, _RUN_ID, job_ids, "upwork")

    assert result == existing_list.id
    # Should NOT create a new list
    job_list_repo.create.assert_not_called()
    # Should append items to existing list
    job_list_repo.add_items.assert_awaited_once_with(existing_list.id, job_ids)


@pytest.mark.asyncio
async def test_create_for_run_different_runs_create_different_lists():
    """Two runs on the same day should produce distinct lists."""
    run_id_1 = uuid4()
    run_id_2 = uuid4()

    job_list_repo = AsyncMock()
    job_list_repo.find_by_user.return_value = []
    job_list_repo.create.side_effect = [
        _make_list_row(f"upwork-2026-05-03-{str(run_id_1)[:8]}"),
        _make_list_row(f"upwork-2026-05-03-{str(run_id_2)[:8]}"),
    ]

    svc = AutoListService(job_list_repo)

    await svc.create_for_run(_USER_ID, run_id_1, [uuid4()], "upwork")
    await svc.create_for_run(_USER_ID, run_id_2, [uuid4()], "upwork")

    assert job_list_repo.create.call_count == 2
    # Verify different names
    name_1 = job_list_repo.create.call_args_list[0][0][1]
    name_2 = job_list_repo.create.call_args_list[1][0][1]
    assert name_1 != name_2


# ---------------------------------------------------------------------------
# create_for_run — edge cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_for_run_empty_ids_returns_none():
    job_list_repo = AsyncMock()
    svc = AutoListService(job_list_repo)

    result = await svc.create_for_run(_USER_ID, _RUN_ID, [], "upwork")

    assert result is None
    job_list_repo.create.assert_not_called()
    job_list_repo.add_items.assert_not_called()


@pytest.mark.asyncio
async def test_create_for_run_different_platforms():
    """Different platforms in the same run produce different lists."""
    job_list_repo = AsyncMock()
    job_list_repo.find_by_user.return_value = []
    job_list_repo.create.side_effect = [
        _make_list_row(f"upwork-2026-05-03-{str(_RUN_ID)[:8]}"),
        _make_list_row(f"linkedin-2026-05-03-{str(_RUN_ID)[:8]}"),
    ]

    svc = AutoListService(job_list_repo)

    await svc.create_for_run(_USER_ID, _RUN_ID, [uuid4()], "upwork")
    await svc.create_for_run(_USER_ID, _RUN_ID, [uuid4()], "linkedin")

    assert job_list_repo.create.call_count == 2
    name_1 = job_list_repo.create.call_args_list[0][0][1]
    name_2 = job_list_repo.create.call_args_list[1][0][1]
    assert name_1.startswith("upwork-")
    assert name_2.startswith("linkedin-")


@pytest.mark.asyncio
async def test_create_for_run_name_includes_date():
    job_list_repo = AsyncMock()
    job_list_repo.find_by_user.return_value = []
    job_list_repo.create.return_value = _make_list_row("upwork-2026-05-03-abcd1234")

    svc = AutoListService(job_list_repo)
    await svc.create_for_run(_USER_ID, _RUN_ID, [uuid4()], "upwork")

    list_name = job_list_repo.create.call_args[0][1]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    assert today in list_name
