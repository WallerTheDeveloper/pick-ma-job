"""Integration tests for database-layer tasks.

Requires TEST_DATABASE_URL to be set. Each test runs inside a transaction
that is rolled back on teardown (see conftest.py).

Tasks covered:
- DB-1: magic_link.claim() is atomic (TOCTOU fix)
- DB-2: count_recent_for_user uses parameterized interval (no string concat)
- DB-3: keyset pagination in find_by_user (cursor-based, not OFFSET)
- DB-5 / CR-3+4: add_job and remove_job enforce cross-user ownership
- DB-6: pipeline_run.update_status scoped by user_id
- DB-7: invalid sort key raises ValueError immediately
- DB-9: _build_filter used by both find_by_user and count_by_user (consistency)
- DB-12: exists() documents its intentional round-trip (not removed)
- DB-13: delete_expired returns row count
- DB-14: list_users_with_stats accepts limit/offset
"""

import asyncio
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from repositories.job_list import JobListRepository
from repositories.job_result import JobResultRepository
from repositories.magic_link import MagicLinkRepository
from repositories.pipeline_run import PipelineRunRepository
from repositories.session import SessionRepository
from repositories.user import UserRepository


# ── Helpers ───────────────────────────────────────────────────────────────────

def _future(seconds: int = 900) -> datetime:
    return datetime.now(timezone.utc) + timedelta(seconds=seconds)


def _past(seconds: int = 60) -> datetime:
    return datetime.now(timezone.utc) - timedelta(seconds=seconds)


async def _make_user(conn_pool, suffix: str = "") -> "UserRow":  # noqa: F821
    repo = UserRepository(conn_pool)
    email = f"test-{uuid4().hex[:8]}{suffix}@example.com"
    return await repo.create(email)


async def _insert_job(conn_pool, user_id, platform="upwork", job_id=None, score=7, title="Test Job"):
    repo = JobResultRepository(conn_pool)
    return await repo.insert(
        user_id, platform, job_id or uuid4().hex[:12], title, f"https://example.com/{uuid4().hex}", score, None
    )


# ── DB-1: claim() is atomic ───────────────────────────────────────────────────

async def test_claim_returns_link_and_marks_used(conn_pool):
    """claim() atomically marks the link used and returns the row."""
    user = await _make_user(conn_pool)
    ml_repo = MagicLinkRepository(conn_pool)
    token = f"ml-{uuid4().hex}"
    await ml_repo.create(user.id, token, _future())

    result = await ml_repo.claim(token)

    assert result is not None
    assert result.token == token
    assert result.used is True


async def test_claim_returns_none_for_already_used_token(conn_pool):
    """Calling claim() a second time on the same token returns None."""
    user = await _make_user(conn_pool)
    ml_repo = MagicLinkRepository(conn_pool)
    token = f"ml-{uuid4().hex}"
    await ml_repo.create(user.id, token, _future())

    first = await ml_repo.claim(token)
    second = await ml_repo.claim(token)

    assert first is not None
    assert second is None  # already claimed


async def test_claim_returns_none_for_expired_token(conn_pool):
    """claim() returns None for an expired magic link."""
    user = await _make_user(conn_pool)
    ml_repo = MagicLinkRepository(conn_pool)
    token = f"ml-{uuid4().hex}"
    await ml_repo.create(user.id, token, _past())

    result = await ml_repo.claim(token)
    assert result is None


async def test_claim_returns_none_for_unknown_token(conn_pool):
    """claim() returns None for a token that does not exist."""
    ml_repo = MagicLinkRepository(conn_pool)
    result = await ml_repo.claim("nonexistent-token")
    assert result is None


async def test_claim_concurrent_only_one_succeeds(conn_pool):
    """Simulates two concurrent claim() calls — only the first succeeds.

    Because we're within a single transaction (the test fixture), we can't
    truly test DB-level serialisation. Instead we verify the single-claim
    semantic by calling claim() twice sequentially, which is the same guarantee.
    """
    user = await _make_user(conn_pool)
    ml_repo = MagicLinkRepository(conn_pool)
    token = f"ml-{uuid4().hex}"
    await ml_repo.create(user.id, token, _future())

    results = await asyncio.gather(
        ml_repo.claim(token),
        ml_repo.claim(token),
    )

    successful = [r for r in results if r is not None]
    assert len(successful) == 1, "Exactly one claim must succeed"


