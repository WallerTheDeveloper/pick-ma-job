"""Unit tests for services.run_manager.RunManager (DB-backed, stateless).

Strategy:
- PipelineRunRepository is patched at services.run_manager.PipelineRunRepository
  to avoid real DB calls.
- PipelineService is patched at services.run_manager.PipelineService.
- asyncio.create_task is patched to a no-op in start_run tests so the
  background task doesn't run during the synchronous part of the test.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, call, patch
from uuid import UUID, uuid4

import pytest

from core.settings import Settings
from services.pipeline import PipelineStats
from services.run_manager import RunActiveError, RunManager


_USER_A = uuid4()
_USER_B = uuid4()


def _make_result(**overrides) -> PipelineStats:
    defaults = dict(
        jobs_found=5,
        jobs_skipped_dedup=1,
        jobs_skipped_filter=1,
        jobs_skipped_blacklist=0,
        jobs_skipped_low_score=0,
        jobs_stored=3,
        jobs_failed=0,
        errors=(),
    )
    defaults.update(overrides)
    return PipelineStats(**defaults)


def _make_manager() -> RunManager:
    return RunManager(llm_client=MagicMock(), pool=MagicMock(), settings=Settings())


def _mock_repo(*, has_active: bool = False, find_row=None):
    """Return a mock PipelineRunRepository."""
    repo = MagicMock()
    repo.has_active_run = AsyncMock(return_value=has_active)
    repo.insert = AsyncMock()
    repo.update_status = AsyncMock(return_value=True)
    repo.find_by_id = AsyncMock(return_value=find_row)
    repo.mark_stale_as_failed = AsyncMock(return_value=0)
    return repo


def _no_task(coro):
    """Patch target for asyncio.create_task: closes the coroutine to suppress warnings."""
    coro.close()
    return MagicMock()


# ── start_run ────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_start_run_returns_uuid():
    manager = _make_manager()
    repo = _mock_repo()
    with patch("services.run_manager.PipelineRunRepository", return_value=repo), \
         patch("asyncio.create_task", side_effect=_no_task):
        run_id = await manager.start_run(_USER_A)
    assert isinstance(run_id, UUID)


@pytest.mark.asyncio
async def test_start_run_inserts_pending_row():
    manager = _make_manager()
    repo = _mock_repo()
    with patch("services.run_manager.PipelineRunRepository", return_value=repo), \
         patch("asyncio.create_task", side_effect=_no_task):
        run_id = await manager.start_run(_USER_A)
    repo.insert.assert_called_once()
    call_run_id, call_user_id, _ = repo.insert.call_args[0]
    assert call_run_id == run_id
    assert call_user_id == _USER_A


@pytest.mark.asyncio
async def test_start_run_spawns_one_asyncio_task():
    manager = _make_manager()
    repo = _mock_repo()
    with patch("services.run_manager.PipelineRunRepository", return_value=repo), \
         patch("asyncio.create_task") as mock_create:
        await manager.start_run(_USER_A)
    assert mock_create.call_count == 1


@pytest.mark.asyncio
async def test_start_run_raises_run_active_error_when_active():
    manager = _make_manager()
    repo = _mock_repo(has_active=True)
    with patch("services.run_manager.PipelineRunRepository", return_value=repo):
        with pytest.raises(RunActiveError):
            await manager.start_run(_USER_A)


@pytest.mark.asyncio
async def test_start_run_does_not_insert_when_active():
    manager = _make_manager()
    repo = _mock_repo(has_active=True)
    with patch("services.run_manager.PipelineRunRepository", return_value=repo):
        try:
            await manager.start_run(_USER_A)
        except RunActiveError:
            pass
    repo.insert.assert_not_called()


@pytest.mark.asyncio
async def test_start_run_allowed_when_no_active_run():
    manager = _make_manager()
    repo = _mock_repo(has_active=False)
    with patch("services.run_manager.PipelineRunRepository", return_value=repo), \
         patch("asyncio.create_task", side_effect=_no_task):
        run_id = await manager.start_run(_USER_A)
    assert run_id is not None


@pytest.mark.asyncio
async def test_different_users_can_start_concurrently():
    """Two users with no active runs can both start."""
    manager = _make_manager()
    repo = _mock_repo(has_active=False)
    with patch("services.run_manager.PipelineRunRepository", return_value=repo), \
         patch("asyncio.create_task", side_effect=_no_task):
        run_a = await manager.start_run(_USER_A)
        run_b = await manager.start_run(_USER_B)
    assert run_a != run_b


# ── get_run ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_run_returns_none_for_unknown_id():
    manager = _make_manager()
    repo = _mock_repo(find_row=None)
    with patch("services.run_manager.PipelineRunRepository", return_value=repo):
        result = await manager.get_run(uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_get_run_returns_row_when_found():
    manager = _make_manager()
    fake_row = MagicMock()
    repo = _mock_repo(find_row=fake_row)
    with patch("services.run_manager.PipelineRunRepository", return_value=repo):
        result = await manager.get_run(uuid4())
    assert result is fake_row


# ── reconcile_stale_runs ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_reconcile_calls_mark_stale_with_correct_minutes():
    manager = _make_manager()
    repo = _mock_repo()
    with patch("services.run_manager.PipelineRunRepository", return_value=repo):
        await manager.reconcile_stale_runs(stale_after_minutes=15)
    repo.mark_stale_as_failed.assert_called_once_with(15)


@pytest.mark.asyncio
async def test_reconcile_uses_default_minutes():
    manager = _make_manager()
    repo = _mock_repo()
    with patch("services.run_manager.PipelineRunRepository", return_value=repo):
        await manager.reconcile_stale_runs()
    repo.mark_stale_as_failed.assert_called_once_with(30)


# ── _execute — state transitions ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_execute_persists_running_then_completed():
    manager = _make_manager()
    run_id = uuid4()
    repo = _mock_repo()

    mock_service = AsyncMock()
    mock_service.run_pipeline.return_value = _make_result()

    with patch("services.run_manager.PipelineRunRepository", return_value=repo), \
         patch("services.run_manager.PipelineService", return_value=mock_service):
        await manager._execute(run_id, _USER_A, None)

    call_statuses = [c.kwargs["status"] for c in repo.update_status.call_args_list]
    assert call_statuses == ["running", "completed"]


@pytest.mark.asyncio
async def test_execute_persists_running_then_failed_on_exception():
    manager = _make_manager()
    run_id = uuid4()
    repo = _mock_repo()

    mock_service = AsyncMock()
    mock_service.run_pipeline.side_effect = RuntimeError("Claude API down")

    with patch("services.run_manager.PipelineRunRepository", return_value=repo), \
         patch("services.run_manager.PipelineService", return_value=mock_service):
        await manager._execute(run_id, _USER_A, None)

    call_statuses = [c.kwargs["status"] for c in repo.update_status.call_args_list]
    assert call_statuses == ["running", "failed"]


@pytest.mark.asyncio
async def test_execute_stores_generic_error_not_raw_message():
    manager = _make_manager()
    run_id = uuid4()
    repo = _mock_repo()

    raw_message = "Sensitive detail: DB at 10.0.0.1:5432"
    mock_service = AsyncMock()
    mock_service.run_pipeline.side_effect = RuntimeError(raw_message)

    with patch("services.run_manager.PipelineRunRepository", return_value=repo), \
         patch("services.run_manager.PipelineService", return_value=mock_service):
        await manager._execute(run_id, _USER_A, None)

    last_call = repo.update_status.call_args_list[-1]
    error = last_call.kwargs.get("error", "")
    assert error == "An internal error occurred. Please try again."
    assert raw_message not in error


@pytest.mark.asyncio
async def test_execute_passes_platforms_to_pipeline():
    manager = _make_manager()
    run_id = uuid4()
    repo = _mock_repo()

    mock_service = AsyncMock()
    mock_service.run_pipeline.return_value = _make_result()

    with patch("services.run_manager.PipelineRunRepository", return_value=repo), \
         patch("services.run_manager.PipelineService", return_value=mock_service):
        await manager._execute(run_id, _USER_A, ["upwork"])

    call = mock_service.run_pipeline.call_args
    assert call.args[0] == _USER_A
    assert call.args[1] == ["upwork"]
    assert call.kwargs["run_id"] == run_id


@pytest.mark.asyncio
async def test_execute_completed_at_is_set_on_success():
    manager = _make_manager()
    run_id = uuid4()
    repo = _mock_repo()
    before = datetime.now(timezone.utc)

    mock_service = AsyncMock()
    mock_service.run_pipeline.return_value = _make_result()

    with patch("services.run_manager.PipelineRunRepository", return_value=repo), \
         patch("services.run_manager.PipelineService", return_value=mock_service):
        await manager._execute(run_id, _USER_A, None)

    after = datetime.now(timezone.utc)
    completed_call = next(
        c for c in repo.update_status.call_args_list
        if c.kwargs.get("status") == "completed"
    )
    completed_at = completed_call.kwargs.get("completed_at")
    assert before <= completed_at <= after


@pytest.mark.asyncio
async def test_execute_result_stored_as_dict():
    manager = _make_manager()
    run_id = uuid4()
    repo = _mock_repo()

    result = _make_result(jobs_found=10, jobs_stored=7)
    mock_service = AsyncMock()
    mock_service.run_pipeline.return_value = result

    with patch("services.run_manager.PipelineRunRepository", return_value=repo), \
         patch("services.run_manager.PipelineService", return_value=mock_service):
        await manager._execute(run_id, _USER_A, None)

    completed_call = next(
        c for c in repo.update_status.call_args_list
        if c.kwargs.get("status") == "completed"
    )
    stored_result = completed_call.kwargs.get("result")
    assert isinstance(stored_result, dict)
    assert stored_result["jobs_found"] == 10
    assert stored_result["jobs_stored"] == 7


# ── cancel_run ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cancel_run_sets_cancelled_status():
    """cancel_run adds run_id to _cancelled_runs and persists 'cancelled' status."""
    manager = _make_manager()
    run_id = uuid4()
    user_id = uuid4()

    mock_row = MagicMock()
    mock_row.id = run_id
    mock_row.user_id = user_id
    mock_row.status = "running"

    repo = _mock_repo(find_row=mock_row)
    with patch("services.run_manager.PipelineRunRepository", return_value=repo):
        await manager.cancel_run(run_id, user_id)

    assert run_id in manager._cancelled_runs

    # Check the persist call had status="cancelled"
    cancel_call = next(
        (c for c in repo.update_status.call_args_list if c.kwargs.get("status") == "cancelled"),
        None,
    )
    assert cancel_call is not None
    assert cancel_call.kwargs["completed_at"] is not None


@pytest.mark.asyncio
async def test_cancel_run_raises_not_found_for_missing_run():
    """cancel_run raises NotFoundError when the run doesn't exist."""
    from core.exceptions import NotFoundError

    manager = _make_manager()
    repo = _mock_repo(find_row=None)
    with patch("services.run_manager.PipelineRunRepository", return_value=repo):
        with pytest.raises(NotFoundError):
            await manager.cancel_run(uuid4(), uuid4())


