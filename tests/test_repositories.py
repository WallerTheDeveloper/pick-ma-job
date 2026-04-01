"""Integration tests for all repository classes.

Requires TEST_DATABASE_URL to be set. Each test runs inside a transaction
that is rolled back on teardown (see conftest.py).
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from repositories.job_result import JobResultRepository
from repositories.magic_link import MagicLinkRepository
from repositories.profile import ProfileRepository
from repositories.search_config import SearchConfigRepository
from repositories.session import SessionRepository
from repositories.user import UserRepository


# ── Helpers ───────────────────────────────────────────────────────────────────

def _future(seconds: int = 900) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


def _past(seconds: int = 60) -> datetime:
    return datetime.now(timezone.utc) - timedelta(seconds=seconds)


# ── UserRepository ────────────────────────────────────────────────────────────

async def test_user_create_and_find_by_email(conn_pool):
    repo = UserRepository(conn_pool)
    email = f"test-{uuid4().hex[:8]}@example.com"

    user = await repo.create(email)

    assert user.email == email
    assert user.id is not None
    assert user.last_login is None

    found = await repo.find_by_email(email)
    assert found is not None
    assert found.id == user.id


async def test_user_find_by_id(conn_pool):
    repo = UserRepository(conn_pool)
    email = f"test-{uuid4().hex[:8]}@example.com"
    user = await repo.create(email)

    found = await repo.find_by_id(user.id)
    assert found is not None
    assert found.email == email


async def test_user_find_by_email_not_found_returns_none(conn_pool):
    repo = UserRepository(conn_pool)
    result = await repo.find_by_email("nobody@nowhere.example")
    assert result is None


async def test_user_find_by_id_not_found_returns_none(conn_pool):
    repo = UserRepository(conn_pool)
    result = await repo.find_by_id(uuid4())
    assert result is None


async def test_user_update_last_login(conn_pool):
    repo = UserRepository(conn_pool)
    email = f"test-{uuid4().hex[:8]}@example.com"
    user = await repo.create(email)
    assert user.last_login is None

    await repo.update_last_login(user.id)

    updated = await repo.find_by_id(user.id)
    assert updated.last_login is not None


# ── SessionRepository ─────────────────────────────────────────────────────────

async def test_session_create_and_find_by_token(conn_pool):
    user_repo = UserRepository(conn_pool)
    session_repo = SessionRepository(conn_pool)

    user = await user_repo.create(f"test-{uuid4().hex[:8]}@example.com")
    token = f"tok-{uuid4().hex}"
    session = await session_repo.create(user.id, token, _future())

    assert session.user_id == user.id
    assert session.token == token

    found = await session_repo.find_by_token(token)
    assert found is not None
    assert found.id == session.id


async def test_session_find_expired_returns_none(conn_pool):
    user_repo = UserRepository(conn_pool)
    session_repo = SessionRepository(conn_pool)

    user = await user_repo.create(f"test-{uuid4().hex[:8]}@example.com")
    token = f"tok-{uuid4().hex}"
    await session_repo.create(user.id, token, _past())

    found = await session_repo.find_by_token(token)
    assert found is None


async def test_session_delete(conn_pool):
    user_repo = UserRepository(conn_pool)
    session_repo = SessionRepository(conn_pool)

    user = await user_repo.create(f"test-{uuid4().hex[:8]}@example.com")
    token = f"tok-{uuid4().hex}"
    session = await session_repo.create(user.id, token, _future())

    await session_repo.delete(session.id)

    found = await session_repo.find_by_token(token)
    assert found is None


# ── MagicLinkRepository ───────────────────────────────────────────────────────

async def test_magic_link_create_find_and_mark_used(conn_pool):
    user_repo = UserRepository(conn_pool)
    ml_repo = MagicLinkRepository(conn_pool)

    user = await user_repo.create(f"test-{uuid4().hex[:8]}@example.com")
    token = f"ml-{uuid4().hex}"
    link = await ml_repo.create(user.id, token, _future())

    assert not link.used

    found = await ml_repo.find_by_token(token)
    assert found is not None
    assert not found.used

    await ml_repo.mark_used(link.id)

    found_after = await ml_repo.find_by_token(token)
    assert found_after.used is True


async def test_magic_link_find_nonexistent_returns_none(conn_pool):
    ml_repo = MagicLinkRepository(conn_pool)
    result = await ml_repo.find_by_token("does-not-exist")
    assert result is None


async def test_magic_link_expired_still_returned(conn_pool):
    """find_by_token returns expired links — expiry check is the service's job."""
    user_repo = UserRepository(conn_pool)
    ml_repo = MagicLinkRepository(conn_pool)

    user = await user_repo.create(f"test-{uuid4().hex[:8]}@example.com")
    token = f"ml-{uuid4().hex}"
    await ml_repo.create(user.id, token, _past())

    found = await ml_repo.find_by_token(token)
    assert found is not None


