"""Results JSON API — view and manage job evaluation results."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.csrf import require_csrf
from api.deps import get_current_user, get_job_result_repo
from api.schemas import (
    JobResultResponse,
    PaginationMeta,
    ResultStatusUpdateRequest,
    ResultsListResponse,
)
from repositories.job_result import VALID_STATUSES, JobResultRepository
from repositories.user import UserRow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/results", tags=["api-results"])

_PAGE_SIZE = 50


@router.get("")
async def api_list_results(
    user: Annotated[UserRow, Depends(get_current_user)],
    repo: Annotated[JobResultRepository, Depends(get_job_result_repo)],
    status_filter: Annotated[str, Query(alias="status")] = "",
    min_score: Annotated[str, Query()] = "",
    platform: Annotated[str, Query()] = "",
    page: Annotated[int, Query(ge=1)] = 1,
) -> ResultsListResponse:
    """Return paginated job results with optional filtering."""
    parsed_status: str | None = status_filter if status_filter else None
    parsed_min_score: int | None = int(min_score) if min_score else None
    parsed_platform: str | None = platform if platform else None

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

    return ResultsListResponse(
        results=[
            JobResultResponse(
                id=r.id,
                platform=r.platform,
                job_id=r.job_id,
                title=r.title,
                url=r.url,
                score=r.score,
                evaluation=r.evaluation,
                status=r.status,
                created_at=r.created_at,
            )
            for r in results
        ],
        pagination=PaginationMeta(
            total=total,
            page=page,
            limit=_PAGE_SIZE,
            total_pages=total_pages,
        ),
    )


@router.patch("/{result_id}")
async def api_update_result_status(
    result_id: UUID,
    body: ResultStatusUpdateRequest,
    user: Annotated[UserRow, Depends(get_current_user)],
    repo: Annotated[JobResultRepository, Depends(get_job_result_repo)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> JobResultResponse:
    """Update the status of a job result. Returns the updated result."""
    if body.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status '{body.status}'. Must be one of: {sorted(VALID_STATUSES)}",
        )

    updated = await repo.update_status(result_id, user.id, body.status)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found",
        )

    return JobResultResponse(
        id=updated.id,
        platform=updated.platform,
        job_id=updated.job_id,
        title=updated.title,
        url=updated.url,
        score=updated.score,
        evaluation=updated.evaluation,
        status=updated.status,
        created_at=updated.created_at,
    )
