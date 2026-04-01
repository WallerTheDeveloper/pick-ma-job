"""Shared pytest fixtures for Phase 1 tests.

DB fixtures use a real PostgreSQL database pointed to by TEST_DATABASE_URL.
Each test gets a connection with an open transaction that is rolled back on
teardown — this keeps tests isolated without recreating the schema each time.

Set up a local test DB:
    docker run -d --name pickmajob-test -e POSTGRES_PASSWORD=test \\
        -e POSTGRES_DB=pickmajob_test -p 5433:5432 postgres:16
    export TEST_DATABASE_URL=postgresql://postgres:test@localhost:5433/pickmajob_test
"""

import os

import asyncpg
import pytest

from db.pool import create_pool, close_pool


@pytest.fixture(scope="session")
def test_database_url() -> str:
    url = os.environ.get("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL not set — skipping DB integration tests")
    return url


@pytest.fixture
async def db_pool(test_database_url: str) -> asyncpg.Pool:
    """Per-test pool — avoids event loop mismatch on Windows with pytest-asyncio."""
    pool = await create_pool(test_database_url)
    yield pool
    await close_pool(pool)


@pytest.fixture
async def db_conn(db_pool: asyncpg.Pool) -> asyncpg.Connection:
    """Per-test connection with a transaction that rolls back after each test.

    Repositories under test receive this connection wrapped in a single-conn pool
    shim — see ``single_conn_pool`` below.
    """
    async with db_pool.acquire() as conn:
        tx = conn.transaction()
        await tx.start()
        yield conn
        await tx.rollback()


@pytest.fixture
def conn_pool(db_conn: asyncpg.Connection) -> asyncpg.Pool:
    """A minimal asyncpg.Pool-like shim that always returns ``db_conn``.

    Repositories call ``pool.acquire()`` — this shim routes those calls to the
    single test connection so all queries run inside the rollback transaction.
    """
    class _SingleConnPool:
        """Minimal shim: acquire() returns the fixed connection as a context manager."""

        class _AcquireCtx:
            def __init__(self, conn):
                self._conn = conn

            async def __aenter__(self):
                return self._conn

            async def __aexit__(self, *args):
                pass  # Don't release — the outer fixture owns the connection

        def acquire(self):
            return self._AcquireCtx(db_conn)

    return _SingleConnPool()
