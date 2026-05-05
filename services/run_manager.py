"""RunManager — DB-backed run state tracking and background task dispatch.

Uses the ``pipeline_runs`` table as the authoritative source of truth.
No in-memory state is kept for run status — all queries go to the DB.

Lifecycle:
    pending  →  running  →  completed
                          →  failed

On startup, ``reconcile_stale_runs`` marks any rows that were left in
``pending`` or ``running`` (from a previous process) as ``failed``.
"""

import asyncio
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from uuid import UUID, uuid4

import asyncpg

from core.context import run_id_var, user_id_var
from core.exceptions import ConflictError
from core.llm_client import LLMClient
from core.settings import Settings
from repositories.company_blacklist import CompanyBlacklistRepository
from repositories.job_list import JobListRepository
from repositories.job_result import JobResultRepository
from repositories.pipeline_run import PipelineRunRepository, PipelineRunRow
from repositories.profile import ProfileRepository
from repositories.search_config import SearchConfigRepository
from services.auto_list_service import AutoListService
from services.pipeline import PipelineService

logger = logging.getLogger(__name__)

_STALE_RUN_MINUTES = 30

# Backward-compatible alias — existing tests catch RunActiveError.
RunActiveError = ConflictError


class RunManager:
    """Manages background pipeline runs for all users.

    One instance is created at application startup and stored on
    ``app.state.run_manager``. Each authenticated ``POST /run`` request
    calls ``start_run``, which inserts a DB row and spawns an
    ``asyncio.Task``, then returns the ``run_id`` immediately.

    Args:
        llm_client: Shared ``LLMClient`` passed through to each ``PipelineService``.
        pool: asyncpg connection pool shared with the rest of the app.
        settings: Validated application settings.
    """

    def __init__(self, llm_client: LLMClient, pool: asyncpg.Pool, settings: Settings) -> None:
        self._llm_client = llm_client
        self._pool = pool
        self._settings = settings

    async def reconcile_stale_runs(self, stale_after_minutes: int = _STALE_RUN_MINUTES) -> None:
        """Mark pending/running rows older than stale_after_minutes as failed.

        Call once at startup after the pool is ready to clean up runs that
        were interrupted by a previous server restart.
        """
        repo = PipelineRunRepository(self._pool)
        count = await repo.mark_stale_as_failed(stale_after_minutes)
        if count:
            logger.warning("Reconciled %d stale pipeline run(s) → failed", count)
        else:
            logger.info("No stale pipeline runs found on startup")

    async def start_run(
        self,
        user_id: UUID,
        platforms: list[str] | None = None,
    ) -> UUID:
        """Insert a PENDING row and enqueue the pipeline task. Returns run_id.

        Args:
            user_id: The authenticated user.
            platforms: Optional list of platform slugs to restrict the run.
                       None means run all configured platforms.

        Returns:
            A fresh ``run_id`` UUID that the caller can use to poll status.

        Raises:
            RunActiveError: If the user already has a pending or running run.
        """
        repo = PipelineRunRepository(self._pool)

        if await repo.has_active_run(user_id):
            raise RunActiveError(
                "A pipeline run is already in progress. "
                "Please wait for it to finish before starting another."
            )

        run_id = uuid4()
        now = datetime.now(timezone.utc)
        await repo.insert(run_id, user_id, now)

        asyncio.create_task(self._execute(run_id, user_id, platforms))
        return run_id

    async def get_run(self, run_id: UUID) -> PipelineRunRow | None:
        """Return the current DB row for ``run_id``, or None if not found."""
        repo = PipelineRunRepository(self._pool)
        return await repo.find_by_id(run_id)

    # ── Background execution ───────────────────────────────────────────────

    async def _execute(
        self,
        run_id: UUID,
        user_id: UUID,
        platforms: list[str] | None,
    ) -> None:
        """Background coroutine — runs the pipeline and persists state to DB."""
        # Set context vars so all log lines in this run are tagged
        run_id_var.set(str(run_id))
        user_id_var.set(str(user_id))

        await self._persist_status(run_id, user_id, status="running")

        service = PipelineService(
            profile_repo=ProfileRepository(self._pool),
            search_config_repo=SearchConfigRepository(self._pool),
            job_result_repo=JobResultRepository(self._pool),
            job_list_repo=JobListRepository(self._pool),
            company_blacklist_repo=CompanyBlacklistRepository(self._pool),
            llm_client=self._llm_client,
            settings=self._settings,
            auto_list_service=AutoListService(job_list_repo=JobListRepository(self._pool)),
        )

        try:
            result = await service.run_pipeline(user_id, platforms, run_id=run_id)
            completed_at = datetime.now(timezone.utc)
            await self._persist_status(
                run_id,
                user_id,
                status="completed",
                result=asdict(result),
                completed_at=completed_at,
            )
            logger.info(
                "Run %s completed: found=%d language=%d stored=%d errors=%d",
                run_id,
                result.jobs_found,
                result.jobs_skipped_language,
                result.jobs_stored,
                len(result.errors),
            )
        except Exception as exc:
            logger.error("Run %s failed (user_id=%s): %s", run_id, user_id, exc, exc_info=True)
            await self._persist_status(
                run_id,
                user_id,
                status="failed",
                error="An internal error occurred. Please try again.",
                completed_at=datetime.now(timezone.utc),
            )

    # ── DB persistence helpers ─────────────────────────────────────────────

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
