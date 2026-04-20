"""CompanyBlacklistRepository — all database access for the company_blacklist table."""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CompanyBlacklistEntry:
    id: UUID
    user_id: UUID
    name: str
    name_lower: str
    created_at: datetime


def _row_to_entry(row: asyncpg.Record) -> CompanyBlacklistEntry:
    return CompanyBlacklistEntry(
        id=row["id"],
        user_id=row["user_id"],
        name=row["name"],
        name_lower=row["name_lower"],
        created_at=row["created_at"],
    )


_SELECT = "SELECT id, user_id, name, name_lower, created_at FROM company_blacklist"


class CompanyBlacklistRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def find_by_user_id(self, user_id: UUID) -> list[CompanyBlacklistEntry]:
        """Return all blacklist entries for the user, ordered by name."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                f"{_SELECT} WHERE user_id = $1 ORDER BY name",
                user_id,
            )
        return [_row_to_entry(r) for r in rows]

    async def find_names_by_user_id(self, user_id: UUID) -> tuple[str, ...]:
        """Return lowercase company names for the user; used by pipeline filter."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT name_lower FROM company_blacklist WHERE user_id = $1",
                user_id,
            )
        return tuple(r["name_lower"] for r in rows)

    async def insert(self, user_id: UUID, name: str) -> CompanyBlacklistEntry | None:
        """Insert a blacklist entry; returns None on duplicate."""
        name_lower = name.strip().lower()
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO company_blacklist (user_id, name, name_lower)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, name_lower) DO NOTHING
                RETURNING id, user_id, name, name_lower, created_at
                """,
                user_id,
                name.strip(),
                name_lower,
            )
        if row is None:
            return None
        logger.debug("Inserted blacklist entry user_id=%s name=%s", user_id, name)
        return _row_to_entry(row)

    async def delete(self, user_id: UUID, entry_id: UUID) -> bool:
        """Delete an entry scoped by user_id; returns False if not found."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM company_blacklist WHERE id = $1 AND user_id = $2",
                entry_id,
                user_id,
            )
        deleted = result == "DELETE 1"
        if deleted:
            logger.debug("Deleted blacklist entry id=%s user_id=%s", entry_id, user_id)
        return deleted

    async def exists(self, user_id: UUID, name_lower: str) -> bool:
        """Return True if the user already has this company blacklisted."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT 1 FROM company_blacklist WHERE user_id = $1 AND name_lower = $2",
                user_id,
                name_lower,
            )
        return row is not None
