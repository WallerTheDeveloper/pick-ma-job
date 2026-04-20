"""CVRepository — all database access for the cvs table."""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CVRow:
    id: UUID
    user_id: UUID
    filename: str
    raw_text: str
    structured: dict
    created_at: datetime
    updated_at: datetime


def _row_to_cv(row: asyncpg.Record) -> CVRow:
    return CVRow(
        id=row["id"],
        user_id=row["user_id"],
        filename=row["filename"],
        raw_text=row["raw_text"],
        structured=dict(row["structured"] or {}),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class CVRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def find_by_user(self, user_id: UUID) -> CVRow | None:
        """Return the CV for the given user, or None if not uploaded yet."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, filename, raw_text, structured, created_at, updated_at
                FROM cvs WHERE user_id = $1
                """,
                user_id,
            )
        return _row_to_cv(row) if row else None

    async def upsert(
        self,
        user_id: UUID,
        filename: str,
        raw_text: str,
        structured: dict,
    ) -> CVRow:
        """Insert or replace the CV for the given user. Returns the resulting row."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO cvs (user_id, filename, raw_text, structured)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id) DO UPDATE SET
                    filename   = EXCLUDED.filename,
                    raw_text   = EXCLUDED.raw_text,
                    structured = EXCLUDED.structured,
                    updated_at = now()
                RETURNING id, user_id, filename, raw_text, structured, created_at, updated_at
                """,
                user_id,
                filename,
                raw_text,
                structured,
            )
        logger.debug("Upserted CV user_id=%s filename=%s", user_id, filename)
        return _row_to_cv(row)

    async def delete_by_user(self, user_id: UUID) -> None:
        """Delete the user's CV and all associated customizations (cascade)."""
        async with self._pool.acquire() as conn:
            await conn.execute("DELETE FROM cvs WHERE user_id = $1", user_id)
        logger.debug("Deleted CV for user_id=%s", user_id)
