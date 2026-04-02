"""Pipeline routes — trigger background evaluation runs and poll their status.

JSON responses are returned by default. When the request includes the
``HX-Request`` header (sent automatically by HTMX), HTML partials are
returned instead so the browser can swap them directly into the page.
"""

import logging
from typing import Annotated
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse

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


def _templates(request: Request):
    return request.app.state.templates


def _status_partial(
    request: Request,
    run_id: str | None,
    status_str: str,
    result: dict | None,
    error: str | None,
) -> HTMLResponse:
    """Render the run_status partial for an HTMX response."""
    return _templates(request).TemplateResponse(
        request,
        "partials/run_status.html",
        {
            "run_id": run_id,
            "status": status_str,
            "result": result,
            "error": error,
        },
    )


@router.post("", response_model=None)
async def start_run(
    request: Request,
    user: Annotated[UserRow, Depends(get_current_user)],
    run_manager: Annotated[RunManager, Depends(get_run_manager)],
    profile_svc: Annotated[ProfileService, Depends(get_profile_service)],
    search_config_svc: Annotated[SearchConfigService, Depends(get_search_config_service)],
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
    platform: Annotated[str | None, Query()] = None,
) -> JSONResponse | HTMLResponse:
    """Start a background pipeline run for the authenticated user.

    Validates that the user has a profile and at least one search config
    before enqueuing the run. Returns 202 + ``run_id`` (JSON) or the
    status partial (HTMX). Poll ``GET /run/{run_id}/status`` to track progress.

    Args:
        platform: Optional platform slug to restrict the run (e.g. ``upwork``).
                  If omitted, all configured platforms are run.
    """
    is_htmx = bool(request.headers.get("hx-request"))

    profile = await profile_svc.get_or_default(user.id)
    if profile is None:
        msg = "Profile not configured. Please set up your profile before running the pipeline."
        if is_htmx:
            return _status_partial(request, None, "error", None, msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    if platform is not None:
        config = await search_config_svc.get_by_platform(user.id, platform)
        if config is None:
            msg = f"No search config found for platform '{platform}'. Please configure it first."
            if is_htmx:
                return _status_partial(request, None, "error", None, msg)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)
    else:
        configs = await search_config_svc.get_all(user.id)
        if not configs:
            msg = "No search configurations found. Please set up at least one search config first."
            if is_htmx:
                return _status_partial(request, None, "error", None, msg)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg)

    try:
        run_id = run_manager.start_run(user.id, pool, platform)
    except RunActiveError as exc:
        if is_htmx:
            return _status_partial(request, None, "error", None, str(exc))
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    logger.info("Run %s started for user_id=%s platform=%s", run_id, user.id, platform)

    if is_htmx:
        return _status_partial(request, str(run_id), "pending", None, None)

    return JSONResponse(
        content={"run_id": str(run_id)},
        status_code=status.HTTP_202_ACCEPTED,
    )


@router.get("/{run_id}/status", response_model=None)
async def get_run_status(
    run_id: UUID,
    request: Request,
    user: Annotated[UserRow, Depends(get_current_user)],
    run_manager: Annotated[RunManager, Depends(get_run_manager)],
) -> JSONResponse | HTMLResponse:
    """Return the current status of a pipeline run.

    Returns 404 if the run does not exist or belongs to a different user.
    Returns HTML partial for HTMX requests, JSON otherwise.
    """
    is_htmx = bool(request.headers.get("hx-request"))
    snapshot = run_manager.get_run(run_id)

    if snapshot is None or snapshot.user_id != user.id:
        if is_htmx:
            return _status_partial(request, str(run_id), "error", None, "Run not found.")
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

    if is_htmx:
        return _status_partial(
            request,
            str(snapshot.run_id),
            snapshot.status,
            result_data,
            snapshot.error,
        )

    return JSONResponse(content={
        "run_id": str(snapshot.run_id),
        "status": snapshot.status,
        "started_at": snapshot.started_at.isoformat(),
        "completed_at": snapshot.completed_at.isoformat() if snapshot.completed_at else None,
        "result": result_data,
        "error": snapshot.error,
    })
