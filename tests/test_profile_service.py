"""Unit tests for ProfileService — ProfileRepository is mocked."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from repositories.profile import ProfileRow
from services.profile import ProfileData, ProfileError, ProfileService, empty_profile_data


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_profile_row(**overrides) -> ProfileRow:
    defaults = dict(
        id=uuid4(),
        user_id=uuid4(),
        role="Unity Developer",
        experience="mid-level",
        rate="€20/hr",
        primary_skills=["Unity", "C#"],
        secondary_skills=["Rust"],
        tertiary_skills=[],
        not_a_good_fit=["Pure frontend"],
        background=["2 years at ZAUBAR"],
        notable_projects=[{"name": "VR App", "description": "Unity XR project"}],
        languages=["English"],
        rubric={"scoring": {}},
        cv_customize_threshold=7,
        exclude_keywords=[],
        updated_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return ProfileRow(**defaults)


def _make_service(profile_repo=None) -> ProfileService:
    return ProfileService(profile_repo=profile_repo or MagicMock())


def _valid_data(**overrides) -> ProfileData:
    defaults = dict(
        role="Unity Developer",
        experience="mid-level",
        rate="€20/hr",
        primary_skills=["Unity", "C#"],
        secondary_skills=["Rust"],
        tertiary_skills=[],
        not_a_good_fit=["Pure frontend"],
        background=["2 years at ZAUBAR"],
        notable_projects=[{"name": "VR App", "description": "Unity XR project"}],
        languages=["English"],
        rubric={},
        exclude_keywords=[],
    )
    defaults.update(overrides)
    return ProfileData(**defaults)


# ── get_or_default ────────────────────────────────────────────────────────────

async def test_get_or_default_returns_row_when_found():
    repo = MagicMock()
    user_id = uuid4()
    row = _make_profile_row(user_id=user_id)
    repo.find_by_user_id = AsyncMock(return_value=row)

    svc = _make_service(repo)
    result = await svc.get_or_default(user_id)

    assert result is row
    repo.find_by_user_id.assert_awaited_once_with(user_id)


async def test_get_or_default_returns_none_when_missing():
    repo = MagicMock()
    repo.find_by_user_id = AsyncMock(return_value=None)

    svc = _make_service(repo)
    result = await svc.get_or_default(uuid4())

    assert result is None


# ── update ────────────────────────────────────────────────────────────────────

async def test_update_calls_upsert_with_correct_data():
    repo = MagicMock()
    user_id = uuid4()
    row = _make_profile_row(user_id=user_id)
    repo.upsert = AsyncMock(return_value=row)

    svc = _make_service(repo)
    data = _valid_data()
    result = await svc.update(user_id, data)

    assert result is row
    repo.upsert.assert_awaited_once()
    call_kwargs = repo.upsert.call_args.kwargs
    assert call_kwargs["user_id"] == user_id
    assert call_kwargs["primary_skills"] == ["Unity", "C#"]
    assert call_kwargs["secondary_skills"] == ["Rust"]


async def test_update_raises_when_no_primary_skills():
    svc = _make_service()
    data = _valid_data(primary_skills=[])

    with pytest.raises(ProfileError, match="primary skill"):
        await svc.update(uuid4(), data)


async def test_update_raises_when_notable_project_missing_name():
    svc = _make_service()
    data = _valid_data(notable_projects=[{"description": "no name here"}])

    with pytest.raises(ProfileError, match="name"):
        await svc.update(uuid4(), data)


async def test_update_raises_when_notable_project_missing_description():
    svc = _make_service()
    data = _valid_data(notable_projects=[{"name": "Some Project"}])

    with pytest.raises(ProfileError, match="description"):
        await svc.update(uuid4(), data)


async def test_update_raises_when_notable_project_not_a_dict():
    svc = _make_service()
    data = _valid_data(notable_projects=["not a dict"])

    with pytest.raises(ProfileError, match="object"):
        await svc.update(uuid4(), data)


async def test_update_empty_optional_lists_are_accepted():
    """Secondary/tertiary/languages etc. are all optional — no primary skills needed to fail."""
    repo = MagicMock()
    user_id = uuid4()
    row = _make_profile_row(user_id=user_id)
    repo.upsert = AsyncMock(return_value=row)

    svc = _make_service(repo)
    data = _valid_data(secondary_skills=[], tertiary_skills=[], languages=[], not_a_good_fit=[])
    result = await svc.update(user_id, data)

    assert result is row


# ── empty_profile_data ────────────────────────────────────────────────────────

def test_empty_profile_data_has_empty_lists():
    data = empty_profile_data()
    assert data.primary_skills == []
    assert data.secondary_skills == []
    assert data.tertiary_skills == []
    assert data.not_a_good_fit == []
    assert data.background == []
    assert data.notable_projects == []
    assert data.languages == []
    assert data.rubric == {}
    assert data.exclude_keywords == []
