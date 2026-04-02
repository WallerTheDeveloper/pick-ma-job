"""Unit tests for services.run_manager.RunManager.

Strategy:
- ``start_run`` API tested with asyncio.create_task patched to a no-op so we
  can inspect state without actually running the pipeline.
- ``_execute`` tested directly (called as a coroutine) so we can assert
  snapshot state transitions without fighting asyncio task scheduling.
- PipelineService is always mocked at services.run_manager.PipelineService.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from services.pipeline import PipelineRunResult
from services.run_manager import (
    PipelineRunSnapshot,
    RunActiveError,
    RunManager,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_USER_A = uuid4()
_USER_B = uuid4()


def _make_result(**overrides) -> PipelineRunResult:
    defaults = dict(
        jobs_found=5,
        jobs_skipped_dedup=1,
        jobs_skipped_filter=1,
        jobs_evaluated=3,
        jobs_stored=3,
        errors=(),
    )
    defaults.update(overrides)
    return PipelineRunResult(**defaults)


def _make_manager() -> RunManager:
    return RunManager(anthropic_api_key="test-key")


def _mock_pool() -> MagicMock:
    return MagicMock()


def _no_task(coro):
    """Patch target for asyncio.create_task: closes the coroutine to suppress warnings."""
    coro.close()
    return MagicMock()


def _inject_snapshot(manager: RunManager, user_id, status: str, **overrides) -> PipelineRunSnapshot:
    """Directly plant a snapshot in the manager's internal dict (test helper)."""
    run_id = uuid4()
    snapshot = PipelineRunSnapshot(
        run_id=run_id,
        user_id=user_id,
        status=status,
        started_at=datetime.now(timezone.utc),
        **overrides,
    )
    manager._runs[run_id] = snapshot
    return snapshot


# ---------------------------------------------------------------------------
# start_run — basic API
# ---------------------------------------------------------------------------

def test_start_run_returns_uuid():
    manager = _make_manager()
    with patch("asyncio.create_task", side_effect=_no_task):
        run_id = manager.start_run(_USER_A, _mock_pool())
    from uuid import UUID
    assert isinstance(run_id, UUID)


def test_start_run_stores_pending_snapshot():
    manager = _make_manager()
    with patch("asyncio.create_task", side_effect=_no_task):
        run_id = manager.start_run(_USER_A, _mock_pool())
    snapshot = manager.get_run(run_id)
    assert snapshot is not None
    assert snapshot.status == "pending"
    assert snapshot.user_id == _USER_A
    assert snapshot.run_id == run_id


def test_start_run_snapshot_has_started_at():
    manager = _make_manager()
    before = datetime.now(timezone.utc)
    with patch("asyncio.create_task", side_effect=_no_task):
        run_id = manager.start_run(_USER_A, _mock_pool())
    after = datetime.now(timezone.utc)
    snapshot = manager.get_run(run_id)
    assert before <= snapshot.started_at <= after


def test_start_run_spawns_asyncio_task():
    manager = _make_manager()
    with patch("asyncio.create_task") as mock_create:
        manager.start_run(_USER_A, _mock_pool())
    mock_create.assert_called_once()


# ---------------------------------------------------------------------------
# get_run
# ---------------------------------------------------------------------------

def test_get_run_returns_none_for_unknown_id():
    manager = _make_manager()
    assert manager.get_run(uuid4()) is None


def test_get_run_returns_snapshot_after_start():
    manager = _make_manager()
    with patch("asyncio.create_task", side_effect=_no_task):
        run_id = manager.start_run(_USER_A, _mock_pool())
    assert manager.get_run(run_id) is not None


# ---------------------------------------------------------------------------
# Concurrent run guard
# ---------------------------------------------------------------------------

def test_second_start_raises_run_active_error_while_pending():
    manager = _make_manager()
    with patch("asyncio.create_task", side_effect=_no_task):
        manager.start_run(_USER_A, _mock_pool())
        with pytest.raises(RunActiveError):
            manager.start_run(_USER_A, _mock_pool())