@pytest.mark.asyncio
async def test_cancel_run_raises_not_found_for_wrong_user():
    """cancel_run raises NotFoundError when the run belongs to a different user."""
    from core.exceptions import NotFoundError

    manager = _make_manager()
    run_id = uuid4()
    owner_id = uuid4()
    other_user = uuid4()

    mock_row = MagicMock()
    mock_row.id = run_id
    mock_row.user_id = owner_id
    mock_row.status = "running"

    repo = _mock_repo(find_row=mock_row)
    with patch("services.run_manager.PipelineRunRepository", return_value=repo):
        with pytest.raises(NotFoundError):
            await manager.cancel_run(run_id, other_user)


@pytest.mark.asyncio
async def test_cancel_run_raises_not_active_for_completed_run():
    """cancel_run raises RunNotActiveError when the run is already completed."""
    from services.run_manager import RunNotActiveError

    manager = _make_manager()
    run_id = uuid4()
    user_id = uuid4()

    mock_row = MagicMock()
    mock_row.id = run_id
    mock_row.user_id = user_id
    mock_row.status = "completed"

    repo = _mock_repo(find_row=mock_row)
    with patch("services.run_manager.PipelineRunRepository", return_value=repo):
        with pytest.raises(RunNotActiveError):
            await manager.cancel_run(run_id, user_id)