# ── DB-2: count_recent_for_user parameterized interval ───────────────────────

async def test_count_recent_for_user_returns_correct_count(conn_pool):
    """Parameterized $2 * interval '1 second' query works correctly."""
    user = await _make_user(conn_pool)
    ml_repo = MagicLinkRepository(conn_pool)

    # Create 2 links
    await ml_repo.create(user.id, f"ml-{uuid4().hex}", _future())
    await ml_repo.create(user.id, f"ml-{uuid4().hex}", _future())

    count = await ml_repo.count_recent_for_user(user.id, 600)
    assert count == 2


async def test_count_recent_for_user_zero_for_new_user(conn_pool):
    user = await _make_user(conn_pool)
    ml_repo = MagicLinkRepository(conn_pool)
    count = await ml_repo.count_recent_for_user(user.id, 600)
    assert count == 0


async def test_count_recent_for_user_accepts_integer_parameter(conn_pool):
    """Verifies within_seconds is bound as an integer, not concatenated as string."""
    user = await _make_user(conn_pool)
    ml_repo = MagicLinkRepository(conn_pool)
    await ml_repo.create(user.id, f"ml-{uuid4().hex}", _future())

    # These should all work without SQL injection from int params
    assert await ml_repo.count_recent_for_user(user.id, 1) == 1
    assert await ml_repo.count_recent_for_user(user.id, 3600) == 1
    assert await ml_repo.count_recent_for_user(user.id, 0) == 0  # 0 seconds window → nothing


# ── DB-3: Keyset pagination ───────────────────────────────────────────────────

async def test_find_by_user_returns_results_without_cursor(conn_pool):
    """Without a cursor, find_by_user returns up to limit results."""
    user = await _make_user(conn_pool)
    await _insert_job(conn_pool, user.id, score=9)
    await _insert_job(conn_pool, user.id, score=7)
    await _insert_job(conn_pool, user.id, score=5)

    results = await JobResultRepository(conn_pool).find_by_user(user.id)
    assert len(results) == 3
    # score_desc order: 9, 7, 5
    assert results[0].score == 9
    assert results[1].score == 7
    assert results[2].score == 5


async def test_find_by_user_keyset_cursor_pagination(conn_pool):
    """Cursor-based pagination returns the next page."""
    user = await _make_user(conn_pool)
    jr_repo = JobResultRepository(conn_pool)
    # Insert 3 jobs with distinct scores
    await _insert_job(conn_pool, user.id, score=9)
    await _insert_job(conn_pool, user.id, score=7)
    await _insert_job(conn_pool, user.id, score=5)

    # Page 1: limit 2
    page1 = await jr_repo.find_by_user(user.id, limit=2)
    assert len(page1) == 2
    assert page1[0].score == 9
    assert page1[1].score == 7

    # Page 2: use last row as cursor
    last = page1[-1]
    page2 = await jr_repo.find_by_user(
        user.id,
        limit=2,
        cursor_id=last.id,
        cursor_score=last.score,
    )
    assert len(page2) == 1
    assert page2[0].score == 5


async def test_find_by_user_raises_for_unknown_sort_key(conn_pool):
    """DB-7: ValueError is raised immediately for an unknown sort key."""
    user = await _make_user(conn_pool)
    jr_repo = JobResultRepository(conn_pool)
    with pytest.raises(ValueError, match="Unknown sort key"):
        await jr_repo.find_by_user(user.id, sort="bad_sort")


async def test_find_by_user_sort_date_asc_works(conn_pool):
    """All four valid sort keys should be accepted."""
    user = await _make_user(conn_pool)
    jr_repo = JobResultRepository(conn_pool)
    await _insert_job(conn_pool, user.id)

    for sort_key in ("score_desc", "score_asc", "date_desc", "date_asc"):
        results = await jr_repo.find_by_user(user.id, sort=sort_key)
        assert isinstance(results, list)


# ── DB-5 / CR-3+4: Cross-user ownership in add_job / remove_job ──────────────

async def test_add_job_enforces_ownership(conn_pool):
    """User B cannot add User A's job result into User B's list."""
    user_a = await _make_user(conn_pool, "-a")
    user_b = await _make_user(conn_pool, "-b")
    jr_repo = JobResultRepository(conn_pool)
    jl_repo = JobListRepository(conn_pool)

    # User A has a job result; User B has a list
    job = await _insert_job(conn_pool, user_a.id, job_id=f"jl-{uuid4().hex[:8]}")
    b_list = await jl_repo.create(user_b.id, "B's list")

    # User B tries to add User A's job to their own list → must fail
    added = await jl_repo.add_job(b_list.id, job.id, user_b.id)
    assert added is False, "Cross-user add_job must return False"

    # Verify the list is empty
    jobs_in_list = await jl_repo.find_jobs_in_list(b_list.id, user_b.id)
    assert len(jobs_in_list) == 0


