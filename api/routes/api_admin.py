"""Admin JSON API — operator-only endpoints gated by ADMIN_EMAIL."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from api.deps import get_admin_user, get_db_pool
from api.schemas import AdminUsersResponse, UserStatsResponse
from repositories.user import UserRepository, UserRow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["api-admin"])


@router.get("/users")
async def api_admin_users(
    user: Annotated[UserRow, Depends(get_admin_user)],
    pool: Annotated[object, Depends(get_db_pool)],
) -> AdminUsersResponse:
    """List all users with stats. Admin-only."""
    repo = UserRepository(pool)
    users = await repo.list_users_with_stats()

    return AdminUsersResponse(
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
