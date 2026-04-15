"""Admin JSON API — operator-only endpoints gated by ADMIN_EMAIL."""

import asyncio
import logging
from typing import Annotated

import asyncpg
from fastapi import APIRouter, Depends, Query

from api.deps import get_admin_user, get_db_pool
from api.schemas import AdminUsersResponse, UserStatsResponse
from repositories.user import UserRepository, UserRow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["api-admin"])


@router.get("/users")
async def api_admin_users(
    user: Annotated[UserRow, Depends(get_admin_user)],
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> AdminUsersResponse:
    """List all users with stats. Admin-only."""
    repo = UserRepository(pool)
    users, total = await asyncio.gather(
        repo.list_users_with_stats(limit=limit, offset=offset),
        repo.count_users(),
    )

    return AdminUsersResponse(
        total=total,
        users=[
            UserStatsResponse(
                id=u.id,
                email=u.email,
                created_at=u.created_at,
                last_login=u.last_login,
                job_count=u.job_count,
            )
            for u in users
        ],
    )
