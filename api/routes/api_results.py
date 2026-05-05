"""Results JSON API — view and manage job evaluation results."""

import asyncio
import base64
import binascii
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from api.csrf import require_csrf
from api.deps import get_current_user, get_job_list_repo, get_job_result_repo, get_llm_client, get_profile_repo, get_settings
from api.limiter import limiter
from api.schemas import (
    BulkDeleteByIdsRequest,
    BulkDeleteByIdsResponse,
    BulkDeleteRequest,
    BulkDeleteResponse,
    BulkDismissRequest,
    BulkDismissResponse,
    BulkEvaluationRequest,
    BulkEvaluationResponse,
    BulkStatusUpdateRequest,
    BulkStatusUpdateResponse,
    EvaluationResponse,
    JobResultResponse,
    OkResponse,
    PaginationMeta,
    ResultStatusUpdateRequest,
    ResultsListResponse,
)
from core.evaluator import Evaluator
from core.llm_client import LLMClient
from core.prompt_adapter import load_platform_context, profile_row_to_prompt_dict
from core.settings import Settings
from repositories.job_list import JobListRepository
from repositories.job_result import VALID_STATUSES, JobResultRepository, JobResultRow
from repositories.profile import ProfileRepository
from repositories.user import UserRow
from scrapers.base import NormalizedJob

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/results", tags=["api-results"])

_PAGE_SIZE = 50


def _encode_cursor(row: JobResultRow, sort: str) -> str:
    """Encode the last result row into an opaque pagination cursor."""
    data: dict = {"id": str(row.id)}
    if sort in ("score_desc", "score_asc"):
        data["score"] = row.score  # may be None
    else:
        data["created_at"] = row.created_at.isoformat()
    return base64.urlsafe_b64encode(json.dumps(data).encode()).decode()


def _decode_cursor(
    cursor_str: str,
    sort: str,
) -> tuple[UUID, int | None, datetime | None]:
    """Decode a cursor string into its components. Raises HTTP 422 on invalid input."""
    try:
        raw = base64.urlsafe_b64decode(cursor_str + "==").decode()
        data = json.loads(raw)
        cursor_id = UUID(data["id"])
    except (ValueError, KeyError, binascii.Error, json.JSONDecodeError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid cursor value",
        )
    cursor_score: int | None = None
    cursor_created_at: datetime | None = None
    if sort in ("score_desc", "score_asc"):
        raw_score = data.get("score")
        cursor_score = int(raw_score) if raw_score is not None else None
    else:
        cat_str = data.get("created_at")
        if cat_str:
            cursor_created_at = datetime.fromisoformat(cat_str)
    return cursor_id, cursor_score, cursor_created_at


@router.get("")
async def api_list_results(
    user: Annotated[UserRow, Depends(get_current_user)],
    repo: Annotated[JobResultRepository, Depends(get_job_result_repo)],
    status_filter: Annotated[str, Query(alias="status")] = "",
    min_score: Annotated[str, Query()] = "",
    platform: Annotated[str, Query()] = "",
    sort: Annotated[
        Literal["score_desc", "score_asc", "date_desc", "date_asc"],
        Query(),
    ] = "score_desc",
    cursor: Annotated[str | None, Query()] = None,
) -> ResultsListResponse:
    """Return paginated job results with optional filtering (cursor-based pagination)."""
    parsed_status: str | None = status_filter if status_filter else None
    parsed_min_score: int | None = int(min_score) if min_score else None
    parsed_platform: str | None = platform if platform else None

    if parsed_status is not None and parsed_status not in VALID_STATUSES:
        parsed_status = None

    cursor_id: UUID | None = None
    cursor_score: int | None = None
    cursor_created_at: datetime | None = None
    if cursor is not None:
        cursor_id, cursor_score, cursor_created_at = _decode_cursor(cursor, sort)

    results = await repo.find_by_user(
        user_id=user.id,
        status=parsed_status,
        min_score=parsed_min_score,
        platform=parsed_platform,
        sort=sort,
        limit=_PAGE_SIZE,
        cursor_id=cursor_id,
        cursor_score=cursor_score,
        cursor_created_at=cursor_created_at,
    )
    total = await repo.count_by_user(
        user_id=user.id,
        status=parsed_status,
        min_score=parsed_min_score,
        platform=parsed_platform,
    )

    next_cursor: str | None = None
    if len(results) == _PAGE_SIZE:
        next_cursor = _encode_cursor(results[-1], sort)

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
            limit=_PAGE_SIZE,
        ),
        next_cursor=next_cursor,
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


