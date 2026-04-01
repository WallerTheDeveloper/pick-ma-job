"""SessionRepository — all database access for the sessions table."""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SessionRow:
    id: UUID
    user_id: UUID
    token: str
    expires_at: datetime
    created_at: datetime


def _row_to_session(row: asyncpg.Record) -> SessionRow:
    return SessionRow(
        id=row["id"],
        user_id=row["user_id"],
        token=row["token"],
        expires_at=row["expires_at"],
        created_at=row["created_at"],
    )


class SessionRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def create(self, user_id: UUID, token: str, expires_at: datetime) -> SessionRow:
        """Insert a new session and return the created row."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO sessions (user_id, token, expires_at)
                VALUES ($1, $2, $3)
                RETURNING id, user_id, token, expires_at, created_at
                """,
                user_id,
                token,
                expires_at,
            )
        logger.debug("Created session user_id=%s", user_id)
        return _row_to_session(row)

    async def find_by_token(self, token: str) -> SessionRow | None:
        """Return a non-expired session matching the token, or None."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, token, expires_at, created_at
                FROM sessions
                WHERE token = $1 AND expires_at > now()
                """,
                token,
            )
        return _row_to_session(row) if row else None

    async def delete(self, session_id: UUID) -> None:
        """Delete a session by id."""
        async with self._pool.acquire() as conn:
            await conn.execute("DELETE FROM sessions WHERE id = $1", session_id)

    async def delete_expired(self) -> int:
        """Delete all expired sessions. Returns the number of rows deleted."""
        async with self._pool.acquire() as conn:
            result = await conn.execute("DELETE FROM sessions WHERE expires_at <= now()")
        count = int(result.split()[-1])
        logger.info("Deleted %d expired sessions", count)
        return count