async def test_magic_link_count_recent_for_user(conn_pool):
    user_repo = UserRepository(conn_pool)
    ml_repo = MagicLinkRepository(conn_pool)

    user = await user_repo.create(f"test-{uuid4().hex[:8]}@example.com")

    count_before = await ml_repo.count_recent_for_user(user.id, 600)
    assert count_before == 0

    await ml_repo.create(user.id, f"ml-{uuid4().hex}", _future())
    await ml_repo.create(user.id, f"ml-{uuid4().hex}", _future())

    count_after = await ml_repo.count_recent_for_user(user.id, 600)
    assert count_after == 2


# ── ProfileRepository ─────────────────────────────────────────────────────────

async def test_profile_upsert_creates(conn_pool):
    user_repo = UserRepository(conn_pool)
    profile_repo = ProfileRepository(conn_pool)

    user = await user_repo.create(f"test-{uuid4().hex[:8]}@example.com")
    profile = await profile_repo.upsert(
        user.id,
        skills=["Unity", "C#"],
        experience="4 years",
        rate="€20/hr",
        rubric={"min_score": 7},
    )

    assert profile.user_id == user.id
    assert profile.skills == ["Unity", "C#"]
    assert profile.experience == "4 years"
    assert profile.rate == "€20/hr"


async def test_profile_upsert_updates(conn_pool):
    user_repo = UserRepository(conn_pool)
    profile_repo = ProfileRepository(conn_pool)

    user = await user_repo.create(f"test-{uuid4().hex[:8]}@example.com")
    await profile_repo.upsert(user.id, skills=["Unity"], experience="2 years", rate=None, rubric={})
    updated = await profile_repo.upsert(user.id, skills=["Unity", "Rust"], experience="4 years", rate="€25/hr", rubric={})

    assert updated.skills == ["Unity", "Rust"]
    assert updated.experience == "4 years"
    assert updated.rate == "€25/hr"


async def test_profile_find_by_user_id_not_found(conn_pool):
    profile_repo = ProfileRepository(conn_pool)
    result = await profile_repo.find_by_user_id(uuid4())
    assert result is None


# ── SearchConfigRepository ────────────────────────────────────────────────────

async def test_search_config_upsert_and_find(conn_pool):
    user_repo = UserRepository(conn_pool)
    sc_repo = SearchConfigRepository(conn_pool)

    user = await user_repo.create(f"test-{uuid4().hex[:8]}@example.com")
    config = await sc_repo.upsert(user.id, "upwork", "unity developer", {"maxJobAge": 24})

    assert config.user_id == user.id
    assert config.platform == "upwork"
    assert config.query == "unity developer"
    assert config.filters["maxJobAge"] == 24


async def test_search_config_upsert_updates(conn_pool):
    user_repo = UserRepository(conn_pool)
    sc_repo = SearchConfigRepository(conn_pool)

    user = await user_repo.create(f"test-{uuid4().hex[:8]}@example.com")
    await sc_repo.upsert(user.id, "upwork", "unity", {})
    updated = await sc_repo.upsert(user.id, "upwork", "unity ar developer", {"perPage": 50})

    assert updated.query == "unity ar developer"
    assert updated.filters["perPage"] == 50


async def test_search_config_find_by_user_and_platform(conn_pool):
    user_repo = UserRepository(conn_pool)
    sc_repo = SearchConfigRepository(conn_pool)

    user = await user_repo.create(f"test-{uuid4().hex[:8]}@example.com")
    await sc_repo.upsert(user.id, "upwork", "unity", {})
    await sc_repo.upsert(user.id, "linkedin", "unity developer", {})

    upwork = await sc_repo.find_by_user_and_platform(user.id, "upwork")
    assert upwork is not None
    assert upwork.platform == "upwork"

    linkedin = await sc_repo.find_by_user_and_platform(user.id, "linkedin")
    assert linkedin is not None

    all_configs = await sc_repo.find_by_user_id(user.id)
    assert len(all_configs) == 2


