"""Company blacklist JSON API — manage the authenticated user's company blacklist."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status

from api.csrf import require_csrf
from api.deps import get_company_blacklist_service, get_current_user
from api.limiter import limiter
from api.schemas import (
    CompanyBlacklistAddRequest,
    CompanyBlacklistAddResponse,
    CompanyBlacklistEntryResponse,
    CompanyBlacklistListResponse,
)
from repositories.user import UserRow
from services.company_blacklist import CompanyBlacklistError, CompanyBlacklistService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/company-blacklist", tags=["api-company-blacklist"])

_DUPLICATE_MSG = "Company already blacklisted"
_NOT_FOUND_MSG = "Entry not found"


def _entry_to_response(entry) -> CompanyBlacklistEntryResponse:
    return CompanyBlacklistEntryResponse(
        id=entry.id,
        name=entry.name,
        created_at=entry.created_at,
    )


@router.get("")
async def api_list_blacklist(
    user: Annotated[UserRow, Depends(get_current_user)],
    service: Annotated[CompanyBlacklistService, Depends(get_company_blacklist_service)],
) -> CompanyBlacklistListResponse:
    """Return all blacklisted companies for the authenticated user."""
    entries = await service.list(user.id)
    return CompanyBlacklistListResponse(entries=[_entry_to_response(e) for e in entries])


@router.post("", status_code=status.HTTP_201_CREATED)
@limiter.limit("60/minute")
async def api_add_blacklist_entry(
    request: Request,
    body: CompanyBlacklistAddRequest,
    user: Annotated[UserRow, Depends(get_current_user)],
    _csrf: Annotated[None, Depends(require_csrf)],
    service: Annotated[CompanyBlacklistService, Depends(get_company_blacklist_service)],
) -> CompanyBlacklistAddResponse:
    """Add a company to the user's blacklist. Returns 201 on success, 409 on duplicate."""
    try:
        entry = await service.add(user.id, body.name)
    except CompanyBlacklistError as exc:
        msg = str(exc)
        if msg == _DUPLICATE_MSG:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg)
    return CompanyBlacklistAddResponse(entry=_entry_to_response(entry))


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_remove_blacklist_entry(
    entry_id: UUID,
    user: Annotated[UserRow, Depends(get_current_user)],
    _csrf: Annotated[None, Depends(require_csrf)],
    service: Annotated[CompanyBlacklistService, Depends(get_company_blacklist_service)],
) -> None:
    """Remove a blacklist entry owned by the authenticated user. Returns 404 if not found."""
    try:
        await service.remove(user.id, entry_id)
    except CompanyBlacklistError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
