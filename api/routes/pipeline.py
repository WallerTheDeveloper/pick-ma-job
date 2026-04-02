"""Pipeline routes — trigger background evaluation runs and poll their status."""

import logging
from typing import Annotated
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from api.deps import (
    get_current_user,
    get_db_pool,
    get_profile_service,
    get_run_manager,
    get_search_config_service,
)
from repositories.user import UserRow
from services.profile import ProfileService
from services.run_manager import RunActiveError, RunManager
from services.search_config import SearchConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/run", tags=["pipeline"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def start_run(
    user: Annotated[UserRow, Depends(get_current_user)],
    run_manager: Annotated[RunManager, Depends(get_run_manager)],
    profile_svc: Annotated[ProfileService, Depends(get_profile_service)],
    search_config_svc: Annotated[SearchConfigService, Depends(get_search_config_service)],
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
    platform: Annotated[str | None, Query()] = None,
) -> JSONResponse:
    """Start a background pipeline run for the authenticated user.

    Validates that the user has a profile and at least one search config
    before enqueuing the run. Returns 202 immediately with a ``run_id``.
    Poll ``GET /run/{run_id}/status`` to track progress.

    Args:
        platform: Optional platform slug to restrict the run (e.g. ``upwork``).
                  If omitted, all configured platforms are run.
    """
    profile = await profile_svc.get_or_default(user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Profile not configured. Please set up your profile before running the pipeline.",
        )

    if platform is not None:
        config = await search_config_svc.get_by_platform(user.id, platform)
        if config is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No search config found for platform '{platform}'. Please configure it first.",
            )
    else:
        configs = await search_config_svc.get_all(user.id)
        if not configs:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No search configurations found. Please set up at least one search config first.",
            )

    try:
        run_id = run_manager.start_run(user.id, pool, platform)
    except RunActiveError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    logger.info("Run %s started for user_id=%s platform=%s", run_id, user.id, platform)
    return JSONResponse(
        content={"run_id": str(run_id)},
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.get("/{run_id}/status")
async def get_run_status(
    run_id: UUID,
    user: Annotated[UserRow, Depends(get_current_user)],
    run_manager: Annotated[RunManager, Depends(get_run_manager)],
) -> JSONResponse:
    """Return the current status of a pipeline run.

    Returns 404 if the run does not exist or belongs to a different user.
    """
    snapshot = run_manager.get_run(run_id)

    if snapshot is None or snapshot.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")

    result_data = None
    if snapshot.result is not None:
        r = snapshot.result
        result_data = {
            "jobs_found": r.jobs_found,
            "jobs_skipped_dedup": r.jobs_skipped_dedup,
            "jobs_skipped_filter": r.jobs_skipped_filter,
            "jobs_evaluated": r.jobs_evaluated,
            "jobs_stored": r.jobs_stored,
            "errors": list(r.errors),
        }

    return JSONResponse(content={
        "run_id": str(snapshot.run_id),
        "status": snapshot.status,
        "started_at": snapshot.started_at.isoformat(),
        "completed_at": snapshot.completed_at.isoformat() if snapshot.completed_at else None,
        "result": result_data,
        "error": snapshot.error,
    })
