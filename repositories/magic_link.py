"""MagicLinkRepository — all database access for the magic_links table."""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MagicLinkRow:
    id: UUID
    user_id: UUID
    token: str
    used: bool
    expires_at: datetime
    created_at: datetime


def _row_to_magic_link(row: asyncpg.Record) -> MagicLinkRow:
    return MagicLinkRow(
        id=row["id"],
        user_id=row["user_id"],
        token=row["token"],
        used=row["used"],
        expires_at=row["expires_at"],
        created_at=row["created_at"],
    )


class MagicLinkRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(self, user_id: UUID, token: str, expires_at: datetime) -> MagicLinkRow:
        """Insert a new magic link and return the created row."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO magic_links (user_id, token, expires_at)
                VALUES ($1, $2, $3)
                RETURNING id, user_id, token, used, expires_at, created_at
                """,
                user_id,
                token,
                expires_at,
            )
        logger.debug("Created magic link user_id=%s", user_id)
        return _row_to_magic_link(row)

    async def find_by_token(self, token: str) -> MagicLinkRow | None:
        """Return the magic link matching the token (any state), or None.

        Expiry and used-state checks are the caller's responsibility.
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, token, used, expires_at, created_at
                FROM magic_links
                WHERE token = $1
                """,
                token,
            )
        return _row_to_magic_link(row) if row else None

    async def count_recent_for_user(self, user_id: UUID, within_seconds: int) -> int:
        """Return how many magic links were created for this user in the last N seconds."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT COUNT(*) AS cnt
                FROM magic_links
                WHERE user_id = $1
                  AND created_at > now() - ($2 || ' seconds')::interval
                """,
                user_id,
                str(within_seconds),
            )
        return row["cnt"]

    async def mark_used(self, link_id: UUID) -> None:
        """Mark a magic link as used."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE magic_links SET used = TRUE WHERE id = $1",
                link_id,
            )

    async def delete_expired(self) -> int:
        """Delete all expired magic links. Returns the number of rows deleted."""
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM magic_links WHERE expires_at <= now()"
            )
        count = int(result.split()[-1])
        logger.info("Deleted %d expired magic links", count)
        return count
