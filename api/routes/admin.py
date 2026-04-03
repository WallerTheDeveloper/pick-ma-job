"""Admin routes — operator-only views gated by ADMIN_EMAIL."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from api.deps import get_admin_user, get_db_pool
from repositories.user import UserRepository, UserRow

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


def _templates(request: Request):
    return request.app.state.templates


@router.get("/users", response_class=HTMLResponse, response_model=None)
async def admin_users(
    request: Request,
    user: Annotated[UserRow, Depends(get_admin_user)],
    pool: Annotated[object, Depends(get_db_pool)],
) -> HTMLResponse:
    """List all users with stats. Admin-only."""
    repo = UserRepository(pool)
    users = await repo.list_users_with_stats()

    return _templates(request).TemplateResponse(
        request,
        "admin_users.html",
        {"user": user, "users": users},
    )
