"""Search config JSON API — manage per-user platform search configurations."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from api.csrf import require_csrf
from api.deps import get_current_user, get_search_config_service
from api.schemas import (
    OkResponse,
    SearchConfigCreateRequest,
    SearchConfigCreateResponse,
    SearchConfigResponse,
    SearchConfigsListResponse,
)
from repositories.search_config import SearchConfigRow
from repositories.user import UserRow
from services.search_config import SearchConfigData, SearchConfigError, SearchConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/search-configs", tags=["api-search-config"])


def _config_to_response(row: SearchConfigRow) -> SearchConfigResponse:
    return SearchConfigResponse(
        id=row.id,
        platform=row.platform,
        query=row.query,
        filters=row.filters,
        updated_at=row.updated_at,
    )


@router.get("")
async def api_list_search_configs(
    user: Annotated[UserRow, Depends(get_current_user)],
    svc: Annotated[SearchConfigService, Depends(get_search_config_service)],
) -> SearchConfigsListResponse:
    """Return all search configs for the authenticated user."""
    configs = await svc.get_all(user.id)
    return SearchConfigsListResponse(
        configs=[_config_to_response(c) for c in configs],
    )


@router.post("")
async def api_create_search_config(
    body: SearchConfigCreateRequest,
    user: Annotated[UserRow, Depends(get_current_user)],
    _csrf: Annotated[None, Depends(require_csrf)],
    svc: Annotated[SearchConfigService, Depends(get_search_config_service)],
) -> SearchConfigCreateResponse:
    """Create a new search config for the given platform."""
    data = SearchConfigData(
        platform=body.platform,
        query=body.query.strip() if body.query else None,
        filters=body.filters,
    )

    try:
        row = await svc.create(user.id, data)
    except SearchConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return SearchConfigCreateResponse(config=_config_to_response(row))


@router.delete("/{config_id}")
async def api_delete_search_config(
    config_id: UUID,
    user: Annotated[UserRow, Depends(get_current_user)],
    _csrf: Annotated[None, Depends(require_csrf)],
    svc: Annotated[SearchConfigService, Depends(get_search_config_service)],
) -> OkResponse:
    """Delete a search config by id."""
    deleted = await svc.delete(config_id, user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search config not found.")
    logger.info("Search config deleted id=%s by user_id=%s", config_id, user.id)
    return OkResponse()
