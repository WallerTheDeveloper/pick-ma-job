"""Profile JSON API — view and update the authenticated user's profile."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from api.csrf import require_csrf
from api.deps import get_current_user, get_profile_service
from api.schemas import ProfileGetResponse, ProfileResponse, ProfileSaveRequest, ProfileSaveResponse
from repositories.profile import ProfileRow
from repositories.user import UserRow
from services.profile import ProfileData, ProfileError, ProfileService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/profile", tags=["api-profile"])


def _profile_to_response(row: ProfileRow) -> ProfileResponse:
    return ProfileResponse(
        id=row.id,
        role=row.role,
        experience=row.experience,
        rate=row.rate,
        primary_skills=row.primary_skills,
        secondary_skills=row.secondary_skills,
        tertiary_skills=row.tertiary_skills,
        not_a_good_fit=row.not_a_good_fit,
        background=row.background,
        notable_projects=row.notable_projects,
        languages=row.languages,
        rubric=row.rubric,
        updated_at=row.updated_at,
    )


@router.get("")
async def api_get_profile(
    user: Annotated[UserRow, Depends(get_current_user)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
) -> ProfileGetResponse:
    """Return the user's profile, or null if not set up yet."""
    profile = await profile_service.get_or_default(user.id)
    return ProfileGetResponse(
        profile=_profile_to_response(profile) if profile else None,
    )


@router.post("")
async def api_save_profile(
    body: ProfileSaveRequest,
    user: Annotated[UserRow, Depends(get_current_user)],
    _csrf: Annotated[None, Depends(require_csrf)],
    profile_service: Annotated[ProfileService, Depends(get_profile_service)],
) -> ProfileSaveResponse:
    """Validate and upsert the user's profile. Returns the saved profile."""
    data = ProfileData(
        role=body.role.strip() if body.role else None,
        experience=body.experience.strip() if body.experience else None,
        rate=body.rate.strip() if body.rate else None,
        primary_skills=body.primary_skills,
        secondary_skills=body.secondary_skills,
        tertiary_skills=body.tertiary_skills,
        not_a_good_fit=body.not_a_good_fit,
        background=body.background,
        notable_projects=body.notable_projects,
        languages=body.languages,
        rubric=body.rubric,
    )

    try:
        profile = await profile_service.update(user.id, data)
    except ProfileError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return ProfileSaveResponse(profile=_profile_to_response(profile))
