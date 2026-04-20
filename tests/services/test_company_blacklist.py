"""Unit tests for services.company_blacklist.CompanyBlacklistService."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from repositories.company_blacklist import CompanyBlacklistEntry
from services.company_blacklist import CompanyBlacklistError, CompanyBlacklistService

from datetime import datetime, timezone


def _make_entry(name: str = "Acme Corp") -> CompanyBlacklistEntry:
    return CompanyBlacklistEntry(
        id=uuid4(),
        user_id=uuid4(),
        name=name,
        name_lower=name.lower(),
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def repo():
    r = AsyncMock()
    r.find_by_user_id.return_value = []
    r.insert.return_value = _make_entry()
    r.delete.return_value = True
    return r


@pytest.fixture
def svc(repo):
    return CompanyBlacklistService(repo)


@pytest.mark.asyncio
async def test_add_valid_name_returns_entry(svc, repo):
    user_id = uuid4()
    entry = await svc.add(user_id, "Google")
    assert entry.name == "Acme Corp"  # from mock
    repo.insert.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_strips_whitespace_before_validation(svc, repo):
    user_id = uuid4()
    await svc.add(user_id, "  Google  ")
    args = repo.insert.call_args
    assert args[0][1] == "Google"


@pytest.mark.asyncio
async def test_add_empty_string_raises(svc):
    with pytest.raises(CompanyBlacklistError, match="cannot be empty"):
        await svc.add(uuid4(), "   ")


@pytest.mark.asyncio
async def test_add_name_too_short_raises(svc):
    with pytest.raises(CompanyBlacklistError, match="at least 3 characters"):
        await svc.add(uuid4(), "Ab")


@pytest.mark.asyncio
async def test_add_name_too_long_raises(svc):
    with pytest.raises(CompanyBlacklistError, match="at most 200 characters"):
        await svc.add(uuid4(), "A" * 201)


@pytest.mark.asyncio
async def test_add_duplicate_raises(svc, repo):
    repo.insert.return_value = None  # ON CONFLICT DO NOTHING
    with pytest.raises(CompanyBlacklistError, match="already blacklisted"):
        await svc.add(uuid4(), "Google")


@pytest.mark.asyncio
async def test_add_at_500_cap_raises(svc, repo):
    repo.find_by_user_id.return_value = [_make_entry() for _ in range(500)]
    with pytest.raises(CompanyBlacklistError, match="limit reached"):
        await svc.add(uuid4(), "Google")


@pytest.mark.asyncio
async def test_remove_valid_entry_succeeds(svc, repo):
    await svc.remove(uuid4(), uuid4())
    repo.delete.assert_awaited_once()


@pytest.mark.asyncio
async def test_remove_unknown_entry_raises(svc, repo):
    repo.delete.return_value = False
    with pytest.raises(CompanyBlacklistError, match="not found"):
        await svc.remove(uuid4(), uuid4())
