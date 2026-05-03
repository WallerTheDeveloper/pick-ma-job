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
    is_admin: bool = False


@dataclass(frozen=True)
class UserStatsRow:
    id: UUID
    email: str
    created_at: datetime
    last_login: datetime | None
    job_count: int


def _row_to_user(row: asyncpg.Record) -> UserRow:
    return UserRow(
        id=row["id"],
        email=row["email"],
        created_at=row["created_at"],
        last_login=row["last_login"],
        is_admin=row.get("is_admin", False),
    )


class UserRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def find_by_email(self, email: str) -> UserRow | None:
        """Return the user with the given email, or None if not found."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, email, created_at, last_login, is_admin FROM users WHERE email = $1",
                email,
            )
        return _row_to_user(row) if row else None

    async def find_by_id(self, user_id: UUID) -> UserRow | None:
        """Return the user with the given id, or None if not found."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, email, created_at, last_login, is_admin FROM users WHERE id = $1",
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
                RETURNING id, email, created_at, last_login, is_admin
                """,
                email,
            )
        domain = email.split("@")[-1] if "@" in email else "?"
        logger.info("Created user domain=%s id=%s", domain, row["id"])
        return _row_to_user(row)

    async def list_users_with_stats(
        self, limit: int = 100, offset: int = 0
    ) -> list[UserStatsRow]:
        """Return users with their job_results count, paginated."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT u.id, u.email, u.created_at, u.last_login,
                       COALESCE(COUNT(jr.id), 0)::int AS job_count
                FROM users u
                LEFT JOIN job_results jr ON jr.user_id = u.id
                GROUP BY u.id
                ORDER BY u.created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset,
            )
        return [
            UserStatsRow(
                id=r["id"],
                email=r["email"],
                created_at=r["created_at"],
                last_login=r["last_login"],
                job_count=r["job_count"],
            )
            for r in rows
        ]

    async def count_users(self) -> int:
        """Return the total number of registered users."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow("SELECT COUNT(*) AS cnt FROM users")
        return row["cnt"]

    async def update_last_login(self, user_id: UUID) -> None:
        """Set last_login to now() for the given user."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET last_login = now() WHERE id = $1",
                user_id,
            )

    async def set_admin(self, user_id: UUID, is_admin: bool) -> None:
        """Set the is_admin flag for the given user."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                "UPDATE users SET is_admin = $2 WHERE id = $1",
                user_id,
                is_admin,
            )
        logger.info("Set is_admin=%s for user_id=%s", is_admin, user_id)
