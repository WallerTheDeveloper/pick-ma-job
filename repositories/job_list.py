"""JobListRepository — database access for job_lists and job_list_items tables."""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

from repositories.job_result import JobResultRow, _row_to_job_result

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class JobListRow:
    id: UUID
    user_id: UUID
    name: str
    created_at: datetime


def _row_to_job_list(row: asyncpg.Record) -> JobListRow:
    return JobListRow(
        id=row["id"],
        user_id=row["user_id"],
        name=row["name"],
        created_at=row["created_at"],
    )


class JobListRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def find_by_user(self, user_id: UUID) -> list[JobListRow]:
        """Return all job lists for a user, ordered by creation date."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, name, created_at
                FROM job_lists
                WHERE user_id = $1
                ORDER BY created_at ASC
                """,
                user_id,
            )
        return [_row_to_job_list(r) for r in rows]

    async def find_by_id(self, list_id: UUID, user_id: UUID) -> JobListRow | None:
        """Return a specific list scoped to user_id, or None if not found."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, name, created_at
                FROM job_lists
                WHERE id = $1 AND user_id = $2
                """,
                list_id,
                user_id,
            )
        return _row_to_job_list(row) if row is not None else None

    async def create(self, user_id: UUID, name: str) -> JobListRow:
        """Insert a new job list. Returns the inserted row."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO job_lists (user_id, name)
                VALUES ($1, $2)
                RETURNING id, user_id, name, created_at
                """,
                user_id,
                name,
            )
        logger.debug("Created job list user_id=%s name=%r", user_id, name)
        return _row_to_job_list(row)

    async def rename(self, list_id: UUID, user_id: UUID, name: str) -> JobListRow | None:
        """Rename a job list. Returns the updated row, or None if not found/not owned."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE job_lists SET name = $1
                WHERE id = $2 AND user_id = $3
                RETURNING id, user_id, name, created_at
                """,
                name,
                list_id,
                user_id,
            )
        return _row_to_job_list(row) if row is not None else None

    async def delete(self, list_id: UUID, user_id: UUID) -> bool:
        """Delete a job list scoped to user_id. Returns True if a row was deleted."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "DELETE FROM job_lists WHERE id = $1 AND user_id = $2 RETURNING id",
                list_id,
                user_id,
            )
        return row is not None

    async def add_job(self, list_id: UUID, job_result_id: UUID, user_id: UUID) -> bool:
        """Add a job result to a list, verifying both list and job are owned by user_id.

        Returns True if the row was inserted, False if the ownership check failed or
        the job was already present in the list.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                WITH owned_list AS (
                    SELECT id FROM job_lists WHERE id = $1 AND user_id = $3
                ),
                owned_job AS (
                    SELECT id FROM job_results WHERE id = $2 AND user_id = $3
                )
                INSERT INTO job_list_items (list_id, job_result_id)
                SELECT $1, $2 FROM owned_list, owned_job
                ON CONFLICT (list_id, job_result_id) DO NOTHING
                RETURNING list_id
                """,
                list_id,
                job_result_id,
                user_id,
            )
        return row is not None

    async def remove_job(self, list_id: UUID, job_result_id: UUID, user_id: UUID) -> bool:
        """Remove a job result from a list, verifying both list and job ownership.

        Returns True if a row was deleted, False if not found, list not owned by user_id,
        or job result not owned by user_id.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                DELETE FROM job_list_items
                WHERE list_id = $1 AND job_result_id = $2
                  AND list_id IN (SELECT id FROM job_lists WHERE id = $1 AND user_id = $3)
                  AND EXISTS (SELECT 1 FROM job_results WHERE id = $2 AND user_id = $3)
                RETURNING list_id
                """,
                list_id,
                job_result_id,
                user_id,
            )
        return row is not None

    async def find_jobs_in_list(self, list_id: UUID, user_id: UUID) -> list[JobResultRow]:
        """Return all job results in a list, scoped to user_id for security."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT jr.id, jr.user_id, jr.platform, jr.job_id, jr.title, jr.url,
                       jr.score, jr.evaluation, jr.status, jr.created_at
                FROM job_results jr
                JOIN job_list_items jli ON jli.job_result_id = jr.id
                JOIN job_lists jl ON jl.id = jli.list_id
                WHERE jli.list_id = $1 AND jl.user_id = $2
                ORDER BY jli.added_at DESC
                """,
                list_id,
                user_id,
            )
        return [_row_to_job_result(r) for r in rows]

    async def add_items(self, list_id: UUID, job_result_ids: list[UUID]) -> None:
        """Bulk-insert job result IDs into a list. Silently skips duplicates."""
        if not job_result_ids:
            return
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO job_list_items (list_id, job_result_id)
                SELECT $1, unnest($2::uuid[])
                ON CONFLICT DO NOTHING
                """,
                list_id,
                job_result_ids,
            )
        logger.debug("Added %d items to list %s", len(job_result_ids), list_id)

    async def get_list_ids_for_job(self, job_result_id: UUID, user_id: UUID) -> list[UUID]:
        """Return all list IDs that contain this job result, scoped to user_id."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT jli.list_id
                FROM job_list_items jli
                JOIN job_lists jl ON jl.id = jli.list_id
                WHERE jli.job_result_id = $1 AND jl.user_id = $2
                """,
                job_result_id,
                user_id,
            )
        return [r["list_id"] for r in rows]
