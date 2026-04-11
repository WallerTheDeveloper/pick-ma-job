"""asyncpg connection pool — created once at app startup, closed on shutdown."""

import logging
from pathlib import Path

import asyncpg

logger = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"


async def _init_conn(conn: asyncpg.Connection) -> None:
    """Register JSON/JSONB codec so asyncpg returns dicts instead of strings."""
    await conn.set_type_codec(
        "jsonb",
        encoder=lambda v: __import__("json").dumps(v),
        decoder=lambda v: __import__("json").loads(v),
        schema="pg_catalog",
        format="text",
    )
    await conn.set_type_codec(
        "json",
        encoder=lambda v: __import__("json").dumps(v),
        decoder=lambda v: __import__("json").loads(v),
        schema="pg_catalog",
        format="text",
    )


async def init_db(conn: asyncpg.Connection) -> None:
    """Run schema.sql against the database. Safe to call multiple times (idempotent DDL)."""
    sql = _SCHEMA_PATH.read_text(encoding="utf-8")
    await conn.execute(sql)
    logger.info("Database schema initialised")


async def create_pool(database_url: str) -> asyncpg.Pool:
    """Create and return an asyncpg connection pool.

    DDL is no longer run automatically on startup. Migrations are handled by
    db/migrate.py, which deploy.sh runs before restarting the service.
    For local development, run: python db/migrate.py
    """
    pool = await asyncpg.create_pool(
        dsn=database_url,
        min_size=2,
        max_size=10,
        init=_init_conn,
    )
    logger.info("Database pool created (min=2, max=10)")
    return pool


async def close_pool(pool: asyncpg.Pool) -> None:
    """Gracefully close all connections in the pool."""
    await pool.close()
    logger.info("Database pool closed")