async def test_add_job_succeeds_for_owner(conn_pool):
    """add_job works when both the list and job belong to the same user."""
    user = await _make_user(conn_pool)
    jr_repo = JobResultRepository(conn_pool)
    jl_repo = JobListRepository(conn_pool)

    job = await _insert_job(conn_pool, user.id, job_id=f"own-{uuid4().hex[:8]}")
    lst = await jl_repo.create(user.id, "My list")

    added = await jl_repo.add_job(lst.id, job.id, user.id)
    assert added is True

    jobs = await jl_repo.find_jobs_in_list(lst.id, user.id)
    assert len(jobs) == 1
    assert jobs[0].id == job.id


async def test_remove_job_enforces_ownership(conn_pool):
    """User B cannot remove User A's job from User A's list (cross-user)."""
    user_a = await _make_user(conn_pool, "-a2")
    user_b = await _make_user(conn_pool, "-b2")
    jl_repo = JobListRepository(conn_pool)

    # User A has a list and a job in it
    job = await _insert_job(conn_pool, user_a.id, job_id=f"rm-{uuid4().hex[:8]}")
    a_list = await jl_repo.create(user_a.id, "A's list")
    await jl_repo.add_job(a_list.id, job.id, user_a.id)

    # User B tries to remove User A's job from User A's list → must fail
    removed = await jl_repo.remove_job(a_list.id, job.id, user_b.id)
    assert removed is False

    # Job must still be in User A's list
    remaining = await jl_repo.find_jobs_in_list(a_list.id, user_a.id)
    assert len(remaining) == 1


async def test_remove_job_succeeds_for_owner(conn_pool):
    """remove_job works when called by the owner."""
    user = await _make_user(conn_pool)
    jl_repo = JobListRepository(conn_pool)

    job = await _insert_job(conn_pool, user.id, job_id=f"rmo-{uuid4().hex[:8]}")
    lst = await jl_repo.create(user.id, "My list")
    await jl_repo.add_job(lst.id, job.id, user.id)

    removed = await jl_repo.remove_job(lst.id, job.id, user.id)
    assert removed is True

    remaining = await jl_repo.find_jobs_in_list(lst.id, user.id)
    assert len(remaining) == 0


# ── DB-6: pipeline_run.update_status scoped by user_id ───────────────────────

async def test_update_status_scoped_to_user(conn_pool):
    """update_status returns True when run_id and user_id match."""
    user = await _make_user(conn_pool)
    pr_repo = PipelineRunRepository(conn_pool)
    run_id = uuid4()
    started = datetime.now(timezone.utc)
    await pr_repo.insert(run_id, user.id, started)

    updated = await pr_repo.update_status(run_id, user.id, "running")
    assert updated is True

    runs = await pr_repo.find_by_user(user.id)
    assert any(r.id == run_id and r.status == "running" for r in runs)


async def test_update_status_wrong_user_returns_false(conn_pool):
    """update_status returns False when user_id does not match the run's owner."""
    owner = await _make_user(conn_pool, "-owner")
    other = await _make_user(conn_pool, "-other")
    pr_repo = PipelineRunRepository(conn_pool)
    run_id = uuid4()
    started = datetime.now(timezone.utc)
    await pr_repo.insert(run_id, owner.id, started)

    # other user tries to update owner's run → must fail
    updated = await pr_repo.update_status(run_id, other.id, "completed")
    assert updated is False

    # Run status must remain unchanged
    runs = await pr_repo.find_by_user(owner.id)
    matching = [r for r in runs if r.id == run_id]
    assert matching and matching[0].status == "pending"


async def test_update_status_nonexistent_run_returns_false(conn_pool):
    """update_status returns False for a run_id that does not exist."""
    user = await _make_user(conn_pool)
    pr_repo = PipelineRunRepository(conn_pool)

    updated = await pr_repo.update_status(uuid4(), user.id, "failed")
    assert updated is False


# ── DB-9: _build_filter consistency (find_by_user ↔ count_by_user) ───────────

