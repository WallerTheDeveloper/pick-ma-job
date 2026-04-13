"""Platforms JSON API — list registered scrapers and user config status."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from api.deps import get_current_user, get_search_config_service
from api.schemas import PlatformInfo, PlatformsListResponse
from repositories.user import UserRow
from scrapers.registry import list_platforms
from services.search_config import SearchConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/platforms", tags=["api-platforms"])


@router.get("")
async def api_list_platforms(
    user: Annotated[UserRow, Depends(get_current_user)],
    search_config_svc: Annotated[SearchConfigService, Depends(get_search_config_service)],
) -> PlatformsListResponse:
    """Return all registered platform slugs with a flag for whether the user has a config.

    The list is driven entirely by the scraper registry — no hardcoded slugs here.
    """
    all_configs = await search_config_svc.get_all(user.id)
    configured_platforms: set[str] = {c.platform for c in all_configs}

    platforms = [
        PlatformInfo(slug=slug, has_config=slug in configured_platforms)
        for slug in list_platforms()
    ]

    logger.debug(
        "Platforms listed for user_id=%s: %s",
        user.id,
        [p.slug for p in platforms],
    )
    return PlatformsListResponse(platforms=platforms)
