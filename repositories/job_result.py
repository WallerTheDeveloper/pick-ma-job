"""JobResultRepository — all database access for the job_results table."""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)

VALID_STATUSES = frozenset({"new", "applied", "dismissed"})


@dataclass(frozen=True)
class JobResultRow:
    id: UUID
    user_id: UUID
    platform: str
    job_id: str
    title: str
    url: str
    score: int | None
    evaluation: dict | None
    status: str
    created_at: datetime


def _row_to_job_result(row: asyncpg.Record) -> JobResultRow:
    return JobResultRow(
        id=row["id"],
        user_id=row["user_id"],
        platform=row["platform"],
        job_id=row["job_id"],
        title=row["title"],
        url=row["url"],
        score=row["score"],
        evaluation=row["evaluation"],
        status=row["status"],
        created_at=row["created_at"],
    )


class JobResultRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def insert(
        self,
        user_id: UUID,
        platform: str,
        job_id: str,
        title: str,
        url: str,
        score: int | None,
        evaluation: dict | None,
    ) -> JobResultRow | None:
        """Insert a job result. Returns None if the job already exists (dedup via UNIQUE constraint)."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO job_results (user_id, platform, job_id, title, url, score, evaluation)
                VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
                ON CONFLICT (user_id, platform, job_id) DO NOTHING
                RETURNING id, user_id, platform, job_id, title, url, score, evaluation, status, created_at
                """,
                user_id,
                platform,
                job_id,
                title,
                url,
                score,
                evaluation,
            )
        if row is None:
            logger.debug("Skipped duplicate job user_id=%s platform=%s job_id=%s", user_id, platform, job_id)
            return None
        logger.debug("Inserted job result user_id=%s platform=%s job_id=%s", user_id, platform, job_id)
        return _row_to_job_result(row)

    async def exists(self, user_id: UUID, platform: str, job_id: str) -> bool:
        """Return True if this job has already been stored for this user."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 1 FROM job_results
                WHERE user_id = $1 AND platform = $2 AND job_id = $3
                """,
                user_id,
                platform,
                job_id,
            )
        return row is not None

    async def find_by_user(
        self,
        user_id: UUID,
        status: str | None = None,
        min_score: int | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[JobResultRow]:
        """Return paginated job results for a user, optionally filtered by status and min score."""
        conditions = ["user_id = $1"]
        params: list = [user_id]
        idx = 2

        if status is not None:
            conditions.append(f"status = ${idx}")
            params.append(status)
            idx += 1

        if min_score is not None:
            conditions.append(f"score >= ${idx}")
            params.append(min_score)
            idx += 1

        where = " AND ".join(conditions)
        params.extend([limit, offset])

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT id, user_id, platform, job_id, title, url, score, evaluation, status, created_at
                FROM job_results
                WHERE {where}
                ORDER BY score DESC NULLS LAST, created_at DESC
                LIMIT ${idx} OFFSET ${idx + 1}
                """,
                *params,
            )
        return [_row_to_job_result(r) for r in rows]

    async def update_status(self, result_id: UUID, status: str) -> None:
        """Update the status of a job result. Raises ValueError for invalid statuses."""
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {VALID_STATUSES}")
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE job_results SET status = $1 WHERE id = $2",
                status,
                result_id,
            )

    async def count_by_user(self, user_id: UUID, status: str | None = None) -> int:
        """Return the total count of job results for a user, optionally filtered by status."""
        if status is not None:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT COUNT(*) AS cnt FROM job_results WHERE user_id = $1 AND status = $2",
                    user_id,
                    status,
                )
        else:
            async with self._pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT COUNT(*) AS cnt FROM job_results WHERE user_id = $1",
                    user_id,
                )
        return row["cnt"]