async def test_search_config_delete(conn_pool):
    user_repo = UserRepository(conn_pool)
    sc_repo = SearchConfigRepository(conn_pool)

    user = await user_repo.create(f"test-{uuid4().hex[:8]}@example.com")
    config = await sc_repo.upsert(user.id, "upwork", "unity", {})
    await sc_repo.delete(config.id)

    found = await sc_repo.find_by_user_and_platform(user.id, "upwork")
    assert found is None


# ── JobResultRepository ───────────────────────────────────────────────────────

async def test_job_result_insert_and_find(conn_pool):
    user_repo = UserRepository(conn_pool)
    jr_repo = JobResultRepository(conn_pool)

    user = await user_repo.create(f"test-{uuid4().hex[:8]}@example.com")
    result = await jr_repo.insert(
        user.id, "upwork", "job-001", "Unity Developer", "https://upwork.com/1", 8,
        {"recommendation": "Yes apply"},
    )

    assert result is not None
    assert result.score == 8
    assert result.status == "new"

    rows = await jr_repo.find_by_user(user.id)
    assert len(rows) == 1
    assert rows[0].job_id == "job-001"


async def test_job_result_insert_duplicate_returns_none(conn_pool):
    user_repo = UserRepository(conn_pool)
    jr_repo = JobResultRepository(conn_pool)

    user = await user_repo.create(f"test-{uuid4().hex[:8]}@example.com")
    await jr_repo.insert(user.id, "upwork", "job-dup", "Title", "https://example.com", 7, None)
    second = await jr_repo.insert(user.id, "upwork", "job-dup", "Title", "https://example.com", 7, None)

    assert second is None

    rows = await jr_repo.find_by_user(user.id)
    assert len(rows) == 1


async def test_job_result_exists(conn_pool):
    user_repo = UserRepository(conn_pool)
    jr_repo = JobResultRepository(conn_pool)

    user = await user_repo.create(f"test-{uuid4().hex[:8]}@example.com")
    assert not await jr_repo.exists(user.id, "upwork", "job-x")

    await jr_repo.insert(user.id, "upwork", "job-x", "Title", "https://example.com", 5, None)
    assert await jr_repo.exists(user.id, "upwork", "job-x")


async def test_job_result_update_status(conn_pool):
    user_repo = UserRepository(conn_pool)
    jr_repo = JobResultRepository(conn_pool)

    user = await user_repo.create(f"test-{uuid4().hex[:8]}@example.com")
    result = await jr_repo.insert(user.id, "upwork", "job-s", "Title", "https://example.com", 6, None)

    await jr_repo.update_status(result.id, "applied")

    rows = await jr_repo.find_by_user(user.id, status="applied")
    assert len(rows) == 1
    assert rows[0].status == "applied"


async def test_job_result_update_status_invalid_raises(conn_pool):
    jr_repo = JobResultRepository(conn_pool)
    with pytest.raises(ValueError, match="Invalid status"):
        await jr_repo.update_status(uuid4(), "pending")


async def test_job_result_find_by_user_filters(conn_pool):
    user_repo = UserRepository(conn_pool)
    jr_repo = JobResultRepository(conn_pool)

    user = await user_repo.create(f"test-{uuid4().hex[:8]}@example.com")
    await jr_repo.insert(user.id, "upwork", "j1", "High Score", "https://example.com/1", 9, None)
    await jr_repo.insert(user.id, "upwork", "j2", "Low Score", "https://example.com/2", 4, None)

    high = await jr_repo.find_by_user(user.id, min_score=7)
    assert len(high) == 1
    assert high[0].job_id == "j1"


async def test_job_result_count_by_user(conn_pool):
    user_repo = UserRepository(conn_pool)
    jr_repo = JobResultRepository(conn_pool)

    user = await user_repo.create(f"test-{uuid4().hex[:8]}@example.com")
    await jr_repo.insert(user.id, "upwork", "c1", "Title", "https://example.com/1", 8, None)
    await jr_repo.insert(user.id, "upwork", "c2", "Title", "https://example.com/2", 5, None)

    total = await jr_repo.count_by_user(user.id)
    assert total == 2

    new_count = await jr_repo.count_by_user(user.id, status="new")
    assert new_count == 2
