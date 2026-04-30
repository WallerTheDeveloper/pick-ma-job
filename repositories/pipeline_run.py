"""PipelineRunRepository — all database access for the pipeline_runs table."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PipelineRunRow:
    id: UUID
    user_id: UUID
    status: str
    result: dict | None
    error: str | None
    started_at: datetime
    completed_at: datetime | None


def _row_to_pipeline_run(row: asyncpg.Record) -> PipelineRunRow:
    return PipelineRunRow(
        id=row["id"],
        user_id=row["user_id"],
        status=row["status"],
        result=row["result"],
        error=row["error"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
    )


class PipelineRunRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def insert(
        self,
        run_id: UUID,
        user_id: UUID,
        started_at: datetime,
    ) -> PipelineRunRow:
        """Insert a new pipeline run with status 'pending'."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO pipeline_runs (id, user_id, status, started_at)
                VALUES ($1, $2, 'pending', $3)
                RETURNING id, user_id, status, result, error, started_at, completed_at
                """,
                run_id,
                user_id,
                started_at,
            )
        return _row_to_pipeline_run(row)

    async def update_status(
        self,
        run_id: UUID,
        user_id: UUID,
        status: str,
        result: dict | None = None,
        error: str | None = None,
        completed_at: datetime | None = None,
    ) -> bool:
        """Update the status of a run, scoped to user_id.

        Returns True if a row was updated, False if run_id not found or not owned by user.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE pipeline_runs
                SET status = $1, result = $2::jsonb, error = $3, completed_at = $4
                WHERE id = $5 AND user_id = $6
                RETURNING id
                """,
                status,
                result,
                error,
                completed_at,
                run_id,
                user_id,
            )
        return row is not None

    async def find_by_user(
        self,
        user_id: UUID,
        limit: int = 10,
    ) -> list[PipelineRunRow]:
        """Return the most recent pipeline runs for a user."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, status, result, error, started_at, completed_at
                FROM pipeline_runs
                WHERE user_id = $1
                ORDER BY started_at DESC
                LIMIT $2
                """,
                user_id,
                limit,
            )
        return [_row_to_pipeline_run(r) for r in rows]

    async def find_latest_by_user(self, user_id: UUID) -> PipelineRunRow | None:
        """Return the most recent pipeline run for a user, or None."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, status, result, error, started_at, completed_at
                FROM pipeline_runs
                WHERE user_id = $1
                ORDER BY started_at DESC
                LIMIT 1
                """,
                user_id,
            )
        return _row_to_pipeline_run(row) if row else None

    async def find_by_id(self, run_id: UUID) -> PipelineRunRow | None:
        """Return a single run by ID, or None if not found."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, status, result, error, started_at, completed_at
                FROM pipeline_runs
                WHERE id = $1
                """,
                run_id,
            )
        return _row_to_pipeline_run(row) if row else None

    async def has_active_run(self, user_id: UUID) -> bool:
        """Return True if the user has any run in pending or running state."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 1 FROM pipeline_runs
                WHERE user_id = $1 AND status IN ('pending', 'running')
                LIMIT 1
                """,
                user_id,
            )
        return row is not None

    async def mark_stale_as_failed(self, stale_after_minutes: int) -> int:
        """Mark all pending/running rows older than stale_after_minutes as failed.

        Returns the number of rows updated.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=stale_after_minutes)
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE pipeline_runs
                SET status = 'failed',
                    error = 'Run interrupted by server restart.',
                    completed_at = now()
                WHERE status IN ('pending', 'running')
                  AND started_at < $1
                """,
                cutoff,
            )
        updated = int(result.split()[-1])
        return updated
