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
    created_at: datetime


def _row_to_customization(row: asyncpg.Record) -> CVCustomizationRow:
    return CVCustomizationRow(
        id=row["id"],
        user_id=row["user_id"],
        job_result_id=row["job_result_id"],
        customized_text=row["customized_text"],
        created_at=row["created_at"],
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
                SELECT id, user_id, job_result_id, customized_text, created_at
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
    ) -> CVCustomizationRow:
        """Insert or replace a customization for a specific job. Returns the row."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO cv_customizations (user_id, job_result_id, customized_text)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, job_result_id) DO UPDATE SET
                    customized_text = EXCLUDED.customized_text,
                    created_at      = now()
                RETURNING id, user_id, job_result_id, customized_text, created_at
                """,
                user_id,
                job_result_id,
                customized_text,
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
