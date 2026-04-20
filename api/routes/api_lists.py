"""Job Lists JSON API — create, manage, and view named job collections."""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status

from api.csrf import require_csrf
from api.deps import get_current_user, get_job_list_repo
from api.schemas import (
    AddJobToListRequest,
    JobListCreateRequest,
    JobListJobsResponse,
    JobListRenameRequest,
    JobListResponse,
    JobListsResponse,
    JobResultResponse,
    OkResponse,
)
from repositories.job_list import JobListRepository, _VALID_LIST_SORTS
from repositories.job_result import VALID_STATUSES
from repositories.user import UserRow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/lists", tags=["api-lists"])


@router.get("")
async def api_list_job_lists(
    user: Annotated[UserRow, Depends(get_current_user)],
    repo: Annotated[JobListRepository, Depends(get_job_list_repo)],
) -> JobListsResponse:
    """Return all job lists for the authenticated user."""
    lists = await repo.find_by_user(user.id)
    return JobListsResponse(
        lists=[JobListResponse(id=jl.id, name=jl.name, created_at=jl.created_at) for jl in lists]
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def api_create_job_list(
    body: JobListCreateRequest,
    user: Annotated[UserRow, Depends(get_current_user)],
    repo: Annotated[JobListRepository, Depends(get_job_list_repo)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> JobListResponse:
    """Create a new named job list."""
    name = body.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="List name cannot be empty",
        )
    jl = await repo.create(user.id, name)
    return JobListResponse(id=jl.id, name=jl.name, created_at=jl.created_at)


@router.patch("/{list_id}")
async def api_rename_job_list(
    list_id: UUID,
    body: JobListRenameRequest,
    user: Annotated[UserRow, Depends(get_current_user)],
    repo: Annotated[JobListRepository, Depends(get_job_list_repo)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> JobListResponse:
    """Rename a job list."""
    name = body.name.strip()
    if not name:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="List name cannot be empty",
        )
    updated = await repo.rename(list_id, user.id, name)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="List not found")
    return JobListResponse(id=updated.id, name=updated.name, created_at=updated.created_at)


@router.delete("/{list_id}")
async def api_delete_job_list(
    list_id: UUID,
    user: Annotated[UserRow, Depends(get_current_user)],
    repo: Annotated[JobListRepository, Depends(get_job_list_repo)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> OkResponse:
    """Delete a job list and its items. Does not delete the underlying job results."""
    deleted = await repo.delete(list_id, user.id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="List not found")
    return OkResponse()


@router.get("/{list_id}/jobs")
async def api_get_jobs_in_list(
    list_id: UUID,
    user: Annotated[UserRow, Depends(get_current_user)],
    repo: Annotated[JobListRepository, Depends(get_job_list_repo)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    min_score: Annotated[int | None, Query(ge=1, le=10)] = None,
    platform: Annotated[str | None, Query()] = None,
    sort: Annotated[str, Query()] = "score_desc",
) -> JobListJobsResponse:
    """Return job results in a specific list, with optional filtering."""
    if status_filter is not None and status_filter not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status: {status_filter!r}",
        )
    if sort not in _VALID_LIST_SORTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid sort: {sort!r}",
        )
    jl = await repo.find_by_id(list_id, user.id)
    if jl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="List not found")
    jobs = await repo.find_jobs_in_list(
        list_id,
        user.id,
        status=status_filter,
        min_score=min_score,
        platform=platform,
        sort=sort,
    )
    return JobListJobsResponse(
        jobs=[
            JobResultResponse(
                id=j.id,
                platform=j.platform,
                job_id=j.job_id,
                title=j.title,
                url=j.url,
                score=j.score,
                evaluation=j.evaluation,
                status=j.status,
                created_at=j.created_at,
            )
            for j in jobs
        ]
    )


@router.post("/{list_id}/jobs", status_code=status.HTTP_201_CREATED)
async def api_add_job_to_list(
    list_id: UUID,
    body: AddJobToListRequest,
    user: Annotated[UserRow, Depends(get_current_user)],
    repo: Annotated[JobListRepository, Depends(get_job_list_repo)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> OkResponse:
    """Add a job result to a list."""
    jl = await repo.find_by_id(list_id, user.id)
    if jl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="List not found")
    added = await repo.add_job(list_id, body.job_result_id, user.id)
    if not added:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job result not found")
    return OkResponse()


@router.delete("/{list_id}/jobs/{job_result_id}")
async def api_remove_job_from_list(
    list_id: UUID,
    job_result_id: UUID,
    user: Annotated[UserRow, Depends(get_current_user)],
    repo: Annotated[JobListRepository, Depends(get_job_list_repo)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> OkResponse:
    """Remove a job result from a list."""
    jl = await repo.find_by_id(list_id, user.id)
    if jl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="List not found")
    removed = await repo.remove_job(list_id, job_result_id, user.id)
    if not removed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not in list")
    return OkResponse()
