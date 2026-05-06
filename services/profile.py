"""ProfileService — user profile business logic."""

import logging
from dataclasses import dataclass, field
from uuid import UUID

from repositories.profile import ProfileRepository, ProfileRow

logger = logging.getLogger(__name__)


class ProfileError(Exception):
    """Raised for expected profile validation failures."""


@dataclass(frozen=True)
class ProfileData:
    """Validated profile payload used for create/update operations."""

    role: str | None
    experience: str | None
    rate: str | None
    primary_skills: list[str]
    secondary_skills: list[str]
    tertiary_skills: list[str]
    not_a_good_fit: list[str]
    background: list[str]
    notable_projects: list[dict]
    languages: list[str]
    rubric: dict
    cv_customize_threshold: int = 7
    exclude_keywords: list[str] = field(default_factory=list)


class ProfileService:
    def __init__(self, profile_repo: ProfileRepository) -> None:
        self._profile_repo = profile_repo

    async def get_or_default(self, user_id: UUID) -> ProfileRow | None:
        """Return the user's profile row, or None if they haven't set one up yet."""
        return await self._profile_repo.find_by_user_id(user_id)

    async def update(self, user_id: UUID, data: ProfileData) -> ProfileRow:
        """Validate and upsert the user's profile. Raises ProfileError on invalid input."""
        _validate(data)
        profile = await self._profile_repo.upsert(
            user_id=user_id,
            role=data.role or None,
            experience=data.experience or None,
            rate=data.rate or None,
            primary_skills=data.primary_skills,
            secondary_skills=data.secondary_skills,
            tertiary_skills=data.tertiary_skills,
            not_a_good_fit=data.not_a_good_fit,
            background=data.background,
            notable_projects=data.notable_projects,
            languages=data.languages,
            rubric=data.rubric,
            cv_customize_threshold=data.cv_customize_threshold,
            exclude_keywords=data.exclude_keywords,
        )
        logger.info("Profile updated for user_id=%s", user_id)
        return profile


def _validate(data: ProfileData) -> None:
    """Raise ProfileError if the profile data fails basic validation."""
    if not data.primary_skills:
        raise ProfileError("At least one primary skill is required.")

    for project in data.notable_projects:
        if not isinstance(project, dict):
            raise ProfileError("Each notable project must be an object with 'name' and 'description'.")
        if "name" not in project or "description" not in project:
            raise ProfileError("Each notable project must have a 'name' and 'description'.")


def empty_profile_data() -> ProfileData:
    """Return a blank ProfileData instance for new users."""
    return ProfileData(
        role=None,
        experience=None,
        rate=None,
        primary_skills=[],
        secondary_skills=[],
        tertiary_skills=[],
        not_a_good_fit=[],
        background=[],
        notable_projects=[],
        languages=[],
        rubric={},
        cv_customize_threshold=7,
        exclude_keywords=[],
    )
