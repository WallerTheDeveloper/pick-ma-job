"""UserRepository — all database access for the users table."""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class UserRow:
    id: UUID
    email: str
    created_at: datetime
    last_login: datetime | None


def _row_to_user(row: asyncpg.Record) -> UserRow:
    return UserRow(
        id=row["id"],
        email=row["email"],
        created_at=row["created_at"],
        last_login=row["last_login"],
    )


class UserRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def find_by_email(self, email: str) -> UserRow | None:
        """Return the user with the given email, or None if not found."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, email, created_at, last_login FROM users WHERE email = $1",
                email,
            )
        return _row_to_user(row) if row else None

    async def find_by_id(self, user_id: UUID) -> UserRow | None:
        """Return the user with the given id, or None if not found."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, email, created_at, last_login FROM users WHERE id = $1",
                user_id,
            )
        return _row_to_user(row) if row else None

    async def create(self, email: str) -> UserRow:
        """Insert a new user and return the created row."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO users (email)
                VALUES ($1)
                RETURNING id, email, created_at, last_login
                """,
                email,
            )
        logger.info("Created user email=%s id=%s", email, row["id"])
        return _row_to_user(row)

    async def update_last_login(self, user_id: UUID) -> None:
        """Set last_login to now() for the given user."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_login = now() WHERE id = $1",
                user_id,
            )
