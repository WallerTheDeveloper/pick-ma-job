"""ProfileRepository — all database access for the profiles table."""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProfileRow:
    id: UUID
    user_id: UUID
    skills: list
    experience: str | None
    rate: str | None
    rubric: dict
    updated_at: datetime


def _row_to_profile(row: asyncpg.Record) -> ProfileRow:
    return ProfileRow(
        id=row["id"],
        user_id=row["user_id"],
        skills=row["skills"],
        experience=row["experience"],
        rate=row["rate"],
        rubric=row["rubric"],
        updated_at=row["updated_at"],
    )


class ProfileRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def find_by_user_id(self, user_id: UUID) -> ProfileRow | None:
        """Return the profile for the given user, or None if not set up yet."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, skills, experience, rate, rubric, updated_at
                FROM profiles
                WHERE user_id = $1
                """,
                user_id,
            )
        return _row_to_profile(row) if row else None

    async def upsert(
        self,
        user_id: UUID,
        skills: list,
        experience: str | None,
        rate: str | None,
        rubric: dict,
    ) -> ProfileRow:
        """Insert or update the profile for the given user. Returns the resulting row."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO profiles (user_id, skills, experience, rate, rubric, updated_at)
                VALUES ($1, $2::jsonb, $3, $4, $5::jsonb, now())
                ON CONFLICT (user_id) DO UPDATE SET
                    skills     = EXCLUDED.skills,
                    experience = EXCLUDED.experience,
                    rate       = EXCLUDED.rate,
                    rubric     = EXCLUDED.rubric,
                    updated_at = now()
                RETURNING id, user_id, skills, experience, rate, rubric, updated_at
                """,
                user_id,
                skills,
                experience,
                rate,
                rubric,
            )
        logger.debug("Upserted profile user_id=%s", user_id)
        return _row_to_profile(row)
