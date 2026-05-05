"""CVCustomizationRepository — per-job cached CV customizations."""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CVCustomizationRow:
    id: UUID
    user_id: UUID
    job_result_id: UUID
    customized_text: str
    customized_diff: dict | None
    created_at: datetime
    updated_at: datetime


def _row_to_customization(row: asyncpg.Record) -> CVCustomizationRow:
    return CVCustomizationRow(
        id=row["id"],
        user_id=row["user_id"],
        job_result_id=row["job_result_id"],
        customized_text=row["customized_text"],
        customized_diff=row["customized_diff"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class CVCustomizationRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def find_by_user_and_job(
        self,
        user_id: UUID,
        job_result_id: UUID,
    ) -> CVCustomizationRow | None:
        """Return a cached customization, or None if not generated yet."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, job_result_id, customized_text, customized_diff, created_at, updated_at
                FROM cv_customizations
                WHERE user_id = $1 AND job_result_id = $2
                """,
                user_id,
                job_result_id,
            )
        return _row_to_customization(row) if row else None

    async def upsert(
        self,
        user_id: UUID,
        job_result_id: UUID,
        customized_text: str,
        customized_diff: dict | None = None,
    ) -> CVCustomizationRow:
        """Insert or replace a customization for a specific job. Returns the row."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO cv_customizations (user_id, job_result_id, customized_text, customized_diff)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, job_result_id) DO UPDATE SET
                    customized_text = EXCLUDED.customized_text,
                    customized_diff = EXCLUDED.customized_diff,
                    updated_at      = now()
                RETURNING id, user_id, job_result_id, customized_text, customized_diff, created_at, updated_at
                """,
                user_id,
                job_result_id,
                customized_text,
                customized_diff,
            )
        logger.debug(
            "Upserted customization user_id=%s job_result_id=%s", user_id, job_result_id
        )
        return _row_to_customization(row)

    async def delete_by_user_and_job(
        self,
        user_id: UUID,
        job_result_id: UUID,
    ) -> None:
        """Delete a specific customization cache entry."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "DELETE FROM cv_customizations WHERE user_id = $1 AND job_result_id = $2",
                user_id,
                job_result_id,
            )