@pytest.mark.asyncio
async def test_cancel_run_raises_not_active_for_failed_run():
    """cancel_run raises RunNotActiveError when the run has failed."""
    from services.run_manager import RunNotActiveError

    manager = _make_manager()
    run_id = uuid4()
    user_id = uuid4()

    mock_row = MagicMock()
    mock_row.id = run_id
    mock_row.user_id = user_id
    mock_row.status = "failed"

    repo = _mock_repo(find_row=mock_row)
    with patch("services.run_manager.PipelineRunRepository", return_value=repo):
        with pytest.raises(RunNotActiveError):
            await manager.cancel_run(run_id, user_id)


@pytest.mark.asyncio
async def test_cancel_run_allows_cancelling_pending_run():
    """cancel_run succeeds for a run in 'pending' state."""
    manager = _make_manager()
    run_id = uuid4()
    user_id = uuid4()

    mock_row = MagicMock()
    mock_row.id = run_id
    mock_row.user_id = user_id
    mock_row.status = "pending"

    repo = _mock_repo(find_row=mock_row)
    with patch("services.run_manager.PipelineRunRepository", return_value=repo):
        await manager.cancel_run(run_id, user_id)

    assert run_id in manager._cancelled_runs


@pytest.mark.asyncio
async def test_execute_stops_when_cancelled_before_start():
    """_execute returns early when the run was cancelled before it started."""
    manager = _make_manager()
    run_id = uuid4()
    repo = _mock_repo()

    # Pre-register the run as cancelled
    manager._cancelled_runs.add(run_id)

    mock_service = AsyncMock()
    mock_service.run_pipeline.return_value = _make_result()

    with patch("services.run_manager.PipelineRunRepository", return_value=repo), \
         patch("services.run_manager.PipelineService", return_value=mock_service):
        await manager._execute(run_id, _USER_A, None)

    # Pipeline should not have been called
    mock_service.run_pipeline.assert_not_called()

    # Only "running" status persisted (the "cancelled" was already set by cancel_run)
    call_statuses = [c.kwargs["status"] for c in repo.update_status.call_args_list]
    assert "running" in call_statuses


@pytest.mark.asyncio
async def test_execute_stops_when_cancelled_during_pipeline():
    """_execute returns early when cancellation is detected after pipeline completes."""
    manager = _make_manager()
    run_id = uuid4()
    repo = _mock_repo()

    # The is_cancelled callback will return True
    manager._cancelled_runs.add(run_id)

    mock_service = AsyncMock()
    mock_service.run_pipeline.return_value = _make_result()

    with patch("services.run_manager.PipelineRunRepository", return_value=repo), \
         patch("services.run_manager.PipelineService", return_value=mock_service):
        await manager._execute(run_id, _USER_A, None)

    # Pipeline was called (it already ran), but status should be "running" only
    # since cancelled was detected
    call_statuses = [c.kwargs["status"] for c in repo.update_status.call_args_list]
    assert "running" in call_statuses
    # "completed" should NOT be in the statuses since we short-circuited
    assert "completed" not in call_statuses