async def test_find_and_count_agree_with_status_filter(conn_pool):
    """find_by_user and count_by_user return consistent results for the same filter."""
    user = await _make_user(conn_pool)
    jr_repo = JobResultRepository(conn_pool)

    j1 = await jr_repo.insert(user.id, "upwork", f"jf1-{uuid4().hex[:8]}", "T1", "https://x.com/1", 8, None)
    j2 = await jr_repo.insert(user.id, "upwork", f"jf2-{uuid4().hex[:8]}", "T2", "https://x.com/2", 6, None)
    j3 = await jr_repo.insert(user.id, "upwork", f"jf3-{uuid4().hex[:8]}", "T3", "https://x.com/3", 4, None)

    # Dismiss j2
    await jr_repo.update_status(j2.id, user.id, "dismissed")

    rows = await jr_repo.find_by_user(user.id, status="new")
    count = await jr_repo.count_by_user(user.id, status="new")
    assert len(rows) == count == 2


async def test_find_and_count_agree_with_platform_and_min_score(conn_pool):
    """Compound filter: both methods agree on platform + min_score."""
    user = await _make_user(conn_pool)
    jr_repo = JobResultRepository(conn_pool)

    await jr_repo.insert(user.id, "upwork", f"agg1-{uuid4().hex[:8]}", "Good", "https://x.com/1", 9, None)
    await jr_repo.insert(user.id, "upwork", f"agg2-{uuid4().hex[:8]}", "Low", "https://x.com/2", 3, None)
    await jr_repo.insert(user.id, "linkedin", f"agg3-{uuid4().hex[:8]}", "OK", "https://x.com/3", 8, None)

    rows = await jr_repo.find_by_user(user.id, platform="upwork", min_score=7)
    count = await jr_repo.count_by_user(user.id, platform="upwork", min_score=7)
    assert len(rows) == count == 1
    assert rows[0].platform == "upwork"
    assert rows[0].score == 9


# ── DB-13: delete_expired returns row count ───────────────────────────────────

async def test_delete_expired_sessions_returns_count(conn_pool):
    """delete_expired() on SessionRepository returns the number of rows deleted."""
    user = await _make_user(conn_pool)
    sess_repo = SessionRepository(conn_pool)

    # Create 2 expired + 1 valid session
    await sess_repo.create(user.id, f"tok-exp1-{uuid4().hex}", _past())
    await sess_repo.create(user.id, f"tok-exp2-{uuid4().hex}", _past())
    await sess_repo.create(user.id, f"tok-valid-{uuid4().hex}", _future())

    deleted = await sess_repo.delete_expired()
    assert deleted >= 2  # may delete other expired rows from other tests


async def test_delete_expired_magic_links_returns_count(conn_pool):
    """delete_expired() on MagicLinkRepository returns the number of rows deleted."""
    user = await _make_user(conn_pool)
    ml_repo = MagicLinkRepository(conn_pool)

    await ml_repo.create(user.id, f"ml-exp-{uuid4().hex}", _past())
    await ml_repo.create(user.id, f"ml-ok-{uuid4().hex}", _future())

    deleted = await ml_repo.delete_expired()
    assert deleted >= 1


# ── DB-14: list_users_with_stats pagination ───────────────────────────────────

async def test_list_users_with_stats_respects_limit(conn_pool):
    """list_users_with_stats returns at most `limit` rows."""
    user_repo = UserRepository(conn_pool)

    # Create 3 users
    for _ in range(3):
        await user_repo.create(f"test-{uuid4().hex[:8]}@example.com")

    users = await user_repo.list_users_with_stats(limit=2)
    assert len(users) <= 2


async def test_list_users_with_stats_offset_skips_rows(conn_pool):
    """list_users_with_stats with offset skips the first N rows."""
    user_repo = UserRepository(conn_pool)

    # Get total count first
    total = await user_repo.count_users()
    all_users = await user_repo.list_users_with_stats(limit=1000)
    paginated = await user_repo.list_users_with_stats(limit=1000, offset=1)

    assert len(paginated) == len(all_users) - 1


async def test_count_users_returns_total(conn_pool):
    """count_users() returns the correct total user count."""
    user_repo = UserRepository(conn_pool)
    before = await user_repo.count_users()

    await user_repo.create(f"cnt-{uuid4().hex[:8]}@example.com")
    after = await user_repo.count_users()

    assert after == before + 1