@router.delete("/{result_id}", status_code=status.HTTP_204_NO_CONTENT)
async def api_delete_result(
    result_id: UUID,
    user: Annotated[UserRow, Depends(get_current_user)],
    repo: Annotated[JobResultRepository, Depends(get_job_result_repo)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> None:
    """Hard-delete a job result owned by the current user."""
    deleted = await repo.delete_by_id(result_id, user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found",
        )


@router.post("/bulk-dismiss")
@limiter.limit("60/minute")
async def api_bulk_dismiss_results(
    request: Request,
    body: BulkDismissRequest,
    user: Annotated[UserRow, Depends(get_current_user)],
    repo: Annotated[JobResultRepository, Depends(get_job_result_repo)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> BulkDismissResponse:
    """Bulk-dismiss job results matching the given filters."""
    if body.status is not None and body.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status filter '{body.status}'. Must be one of: {sorted(VALID_STATUSES)}",
        )

    older_than: datetime | None = None
    if body.older_than_days is not None:
        older_than = datetime.now(timezone.utc) - timedelta(days=body.older_than_days)

    dismissed_count = await repo.bulk_update_status(
        user_id=user.id,
        new_status="dismissed",
        current_status=body.status,
        platform=body.platform,
        min_score=body.min_score,
        max_score=body.max_score,
        older_than=older_than,
    )
    return BulkDismissResponse(dismissed_count=dismissed_count)


@router.post("/bulk-delete")
@limiter.limit("60/minute")
async def api_bulk_delete_results(
    request: Request,
    body: BulkDeleteRequest,
    user: Annotated[UserRow, Depends(get_current_user)],
    repo: Annotated[JobResultRepository, Depends(get_job_result_repo)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> BulkDeleteResponse:
    """Hard-delete all job results matching the given filters for the current user."""
    if body.status is not None and body.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status filter '{body.status}'. Must be one of: {sorted(VALID_STATUSES)}",
        )

    older_than: datetime | None = None
    if body.older_than_days is not None:
        older_than = datetime.now(timezone.utc) - timedelta(days=body.older_than_days)

    deleted_count = await repo.bulk_delete(
        user_id=user.id,
        current_status=body.status,
        platform=body.platform,
        min_score=body.min_score,
        max_score=body.max_score,
        older_than=older_than,
    )
    return BulkDeleteResponse(deleted_count=deleted_count)


@router.post("/bulk-status")
@limiter.limit("60/minute")
async def api_bulk_status_results(
    request: Request,
    body: BulkStatusUpdateRequest,
    user: Annotated[UserRow, Depends(get_current_user)],
    repo: Annotated[JobResultRepository, Depends(get_job_result_repo)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> BulkStatusUpdateResponse:
    """Update status for an explicit list of job result IDs for the current user."""
    if body.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status '{body.status}'. Must be one of: {sorted(VALID_STATUSES)}",
        )
    if not body.ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ids must not be empty",
        )
    updated = await repo.update_status_many(user.id, body.ids, body.status)
    return BulkStatusUpdateResponse(updated=updated)


@router.post("/bulk-delete-ids")
@limiter.limit("60/minute")
async def api_bulk_delete_results_by_ids(
    request: Request,
    body: BulkDeleteByIdsRequest,
    user: Annotated[UserRow, Depends(get_current_user)],
    repo: Annotated[JobResultRepository, Depends(get_job_result_repo)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> BulkDeleteByIdsResponse:
    """Hard-delete job results by explicit ID list for the current user."""
    deleted = await repo.delete_many(user.id, body.ids)
    return BulkDeleteByIdsResponse(deleted=deleted)


class JobResultListsResponse(OkResponse):
    list_ids: list[str]


@router.get("/{result_id}/lists")
async def api_get_result_lists(
    result_id: UUID,
    user: Annotated[UserRow, Depends(get_current_user)],
    list_repo: Annotated[JobListRepository, Depends(get_job_list_repo)],
) -> JobResultListsResponse:
    """Return the list IDs that contain this job result for the current user."""
    list_ids = await list_repo.get_list_ids_for_job(result_id, user.id)
    return JobResultListsResponse(list_ids=[str(lid) for lid in list_ids])


@router.post("/{result_id}/evaluate")
@limiter.limit("30/minute")
async def api_evaluate_result(
    request: Request,
    result_id: UUID,
    user: Annotated[UserRow, Depends(get_current_user)],
    repo: Annotated[JobResultRepository, Depends(get_job_result_repo)],
    profile_repo: Annotated[ProfileRepository, Depends(get_profile_repo)],
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
    settings: Annotated[Settings, Depends(get_settings)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> EvaluationResponse:
    """Evaluate a single job by its result ID.

    Runs Pass 2 (full evaluation) for a job that already has a score from Pass 1.
    Returns the updated job result with evaluation data.
    """
    # Fetch the job result and verify ownership
    result = await repo.find_by_id_and_user(result_id, user.id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found",
        )

    # Verify the job hasn't been evaluated yet
    if result.evaluation is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job already evaluated",
        )

    # Verify the job has a score
    if result.score is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Job has no score from Pass 1 evaluation",
        )

    # Load user profile and platform context
    profile = await profile_repo.find_by_user_id(user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="User profile not found",
        )

    try:
        platform_context = load_platform_context(result.platform)
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No platform context for '{result.platform}'",
        )

    # Reconstruct NormalizedJob from stored data
    # Note: We need minimal job data for evaluation
    job = NormalizedJob(
        id=result.job_id,
        title=result.title,
        description="",  # Description not stored in job_results
        url=result.url,
        platform=result.platform,
    )

    # Create evaluator and run Pass 2
    prompt_dict = profile_row_to_prompt_dict(profile)
    evaluator = Evaluator(prompt_dict, settings, llm_client=llm_client)

    try:
        eval_result = await evaluator.evaluate_full(job, platform_context, result.score)
    except Exception as exc:
        logger.error(
            "Evaluation failed for result_id=%s: %s",
            result_id,
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evaluation failed: {type(exc).__name__}",
        )

    # Check if evaluation was skipped due to low score
    if eval_result.evaluation is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Job score ({result.score}) is below evaluation threshold",
        )

    # Update the job result with evaluation data
    updated = await repo.update_evaluation(result_id, user.id, eval_result.raw)
    if updated is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Result not found after update",
        )

    return EvaluationResponse(
        result=JobResultResponse(
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
    )


@router.post("/evaluate-bulk")
@limiter.limit("10/minute")
async def api_evaluate_bulk(
    request: Request,
    body: BulkEvaluationRequest,
    user: Annotated[UserRow, Depends(get_current_user)],
    repo: Annotated[JobResultRepository, Depends(get_job_result_repo)],
    profile_repo: Annotated[ProfileRepository, Depends(get_profile_repo)],
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
    settings: Annotated[Settings, Depends(get_settings)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> BulkEvaluationResponse:
    """Evaluate multiple jobs in bulk.

    Processes unevaluated jobs with concurrency limit.
    Returns a summary response with counts.
    """
    # Determine which job result IDs to evaluate
    if body.result_ids is not None:
        # Use explicit IDs
        result_ids = body.result_ids
    elif body.filter is not None:
        # Use filter-based query
        platform = body.filter.get("platform")
        min_score = body.filter.get("min_score")
        status_filter = body.filter.get("status")

        # Fetch unevaluated jobs matching the filter
        unevaluated = await repo.find_unevaluated_by_user(
            user_id=user.id,
            platform=platform,
            min_score=min_score,
            status=status_filter,
        )
        result_ids = [r.id for r in unevaluated]
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Either result_ids or filter must be provided",
        )

    if not result_ids:
        return BulkEvaluationResponse(
            total=0,
            evaluated=0,
            skipped_low_score=0,
            failed=0,
            updated_ids=[],
        )

    # Load user profile
    profile = await profile_repo.find_by_user_id(user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="User profile not found",
        )

    # Create evaluator
    prompt_dict = profile_row_to_prompt_dict(profile)
    evaluator = Evaluator(prompt_dict, settings, llm_client=llm_client)

    # Process jobs with concurrency limit
    semaphore = asyncio.Semaphore(settings.evaluation_concurrency)
    evaluated = 0
    skipped_low_score = 0
    failed = 0
    updated_ids: list[UUID] = []

    async def evaluate_one(result_id: UUID) -> None:
        nonlocal evaluated, skipped_low_score, failed

        async with semaphore:
            # Fetch the job result
            result = await repo.find_by_id_and_user(result_id, user.id)
            if result is None:
                failed += 1
                return

            # Skip if already evaluated
            if result.evaluation is not None:
                return

            # Skip if no score
            if result.score is None:
                failed += 1
                return

            # Load platform context
            try:
                platform_context = load_platform_context(result.platform)
            except FileNotFoundError:
                failed += 1
                return

            # Reconstruct NormalizedJob
            job = NormalizedJob(
                id=result.job_id,
                title=result.title,
                description="",
                url=result.url,
                platform=result.platform,
            )

            # Run evaluation
            try:
                eval_result = await evaluator.evaluate_full(job, platform_context, result.score)
            except Exception as exc:
                logger.error(
                    "Bulk evaluation failed for result_id=%s: %s",
                    result_id,
                    exc,
                    exc_info=True,
                )
                failed += 1
                return

            # Check if below threshold
            if eval_result.evaluation is None:
                skipped_low_score += 1
                return

            # Update the job result
            updated = await repo.update_evaluation(result_id, user.id, eval_result.raw)
            if updated is not None:
                evaluated += 1
                updated_ids.append(result_id)
            else:
                failed += 1

    # Run evaluations concurrently
    await asyncio.gather(*[evaluate_one(rid) for rid in result_ids])

    return BulkEvaluationResponse(
        total=len(result_ids),
        evaluated=evaluated,
        skipped_low_score=skipped_low_score,
        failed=failed,
        updated_ids=updated_ids,
    )