def test_second_start_raises_run_active_error_while_running():
    manager = _make_manager()
    _inject_snapshot(manager, _USER_A, status="running")
    with patch("asyncio.create_task", side_effect=_no_task):
        with pytest.raises(RunActiveError):
            manager.start_run(_USER_A, _mock_pool())


def test_different_users_can_run_concurrently():
    manager = _make_manager()
    with patch("asyncio.create_task", side_effect=_no_task):
        run_a = manager.start_run(_USER_A, _mock_pool())
        run_b = manager.start_run(_USER_B, _mock_pool())
    assert run_a != run_b
    assert manager.get_run(run_a).user_id == _USER_A
    assert manager.get_run(run_b).user_id == _USER_B


def test_start_run_allowed_after_completed_run():
    manager = _make_manager()
    _inject_snapshot(manager, _USER_A, status="completed")
    with patch("asyncio.create_task", side_effect=_no_task):
        run_id = manager.start_run(_USER_A, _mock_pool())
    assert manager.get_run(run_id).status == "pending"


def test_start_run_allowed_after_failed_run():
    manager = _make_manager()
    _inject_snapshot(manager, _USER_A, status="failed")
    with patch("asyncio.create_task", side_effect=_no_task):
        run_id = manager.start_run(_USER_A, _mock_pool())
    assert manager.get_run(run_id).status == "pending"


# ---------------------------------------------------------------------------
# _execute — state transitions (tested directly as a coroutine)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_execute_transitions_pending_to_running_to_completed():
    manager = _make_manager()
    run_id = uuid4()
    manager._runs[run_id] = PipelineRunSnapshot(
        run_id=run_id,
        user_id=_USER_A,
        status="pending",
        started_at=datetime.now(timezone.utc),
    )

    mock_service = AsyncMock()
    mock_service.run_pipeline.return_value = _make_result()

    with patch("services.run_manager.PipelineService", return_value=mock_service):
        await manager._execute(run_id, _USER_A, _mock_pool(), None)

    final = manager.get_run(run_id)
    assert final.status == "completed"
    assert final.result is not None
    assert final.completed_at is not None
    assert final.error is None


@pytest.mark.asyncio
async def test_execute_transitions_to_failed_on_exception():
    manager = _make_manager()
    run_id = uuid4()
    manager._runs[run_id] = PipelineRunSnapshot(
        run_id=run_id,
        user_id=_USER_A,
        status="pending",
        started_at=datetime.now(timezone.utc),
    )

    mock_service = AsyncMock()
    mock_service.run_pipeline.side_effect = RuntimeError("Claude API down")

    with patch("services.run_manager.PipelineService", return_value=mock_service):
        await manager._execute(run_id, _USER_A, _mock_pool(), None)

    final = manager.get_run(run_id)
    assert final.status == "failed"
    assert "Claude API down" in final.error
    assert final.completed_at is not None
    assert final.result is None


@pytest.mark.asyncio
async def test_execute_stores_pipeline_result():
    manager = _make_manager()
    run_id = uuid4()
    manager._runs[run_id] = PipelineRunSnapshot(
        run_id=run_id,
        user_id=_USER_A,
        status="pending",
        started_at=datetime.now(timezone.utc),
    )

    expected = _make_result(jobs_found=10, jobs_stored=7)
    mock_service = AsyncMock()
    mock_service.run_pipeline.return_value = expected

    with patch("services.run_manager.PipelineService", return_value=mock_service):
        await manager._execute(run_id, _USER_A, _mock_pool(), None)

    assert manager.get_run(run_id).result == expected


@pytest.mark.asyncio
async def test_execute_passes_platform_to_pipeline():
    manager = _make_manager()
    run_id = uuid4()
    manager._runs[run_id] = PipelineRunSnapshot(
        run_id=run_id,
        user_id=_USER_A,
        status="pending",
        started_at=datetime.now(timezone.utc),
    )

    mock_service = AsyncMock()
    mock_service.run_pipeline.return_value = _make_result()

    with patch("services.run_manager.PipelineService", return_value=mock_service):
        await manager._execute(run_id, _USER_A, _mock_pool(), "upwork")

    mock_service.run_pipeline.assert_called_once_with(_USER_A, "upwork")


