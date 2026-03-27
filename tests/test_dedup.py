"""Tests for core.dedup.DedupStore."""

import pytest

from core.dedup import DedupStore


@pytest.fixture
def store() -> DedupStore:
    """Fresh in-memory DedupStore for each test. No files written to disk."""
    db = DedupStore(":memory:")
    yield db
    db.close()


def test_unseen_job_returns_false(store: DedupStore) -> None:
    assert store.is_seen("job-1", "upwork") is False


def test_mark_then_is_seen(store: DedupStore) -> None:
    store.mark_seen("job-1", "upwork")
    assert store.is_seen("job-1", "upwork") is True


def test_platform_isolation(store: DedupStore) -> None:
    store.mark_seen("job-1", "upwork")
    assert store.is_seen("job-1", "linkedin") is False


def test_mark_seen_idempotent(store: DedupStore) -> None:
    store.mark_seen("job-1", "upwork")
    store.mark_seen("job-1", "upwork")  # should not raise
    assert store.is_seen("job-1", "upwork") is True


def test_multiple_jobs_tracked_independently(store: DedupStore) -> None:
    store.mark_seen("job-1", "upwork")
    assert store.is_seen("job-1", "upwork") is True
    assert store.is_seen("job-2", "upwork") is False
    store.mark_seen("job-2", "upwork")
    assert store.is_seen("job-2", "upwork") is True


def test_close_does_not_raise(store: DedupStore) -> None:
    store.close()  # called again by fixture teardown — should not raise
