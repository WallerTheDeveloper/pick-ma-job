"""Results routes — view and manage job evaluation results."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from api.csrf import require_csrf
from api.deps import (
    get_current_user,
    get_current_user_optional,
    get_job_result_repo,
    get_profile_service,
    get_search_config_service,
)
from repositories.job_result import JobResultRepository, VALID_STATUSES
from repositories.user import UserRow
from services.profile import ProfileService
from services.search_config import SearchConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/results", tags=["results"])

_VALID_PATCH_STATUSES = frozenset({"new", "applied", "dismissed"})

_PAGE_SIZE = 50


def _templates(request: Request):
    return request.app.state.templates


@router.get("", response_class=HTMLResponse, response_model=None)
async def results_page(
    request: Request,
    user: Annotated[UserRow | None, Depends(get_current_user_optional)],
    repo: Annotated[JobResultRepository, Depends(get_job_result_repo)],
    profile_svc: Annotated[ProfileService, Depends(get_profile_service)],
    search_config_svc: Annotated[SearchConfigService, Depends(get_search_config_service)],
    status_filter: Annotated[str, Query(alias="status")] = "",
    min_score: Annotated[str, Query()] = "",
    platform: Annotated[str, Query()] = "",
    page: Annotated[int, Query(ge=1)] = 1,
) -> HTMLResponse | RedirectResponse:
    """Render the results dashboard with filtering and pagination."""
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    # Normalize empty query params to None
    parsed_status: str | None = status_filter if status_filter else None
    parsed_min_score: int | None = int(min_score) if min_score else None
    parsed_platform: str | None = platform if platform else None

    # Validate status filter
    if parsed_status is not None and parsed_status not in VALID_STATUSES:
        parsed_status = None

    offset = (page - 1) * _PAGE_SIZE

    results = await repo.find_by_user(
        user_id=user.id,
        status=parsed_status,
        min_score=parsed_min_score,
        platform=parsed_platform,
        limit=_PAGE_SIZE,
        offset=offset,
    )
    total = await repo.count_by_user(
        user_id=user.id,
        status=parsed_status,
        min_score=parsed_min_score,
        platform=parsed_platform,
    )

    total_pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)

    # Check setup state for empty-state banners
    has_profile = await profile_svc.get_or_default(user.id) is not None
    has_search_config = len(await search_config_svc.get_all(user.id)) > 0

    filters = {
        "status": parsed_status,
        "min_score": parsed_min_score,
        "platform": parsed_platform,
    }

    return _templates(request).TemplateResponse(
        request,
        "results.html",
        {
            "user": user,
            "results": results,
            "total": total,
            "page": page,
            "total_pages": total_pages,
            "filters": filters,
            "page_size": _PAGE_SIZE,
            "has_profile": has_profile,
            "has_search_config": has_search_config,
        },
    )


@router.patch("/{result_id}", response_class=HTMLResponse, response_model=None)
async def update_result_status(
    request: Request,
    result_id: UUID,
    user: Annotated[UserRow, Depends(get_current_user)],
    repo: Annotated[JobResultRepository, Depends(get_job_result_repo)],
    _csrf: Annotated[None, Depends(require_csrf)],
    status_value: Annotated[str, Form(alias="status")],
) -> HTMLResponse:
    """Update the status of a job result. Returns a re-rendered row partial for HTMX swap."""
    if status_value not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Invalid status '{status_value}'. Must be one of: {sorted(VALID_STATUSES)}",
        )

    updated = await repo.update_status(result_id, user.id, status_value)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found",
        )

    return _templates(request).TemplateResponse(
        request,
        "partials/result_row.html",
        {"r": updated},
    )