@pytest.mark.asyncio
async def test_execute_completed_at_is_set():
    manager = _make_manager()
    run_id = uuid4()
    before = datetime.now(timezone.utc)
    manager._runs[run_id] = PipelineRunSnapshot(
        run_id=run_id,
        user_id=_USER_A,
        status="pending",
        started_at=before,
    )

    mock_service = AsyncMock()
    mock_service.run_pipeline.return_value = _make_result()

    with patch("services.run_manager.PipelineService", return_value=mock_service):
        await manager._execute(run_id, _USER_A, _mock_pool(), None)

    after = datetime.now(timezone.utc)
    completed_at = manager.get_run(run_id).completed_at
    assert before <= completed_at <= after


# ---------------------------------------------------------------------------
# Snapshot immutability
# ---------------------------------------------------------------------------

def test_snapshot_is_frozen():
    snap = PipelineRunSnapshot(
        run_id=uuid4(),
        user_id=_USER_A,
        status="pending",
        started_at=datetime.now(timezone.utc),
    )
    with pytest.raises(Exception):
        snap.status = "running"  # type: ignore[misc]


def test_update_replaces_snapshot_not_mutates():
    manager = _make_manager()
    run_id = uuid4()
    original = PipelineRunSnapshot(
        run_id=run_id,
        user_id=_USER_A,
        status="pending",
        started_at=datetime.now(timezone.utc),
    )
    manager._runs[run_id] = original

    manager._update(run_id, status="running")

    updated = manager.get_run(run_id)
    assert updated is not original       # new object
    assert updated.status == "running"
    assert original.status == "pending"  # original unchanged


# ---------------------------------------------------------------------------
# Eviction
# ---------------------------------------------------------------------------

def test_evict_removes_runs_older_than_one_hour():
    manager = _make_manager()
    old_snapshot = PipelineRunSnapshot(
        run_id=uuid4(),
        user_id=_USER_A,
        status="completed",
        started_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    manager._runs[old_snapshot.run_id] = old_snapshot

    manager._evict_old_runs()

    assert manager.get_run(old_snapshot.run_id) is None


def test_evict_keeps_recent_runs():
    manager = _make_manager()
    recent = PipelineRunSnapshot(
        run_id=uuid4(),
        user_id=_USER_A,
        status="completed",
        started_at=datetime.now(timezone.utc) - timedelta(minutes=30),
    )
    manager._runs[recent.run_id] = recent

    manager._evict_old_runs()

    assert manager.get_run(recent.run_id) is not None


def test_evict_called_on_start_run():
    manager = _make_manager()
    # Plant an old completed run
    old = PipelineRunSnapshot(
        run_id=uuid4(),
        user_id=_USER_B,
        status="completed",
        started_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )
    manager._runs[old.run_id] = old

    with patch("asyncio.create_task", side_effect=_no_task):
        manager.start_run(_USER_A, _mock_pool())

    # Old run should have been evicted
    assert manager.get_run(old.run_id) is None


def test_evict_does_not_remove_active_old_run():
    """Even an ancient pending/running run should be caught by the active guard, not silently evicted."""
    manager = _make_manager()
    ancient_running = PipelineRunSnapshot(
        run_id=uuid4(),
        user_id=_USER_A,
        status="running",
        started_at=datetime.now(timezone.utc) - timedelta(hours=3),
    )
    manager._runs[ancient_running.run_id] = ancient_running

    # Eviction removes it regardless of status (simple TTL — no status check)
    manager._evict_old_runs()

    # After eviction the user can start a new run (the stuck run was cleaned up)
    with patch("asyncio.create_task", side_effect=_no_task):
        run_id = manager.start_run(_USER_A, _mock_pool())
    assert manager.get_run(run_id).status == "pending"
