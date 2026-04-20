"""RunManager — in-memory run state tracking and background task dispatch.

Keeps a ``dict[UUID, PipelineRunSnapshot]`` as the source of truth for all
pipeline runs. Snapshots are immutable (frozen dataclass); state transitions
create a new snapshot via ``dataclasses.replace`` and replace the old one.

Lifecycle:
    pending  →  running  →  completed
                         →  failed

Concurrency model: asyncio (single-threaded event loop). No locks needed —
state updates never cross an ``await`` boundary within a single state
transition.
"""

import asyncio
import logging
import os
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from uuid import UUID, uuid4

import asyncpg

from repositories.company_blacklist import CompanyBlacklistRepository
from repositories.job_list import JobListRepository
from repositories.job_result import JobResultRepository
from repositories.pipeline_run import PipelineRunRepository
from repositories.profile import ProfileRepository
from repositories.search_config import SearchConfigRepository
from services.pipeline import PipelineRunResult, PipelineService

logger = logging.getLogger(__name__)

_EVICT_AFTER_SECONDS = 3600  # 1 hour


class RunActiveError(Exception):
    """Raised when a user tries to start a run while one is already active."""


@dataclass(frozen=True)
class PipelineRunSnapshot:
    """Immutable point-in-time state of a single pipeline run."""

    run_id: UUID
    user_id: UUID
    status: str  # "pending" | "running" | "completed" | "failed"
    started_at: datetime
    completed_at: datetime | None = None
    result: PipelineRunResult | None = None
    error: str | None = None


class RunManager:
    """Manages background pipeline runs for all users.

    One instance is created at application startup and stored on
    ``app.state.run_manager``. Each authenticated ``POST /run`` request
    calls ``start_run``, which spawns an ``asyncio.Task`` and returns the
    ``run_id`` immediately.

    Args:
        anthropic_api_key: Passed through to each ``PipelineService``.
        pool: asyncpg connection pool for persisting run state to the
              ``pipeline_runs`` table.
    """

    def __init__(self, anthropic_api_key: str, pool: asyncpg.Pool) -> None:
        self._api_key = anthropic_api_key
        self._pool = pool
        self._runs: dict[UUID, PipelineRunSnapshot] = {}
        self._active_tasks: set[asyncio.Task] = set()

    def start_run(
        self,
        user_id: UUID,
        pool: asyncpg.Pool,
        platforms: list[str] | None = None,
    ) -> UUID:
        """Enqueue a pipeline run for the user and return the run_id immediately.

        Args:
            user_id: The authenticated user.
            pool: asyncpg pool — passed to the PipelineService constructed
                  inside the background task.
            platforms: Optional list of platform slugs to restrict the run.
                       None means run all configured platforms.

        Returns:
            A fresh ``run_id`` UUID that the caller can use to poll status.

        Raises:
            RunActiveError: If the user already has a pending or running run.
        """
        self._evict_old_runs()

        if self._has_active_run(user_id):
            raise RunActiveError(
                "A pipeline run is already in progress. "
                "Please wait for it to finish before starting another."
            )

        run_id = uuid4()
        now = datetime.now(timezone.utc)
        snapshot = PipelineRunSnapshot(
            run_id=run_id,
            user_id=user_id,
            status="pending",
            started_at=now,
        )
        self._runs[run_id] = snapshot
        persist_task = asyncio.create_task(self._persist_insert(run_id, user_id, now))
        self._active_tasks.add(persist_task)
        persist_task.add_done_callback(self._active_tasks.discard)

        execute_task = asyncio.create_task(self._execute(run_id, user_id, pool, platforms))
        self._active_tasks.add(execute_task)
        execute_task.add_done_callback(self._active_tasks.discard)
        return run_id

    def get_run(self, run_id: UUID) -> PipelineRunSnapshot | None:
        """Return the current snapshot for ``run_id``, or None if not found."""
        return self._runs.get(run_id)

    async def _execute(
        self,
        run_id: UUID,
        user_id: UUID,
        pool: asyncpg.Pool,
        platforms: list[str] | None,
    ) -> None:
        """Background coroutine — runs the pipeline and updates snapshot state."""
        self._update(run_id, status="running")
        await self._persist_status(run_id, user_id, status="running")

        service = PipelineService(
            profile_repo=ProfileRepository(pool),
            search_config_repo=SearchConfigRepository(pool),
            job_result_repo=JobResultRepository(pool),
            job_list_repo=JobListRepository(pool),
            company_blacklist_repo=CompanyBlacklistRepository(pool),
            anthropic_api_key=self._api_key,
        )

        try:
            result = await service.run_pipeline(user_id, platforms)
            completed_at = datetime.now(timezone.utc)
            self._update(
                run_id,
                status="completed",
                result=result,
                completed_at=completed_at,
            )
            result_dict = asdict(result)
            await self._persist_status(
                run_id,
                user_id,
                status="completed",
                result=result_dict,
                completed_at=completed_at,
            )
            logger.info(
                "Run %s completed: found=%d evaluated=%d stored=%d errors=%d",
                run_id,
                result.jobs_found,
                result.jobs_evaluated,
                result.jobs_stored,
                len(result.errors),
            )
        except Exception as exc:
            logger.error("Run %s failed (user_id=%s): %s", run_id, user_id, exc, exc_info=True)
            completed_at = datetime.now(timezone.utc)
            _generic_error = "An internal error occurred. Please try again."
            self._update(
                run_id,
                status="failed",
                error=_generic_error,
                completed_at=completed_at,
            )
            await self._persist_status(
                run_id,
                user_id,
                status="failed",
                error=_generic_error,
                completed_at=completed_at,
            )

    def _update(self, run_id: UUID, **fields) -> None:
        """Replace the snapshot with a new one reflecting updated fields."""
        self._runs[run_id] = replace(self._runs[run_id], **fields)

    def _has_active_run(self, user_id: UUID) -> bool:
        """Return True if the user has any run in pending or running state."""
        return any(
            s.user_id == user_id and s.status in ("pending", "running")
            for s in self._runs.values()
        )

    def _evict_old_runs(self) -> None:
        """Remove completed/failed runs started more than ``_EVICT_AFTER_SECONDS`` ago."""
        now = datetime.now(timezone.utc)
        to_evict = [
            run_id
            for run_id, snapshot in self._runs.items()
            if (now - snapshot.started_at).total_seconds() > _EVICT_AFTER_SECONDS
        ]
        for run_id in to_evict:
            del self._runs[run_id]
            logger.debug("Evicted run %s", run_id)

    # ── DB persistence helpers ─────────────────────────────────────────────

    async def _persist_insert(
        self,
        run_id: UUID,
        user_id: UUID,
        started_at: datetime,
    ) -> None:
        """Insert a new row into pipeline_runs. Errors are logged, not raised."""
        try:
            repo = PipelineRunRepository(self._pool)
            await repo.insert(run_id, user_id, started_at)
        except Exception as exc:
            logger.error("Failed to persist run %s insert: %s", run_id, exc)

    async def _persist_status(
        self,
        run_id: UUID,
        user_id: UUID,
        status: str,
        result: dict | None = None,
        error: str | None = None,
        completed_at: datetime | None = None,
    ) -> None:
        """Update pipeline_runs row scoped to user_id. Errors are logged, not raised."""
        try:
            repo = PipelineRunRepository(self._pool)
            await repo.update_status(
                run_id,
                user_id,
                status=status,
                result=result,
                error=error,
                completed_at=completed_at,
            )
        except Exception as exc:
            logger.error("Failed to persist run %s status=%s: %s", run_id, status, exc)
