"""Database migration runner.

Maintains a schema_migrations table and applies unapplied .sql files from
db/migrations/ in sorted order.

Two scenarios handled automatically:

1. Fresh install (no DB tables yet):
   Applies 000_initial_schema.sql first, then marks 001-003 as pre-applied
   (they are incorporated into the baseline), then applies any remaining
   migrations (004, 005, ...).

2. Existing install (DB was bootstrapped via schema.sql, no migration history):
   Pre-populates schema_migrations with 000-003 so they are not re-applied,
   then applies any new migrations (004, 005, ...).

Usage:
    python db/migrate.py
    DATABASE_URL=postgresql://... python db/migrate.py
"""

import asyncio
import logging
import os
from pathlib import Path

import asyncpg
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

_MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# Migrations already incorporated into 000_initial_schema.sql.
# On a fresh install (after 000 is applied), these are marked as pre-applied
# so the individual migration files are not executed again.
_SUBSUMED_BY_BASELINE = frozenset({
    "001_expand_profiles.sql",
    "002_multi_config_per_platform.sql",
    "003_job_list_items_index.sql",
})

# All migrations that are already reflected in schema.sql (pre-migration-system state).
# Used to bootstrap existing DBs that have no migration history.
_SCHEMA_SQL_INCORPORATED = frozenset({
    "000_initial_schema.sql",
    "001_expand_profiles.sql",
    "002_multi_config_per_platform.sql",
    "003_job_list_items_index.sql",
})


async def run(database_url: str) -> None:
    """Apply all unapplied migrations in db/migrations/ to the given database."""
    conn = await asyncpg.connect(dsn=database_url)
    try:
        await _run_migrations(conn)
    finally:
        await conn.close()


async def _run_migrations(conn: asyncpg.Connection) -> None:
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            filename   TEXT        PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    applied: set[str] = {r["filename"] for r in await conn.fetch("SELECT filename FROM schema_migrations")}

    # Bootstrap: existing DB that was set up via schema.sql has no migration history yet.
    if not applied:
        users_exists: bool = await conn.fetchval(
            "SELECT EXISTS("
            "  SELECT 1 FROM information_schema.tables"
            "  WHERE table_schema = 'public' AND table_name = 'users'"
            ")"
        )
        if users_exists:
            for filename in sorted(_SCHEMA_SQL_INCORPORATED):
                await conn.execute(
                    "INSERT INTO schema_migrations (filename) VALUES ($1) ON CONFLICT DO NOTHING",
                    filename,
                )
                logger.info("Pre-applied (already in schema.sql): %s", filename)
            applied = set(_SCHEMA_SQL_INCORPORATED)

    migration_files = sorted(_MIGRATIONS_DIR.glob("*.sql"))
    for path in migration_files:
        if path.name in applied:
            logger.debug("Already applied: %s", path.name)
            continue

        sql = path.read_text(encoding="utf-8")
        logger.info("Applying migration: %s", path.name)
        async with conn.transaction():
            await conn.execute(sql)
            await conn.execute(
                "INSERT INTO schema_migrations (filename) VALUES ($1)",
                path.name,
            )
        applied.add(path.name)
        logger.info("Applied: %s", path.name)

        # After the baseline migration, mark subsumed migrations as pre-applied
        # so they are skipped (their changes are already in 000_initial_schema.sql).
        if path.name == "000_initial_schema.sql":
            for name in sorted(_SUBSUMED_BY_BASELINE):
                if name not in applied:
                    await conn.execute(
                        "INSERT INTO schema_migrations (filename) VALUES ($1) ON CONFLICT DO NOTHING",
                        name,
                    )
                    applied.add(name)
                    logger.info("Pre-applied (subsumed by baseline): %s", name)

    logger.info("Migrations complete. Applied: %d total.", len(applied))


if __name__ == "__main__":
    load_dotenv()
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s — %(message)s",
    )
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL environment variable is not set")
    asyncio.run(run(database_url))
