"""Results routes — view and manage job evaluation results."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse

from api.csrf import require_csrf
from api.deps import get_current_user, get_current_user_optional, get_job_result_repo
from repositories.job_result import JobResultRepository, VALID_STATUSES
from repositories.user import UserRow

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
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    min_score: Annotated[int | None, Query()] = None,
    platform: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
) -> HTMLResponse | RedirectResponse:
    """Render the results dashboard with filtering and pagination."""
    if user is None:
        return RedirectResponse(url="/auth/login", status_code=302)

    # Validate status filter
    if status_filter is not None and status_filter not in VALID_STATUSES:
        status_filter = None

    offset = (page - 1) * _PAGE_SIZE

    results = await repo.find_by_user(
        user_id=user.id,
        status=status_filter,
        min_score=min_score,
        platform=platform,
        limit=_PAGE_SIZE,
        offset=offset,
    )
    total = await repo.count_by_user(
        user_id=user.id,
        status=status_filter,
        min_score=min_score,
        platform=platform,
    )

    total_pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)

    filters = {
        "status": status_filter,
        "min_score": min_score,
        "platform": platform,
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
