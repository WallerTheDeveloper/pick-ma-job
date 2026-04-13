"""Pipeline JSON API — trigger and poll background evaluation runs.

Re-prefixed under /api/run for the React SPA. Always returns JSON (no HTMX branching).
"""

import logging
from typing import Annotated
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Body, Depends, HTTPException, status

from api.csrf import require_csrf
from api.deps import (
    get_current_user,
    get_db_pool,
    get_profile_service,
    get_run_manager,
    get_search_config_service,
)
from api.schemas import RunStartRequest, RunStartResponse, RunStatusResponse
from repositories.user import UserRow
from services.profile import ProfileService
from services.run_manager import RunActiveError, RunManager
from services.search_config import KNOWN_PLATFORMS, SearchConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/run", tags=["api-pipeline"])


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def api_start_run(
    user: Annotated[UserRow, Depends(get_current_user)],
    _csrf: Annotated[None, Depends(require_csrf)],
    run_manager: Annotated[RunManager, Depends(get_run_manager)],
    profile_svc: Annotated[ProfileService, Depends(get_profile_service)],
    search_config_svc: Annotated[SearchConfigService, Depends(get_search_config_service)],
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
    body: RunStartRequest = Body(default=RunStartRequest()),
) -> RunStartResponse:
    """Start a background pipeline run. Returns the run_id immediately."""
    profile = await profile_svc.get_or_default(user.id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please complete your profile before running the pipeline.",
        )

    platforms = body.platforms
    if platforms is not None:
        unknown = [p for p in platforms if p not in KNOWN_PLATFORMS]
        if unknown:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown platform(s): {unknown}. Supported: {sorted(KNOWN_PLATFORMS)}",
            )
        for platform in platforms:
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
        run_id = run_manager.start_run(user.id, pool, platforms)
    except RunActiveError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    logger.info("Run %s started for user_id=%s platforms=%s", run_id, user.id, platforms)
    return RunStartResponse(run_id=run_id)


@router.get("/{run_id}/status")
async def api_get_run_status(
    run_id: UUID,
    user: Annotated[UserRow, Depends(get_current_user)],
    run_manager: Annotated[RunManager, Depends(get_run_manager)],
) -> RunStatusResponse:
    """Return the current status of a pipeline run."""
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

    return RunStatusResponse(
        run_id=snapshot.run_id,
        status=snapshot.status,
        started_at=snapshot.started_at,
        completed_at=snapshot.completed_at,
        result=result_data,
        error=snapshot.error,
    )
