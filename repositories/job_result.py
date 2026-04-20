"""JobResultRepository — all database access for the job_results table."""

import logging
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from typing import Final
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)

# Sort clauses use `id DESC` as tiebreaker for deterministic keyset pagination.
_SORT_CLAUSES: Final = MappingProxyType({
    "score_desc": "score DESC NULLS LAST, id DESC",
    "score_asc": "score ASC NULLS LAST, id DESC",
    "date_desc": "created_at DESC, id DESC",
    "date_asc": "created_at ASC, id DESC",
})

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
        """Return True if this job has already been stored for this user.

        This intentional round-trip is used by the pipeline service to skip
        evaluation (Claude API calls) for already-seen jobs — not just the insert.
        Removing it would evaluate duplicates unnecessarily before ON CONFLICT rejects them.
        """
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

    def _build_filter(
        self,
        user_id: UUID,
        status: str | None = None,
        min_score: int | None = None,
        platform: str | None = None,
    ) -> tuple[list[str], list, int]:
        """Build the shared filter for user-scoped queries.

        Returns (conditions, params, next_param_index). Callers may append further
        conditions (keyset cursor, etc.) then join with AND and append LIMIT/OFFSET params.
        """
        # SAFETY: column names below are hardcoded literals, never derived from
        # user-controlled input. If you add a column name here from an external
        # source, use a compile-time allowlist (e.g. MappingProxyType) and verify
        # the value before interpolation.
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
        if platform is not None:
            conditions.append(f"platform = ${idx}")
            params.append(platform)
            idx += 1
        return conditions, params, idx

    @staticmethod
    def _build_keyset_condition(
        sort: str,
        cursor_id: UUID,
        cursor_score: int | None,
        cursor_created_at: datetime | None,
        params: list,
        idx: int,
    ) -> tuple[str, int]:
        """Build a keyset WHERE clause for cursor-based pagination.

        Returns (sql_condition, next_param_index). Appends required values to params.
        """
        if sort == "score_desc":
            # ORDER: score DESC NULLS LAST, id DESC
            if cursor_score is not None:
                params.extend([cursor_score, cursor_score, cursor_id])
                cond = (
                    f"(score < ${idx} OR (score = ${idx + 1} AND id < ${idx + 2}) OR score IS NULL)"
                )
                return cond, idx + 3
            else:
                # Cursor is in the NULL section
                params.append(cursor_id)
                return f"(score IS NULL AND id < ${idx})", idx + 1

        elif sort == "score_asc":
            # ORDER: score ASC NULLS LAST, id DESC
            if cursor_score is not None:
                params.extend([cursor_score, cursor_score, cursor_id])
                cond = (
                    f"(score > ${idx} OR (score = ${idx + 1} AND id < ${idx + 2}) OR score IS NULL)"
                )
                return cond, idx + 3
            else:
                params.append(cursor_id)
                return f"(score IS NULL AND id < ${idx})", idx + 1

        elif sort == "date_desc":
            # ORDER: created_at DESC, id DESC
            params.extend([cursor_created_at, cursor_created_at, cursor_id])
            return (
                f"(created_at < ${idx} OR (created_at = ${idx + 1} AND id < ${idx + 2}))",
                idx + 3,
            )

        elif sort == "date_asc":
            # ORDER: created_at ASC, id DESC
            params.extend([cursor_created_at, cursor_created_at, cursor_id])
            return (
                f"(created_at > ${idx} OR (created_at = ${idx + 1} AND id < ${idx + 2}))",
                idx + 3,
            )

        else:
            raise ValueError(f"Unknown sort key: {sort!r}")

    async def find_by_user(
        self,
        user_id: UUID,
        status: str | None = None,
        min_score: int | None = None,
        platform: str | None = None,
        sort: str = "score_desc",
        limit: int = 50,
        cursor_id: UUID | None = None,
        cursor_score: int | None = None,
        cursor_created_at: datetime | None = None,
    ) -> list[JobResultRow]:
        """Return job results using keyset (cursor) pagination.

        Pass cursor_id (plus cursor_score or cursor_created_at depending on sort) to
        retrieve the next page after the last seen row. Omit cursor_id for the first page.
        """
        if sort not in _SORT_CLAUSES:
            raise ValueError(f"Unknown sort key: {sort!r}")

        conditions, params, idx = self._build_filter(user_id, status, min_score, platform)

        if cursor_id is not None:
            keyset_cond, idx = self._build_keyset_condition(
                sort, cursor_id, cursor_score, cursor_created_at, params, idx
            )
            conditions.append(keyset_cond)

        where = " AND ".join(conditions)
        # SAFETY: `order` is drawn from _SORT_CLAUSES (a compile-time MappingProxyType
        # allowlist) and validated above. `where` is built entirely from hardcoded column
        # name literals and $N placeholders — no user-controlled strings are interpolated.
        order = _SORT_CLAUSES[sort]
        params.append(limit)

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"""
                SELECT id, user_id, platform, job_id, title, url, score, evaluation, status, created_at
                FROM job_results
                WHERE {where}
                ORDER BY {order}
                LIMIT ${idx}
                """,
                *params,
            )
        return [_row_to_job_result(r) for r in rows]

    async def update_status(self, result_id: UUID, user_id: UUID, status: str) -> JobResultRow | None:
        """Update the status of a job result scoped to user_id.

        Returns the updated row, or None if no row matched (wrong id or not owned by user).
        Raises ValueError for invalid statuses.
        """
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {VALID_STATUSES}")
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE job_results SET status = $1
                WHERE id = $2 AND user_id = $3
                RETURNING id, user_id, platform, job_id, title, url, score, evaluation, status, created_at
                """,
                status,
                result_id,
                user_id,
            )
        return _row_to_job_result(row) if row is not None else None

    async def bulk_update_status(
        self,
        user_id: UUID,
        new_status: str,
        current_status: str | None = None,
        platform: str | None = None,
        min_score: int | None = None,
        max_score: int | None = None,
        older_than: datetime | None = None,
    ) -> int:
        """Set all matching results to new_status. Returns the number of rows updated."""
        if new_status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of: {VALID_STATUSES}")

        # $1 = new_status, $2 = user_id, remaining params start at $3
        # SAFETY: column names below are hardcoded literals, never derived from
        # user-controlled input. If you add a column name here from an external
        # source, use a compile-time allowlist (e.g. MappingProxyType) and verify
        # the value before interpolation.
        params: list = [new_status, user_id]
        conditions = ["user_id = $2"]
        idx = 3

        if current_status is not None:
            conditions.append(f"status = ${idx}")
            params.append(current_status)
            idx += 1

        if platform is not None:
            conditions.append(f"platform = ${idx}")
            params.append(platform)
            idx += 1

        if min_score is not None:
            conditions.append(f"score >= ${idx}")
            params.append(min_score)
            idx += 1

        if max_score is not None:
            conditions.append(f"score <= ${idx}")
            params.append(max_score)
            idx += 1

        if older_than is not None:
            conditions.append(f"created_at < ${idx}")
            params.append(older_than)
            idx += 1

        where = " AND ".join(conditions)
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"UPDATE job_results SET status = $1 WHERE {where}",
                *params,
            )
        updated_count = int(result.split()[-1])
        logger.debug("Bulk updated %d results for user_id=%s to status=%s", updated_count, user_id, new_status)
        return updated_count

    async def bulk_delete(
        self,
        user_id: UUID,
        current_status: str | None = None,
        platform: str | None = None,
        min_score: int | None = None,
        max_score: int | None = None,
        older_than: datetime | None = None,
    ) -> int:
        """Hard-delete all matching results for user_id. Returns the number of rows deleted."""
        # SAFETY: column names below are hardcoded literals, never derived from
        # user-controlled input. If you add a column name here from an external
        # source, use a compile-time allowlist (e.g. MappingProxyType) and verify
        # the value before interpolation.
        params: list = [user_id]
        conditions = ["user_id = $1"]
        idx = 2

        if current_status is not None:
            conditions.append(f"status = ${idx}")
            params.append(current_status)
            idx += 1

        if platform is not None:
            conditions.append(f"platform = ${idx}")
            params.append(platform)
            idx += 1

        if min_score is not None:
            conditions.append(f"score >= ${idx}")
            params.append(min_score)
            idx += 1

        if max_score is not None:
            conditions.append(f"score <= ${idx}")
            params.append(max_score)
            idx += 1

        if older_than is not None:
            conditions.append(f"created_at < ${idx}")
            params.append(older_than)
            idx += 1

        where = " AND ".join(conditions)
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                f"DELETE FROM job_results WHERE {where}",
                *params,
            )
        deleted_count = int(result.split()[-1])
        logger.debug("Bulk deleted %d results for user_id=%s", deleted_count, user_id)
        return deleted_count

    async def update_status_many(self, user_id: UUID, ids: list[UUID], new_status: str) -> int:
        """Set status for a specific list of IDs scoped to user_id. Returns rows updated."""
        if new_status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{new_status}'. Must be one of: {VALID_STATUSES}")
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE job_results SET status = $1
                WHERE user_id = $2 AND id = ANY($3::uuid[])
                """,
                new_status,
                user_id,
                ids,
            )
        updated_count = int(result.split()[-1])
        logger.debug("Bulk status updated %d results for user_id=%s to status=%s", updated_count, user_id, new_status)
        return updated_count

    async def delete_many(self, user_id: UUID, ids: list[UUID]) -> int:
        """Hard-delete job results by ID list, scoped to user_id. Returns the count deleted."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM job_results
                WHERE user_id = $1 AND id = ANY($2::uuid[])
                """,
                user_id,
                ids,
            )
        deleted_count = int(result.split()[-1])
        logger.debug("Deleted %d job results by id list for user_id=%s", deleted_count, user_id)
        return deleted_count

    async def find_by_id_and_user(self, result_id: UUID, user_id: UUID) -> JobResultRow | None:
        """Return a single job result scoped to user_id, or None if not found."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, platform, job_id, title, url, score, evaluation, status, created_at
                FROM job_results
                WHERE id = $1 AND user_id = $2
                """,
                result_id,
                user_id,
            )
        return _row_to_job_result(row) if row else None

    async def delete_by_id(self, result_id: UUID, user_id: UUID) -> bool:
        """Hard-delete a job result scoped to user_id.

        Returns True if a row was deleted, False if not found or not owned by user.
        """
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM job_results WHERE id = $1 AND user_id = $2",
                result_id,
                user_id,
            )
        deleted = int(result.split()[-1])
        logger.debug("Deleted %d job result(s) id=%s user_id=%s", deleted, result_id, user_id)
        return deleted > 0

    async def count_by_user(
        self,
        user_id: UUID,
        status: str | None = None,
        min_score: int | None = None,
        platform: str | None = None,
    ) -> int:
        """Return the total count of job results for a user, optionally filtered by status, min score, and platform."""
        conditions, params, _ = self._build_filter(user_id, status, min_score, platform)
        where = " AND ".join(conditions)
        # SAFETY: `where` is built by _build_filter from hardcoded column name literals
        # and $N placeholders only — no user-controlled strings are interpolated.
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"SELECT COUNT(*) AS cnt FROM job_results WHERE {where}",
                *params,
            )
        return row["cnt"]
