"""Dashboard JSON API — landing page data for the React SPA."""

import logging
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends

from api.deps import get_current_user, get_db_pool, get_profile_service, get_search_config_service
from api.schemas import DashboardResponse, PipelineRunInfo, UserInfo
from repositories.pipeline_run import PipelineRunRepository
from repositories.user import UserRow
from services.profile import ProfileService
from services.search_config import SearchConfigService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["api-dashboard"])


@router.get("/dashboard")
async def api_dashboard(
    user: Annotated[UserRow, Depends(get_current_user)],
    profile_svc: Annotated[ProfileService, Depends(get_profile_service)],
    search_config_svc: Annotated[SearchConfigService, Depends(get_search_config_service)],
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
) -> DashboardResponse:
    """Return dashboard data: user info, profile status, config count, recent runs."""
    has_profile = await profile_svc.get_or_default(user.id) is not None
    configs = await search_config_svc.get_all(user.id)

    run_repo = PipelineRunRepository(pool)
    recent_db_runs = await run_repo.find_by_user(user.id, limit=5)

    recent_runs = [
        PipelineRunInfo(
            id=r.id,
            status=r.status,
            started_at=r.started_at,
            completed_at=r.completed_at,
            result=r.result,
            error=r.error,
        )
        for r in recent_db_runs
    ]

    return DashboardResponse(
        user=UserInfo(id=user.id, email=user.email, is_admin=user.is_admin),
        has_profile=has_profile,
        config_count=len(configs),
        recent_runs=recent_runs,
    )
