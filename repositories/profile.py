"""ProfileRepository — all database access for the profiles table."""

import json
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
    role: str | None
    experience: str | None
    rate: str | None
    primary_skills: list[str]
    secondary_skills: list[str]
    tertiary_skills: list[str]
    not_a_good_fit: list[str]
    background: list[str]
    notable_projects: list[dict]
    languages: list[str]
    rubric: dict
    updated_at: datetime


def _row_to_profile(row: asyncpg.Record) -> ProfileRow:
    return ProfileRow(
        id=row["id"],
        user_id=row["user_id"],
        role=row["role"],
        experience=row["experience"],
        rate=row["rate"],
        primary_skills=list(row["primary_skills"] or []),
        secondary_skills=list(row["secondary_skills"] or []),
        tertiary_skills=list(row["tertiary_skills"] or []),
        not_a_good_fit=list(row["not_a_good_fit"] or []),
        background=list(row["background"] or []),
        notable_projects=list(row["notable_projects"] or []),
        languages=list(row["languages"] or []),
        rubric=dict(row["rubric"] or {}),
        updated_at=row["updated_at"],
    )


_SELECT = """
    SELECT id, user_id, role, experience, rate,
           primary_skills, secondary_skills, tertiary_skills,
           not_a_good_fit, background, notable_projects, languages,
           rubric, updated_at
    FROM profiles
"""


class ProfileRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def find_by_user_id(self, user_id: UUID) -> ProfileRow | None:
        """Return the profile for the given user, or None if not set up yet."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"{_SELECT} WHERE user_id = $1",
                user_id,
            )
        return _row_to_profile(row) if row else None

    async def upsert(
        self,
        user_id: UUID,
        role: str | None = None,
        experience: str | None = None,
        rate: str | None = None,
        primary_skills: list[str] | None = None,
        secondary_skills: list[str] | None = None,
        tertiary_skills: list[str] | None = None,
        not_a_good_fit: list[str] | None = None,
        background: list[str] | None = None,
        notable_projects: list[dict] | None = None,
        languages: list[str] | None = None,
        rubric: dict | None = None,
    ) -> ProfileRow:
        """Insert or update the profile for the given user. Returns the resulting row."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO profiles (
                    user_id, role, experience, rate,
                    primary_skills, secondary_skills, tertiary_skills,
                    not_a_good_fit, background, notable_projects, languages,
                    rubric, updated_at
                )
                VALUES (
                    $1, $2, $3, $4,
                    $5, $6, $7,
                    $8, $9, $10::jsonb, $11,
                    $12::jsonb, now()
                )
                ON CONFLICT (user_id) DO UPDATE SET
                    role             = EXCLUDED.role,
                    experience       = EXCLUDED.experience,
                    rate             = EXCLUDED.rate,
                    primary_skills   = EXCLUDED.primary_skills,
                    secondary_skills = EXCLUDED.secondary_skills,
                    tertiary_skills  = EXCLUDED.tertiary_skills,
                    not_a_good_fit   = EXCLUDED.not_a_good_fit,
                    background       = EXCLUDED.background,
                    notable_projects = EXCLUDED.notable_projects,
                    languages        = EXCLUDED.languages,
                    rubric           = EXCLUDED.rubric,
                    updated_at       = now()
                RETURNING id, user_id, role, experience, rate,
                          primary_skills, secondary_skills, tertiary_skills,
                          not_a_good_fit, background, notable_projects, languages,
                          rubric, updated_at
                """,
                user_id,
                role,
                experience,
                rate,
                primary_skills or [],
                secondary_skills or [],
                tertiary_skills or [],
                not_a_good_fit or [],
                background or [],
                json.dumps(notable_projects or []),
                languages or [],
                json.dumps(rubric or {}),
            )
        logger.debug("Upserted profile user_id=%s", user_id)
        return _row_to_profile(row)
