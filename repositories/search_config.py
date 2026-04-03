"""SearchConfigRepository — all database access for the search_configs table."""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchConfigRow:
    id: UUID
    user_id: UUID
    platform: str
    query: str | None
    filters: dict
    updated_at: datetime


def _row_to_search_config(row: asyncpg.Record) -> SearchConfigRow:
    return SearchConfigRow(
        id=row["id"],
        user_id=row["user_id"],
        platform=row["platform"],
        query=row["query"],
        filters=row["filters"],
        updated_at=row["updated_at"],
    )


class SearchConfigRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def find_by_user_id(self, user_id: UUID) -> list[SearchConfigRow]:
        """Return all search configs for a user."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, platform, query, filters, updated_at
                FROM search_configs
                WHERE user_id = $1
                ORDER BY platform
                """,
                user_id,
            )
        return [_row_to_search_config(r) for r in rows]

    async def find_by_user_and_platform(
        self, user_id: UUID, platform: str
    ) -> SearchConfigRow | None:
        """Return the search config for a specific user + platform, or None."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, platform, query, filters, updated_at
                FROM search_configs
                WHERE user_id = $1 AND platform = $2
                """,
                user_id,
                platform,
            )
        return _row_to_search_config(row) if row else None

    async def upsert(
        self,
        user_id: UUID,
        platform: str,
        query: str | None,
        filters: dict,
    ) -> SearchConfigRow:
        """Insert or update the config for user + platform. Returns the resulting row."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO search_configs (user_id, platform, query, filters, updated_at)
                VALUES ($1, $2, $3, $4::jsonb, now())
                ON CONFLICT (user_id, platform) DO UPDATE SET
                    query      = EXCLUDED.query,
                    filters    = EXCLUDED.filters,
                    updated_at = now()
                RETURNING id, user_id, platform, query, filters, updated_at
                """,
                user_id,
                platform,
                query,
                filters,
            )
        logger.debug("Upserted search config user_id=%s platform=%s", user_id, platform)
        return _row_to_search_config(row)

    async def delete(self, config_id: UUID, user_id: UUID) -> bool:
        """Delete a search config by id and user_id. Returns True if a row was deleted."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "DELETE FROM search_configs WHERE id = $1 AND user_id = $2 RETURNING id",
                config_id,
                user_id,
            )
        return row is not None
