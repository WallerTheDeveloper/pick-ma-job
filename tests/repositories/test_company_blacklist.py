"""Integration tests for CompanyBlacklistRepository.

Requires TEST_DATABASE_URL with the company_blacklist table already created.
Each test runs inside a rolled-back transaction for isolation.
"""

import pytest
from uuid import uuid4

from repositories.company_blacklist import CompanyBlacklistRepository


@pytest.fixture
def repo(conn_pool):
    return CompanyBlacklistRepository(conn_pool)


@pytest.fixture
async def user_id(db_conn):
    uid = uuid4()
    await db_conn.execute(
        "INSERT INTO users (id, email) VALUES ($1, $2)",
        uid,
        f"{uid}@test.com",
    )
    return uid


@pytest.fixture
async def other_user_id(db_conn):
    uid = uuid4()
    await db_conn.execute(
        "INSERT INTO users (id, email) VALUES ($1, $2)",
        uid,
        f"{uid}@other.com",
    )
    return uid


@pytest.mark.asyncio
async def test_insert_returns_entry(repo, user_id):
    entry = await repo.insert(user_id, "Google")
    assert entry is not None
    assert entry.name == "Google"
    assert entry.name_lower == "google"
    assert entry.user_id == user_id


@pytest.mark.asyncio
async def test_insert_returns_none_on_duplicate(repo, user_id):
    await repo.insert(user_id, "Google")
    result = await repo.insert(user_id, "Google")
    assert result is None


@pytest.mark.asyncio
async def test_insert_case_insensitive_duplicate(repo, user_id):
    await repo.insert(user_id, "Google")
    result = await repo.insert(user_id, "GOOGLE")
    assert result is None


@pytest.mark.asyncio
async def test_delete_returns_true_on_success(repo, user_id):
    entry = await repo.insert(user_id, "Acme")
    deleted = await repo.delete(user_id, entry.id)
    assert deleted is True


@pytest.mark.asyncio
async def test_delete_returns_false_for_nonexistent(repo, user_id):
    deleted = await repo.delete(user_id, uuid4())
    assert deleted is False


@pytest.mark.asyncio
async def test_delete_returns_false_for_foreign_entry(repo, user_id, other_user_id):
    entry = await repo.insert(user_id, "BigCorp")
    deleted = await repo.delete(other_user_id, entry.id)
    assert deleted is False


@pytest.mark.asyncio
async def test_find_names_by_user_id_returns_lowercase_only(repo, user_id, other_user_id):
    await repo.insert(user_id, "Google")
    await repo.insert(user_id, "Meta")
    await repo.insert(other_user_id, "Apple")

    names = await repo.find_names_by_user_id(user_id)
    assert set(names) == {"google", "meta"}
    assert isinstance(names, tuple)
