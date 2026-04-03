"""FastAPI dependency functions — injected into route handlers via Depends()."""

import os
from typing import Annotated

import asyncpg
from fastapi import Depends, HTTPException, Request, status

from repositories.job_result import JobResultRepository
from repositories.magic_link import MagicLinkRepository
from repositories.profile import ProfileRepository
from repositories.search_config import SearchConfigRepository
from repositories.session import SessionRepository
from repositories.user import UserRepository, UserRow
from services.auth import AuthService
from services.profile import ProfileService
from services.run_manager import RunManager
from services.search_config import SearchConfigService

_SESSION_COOKIE = "session_token"


async def get_db_pool(request: Request) -> asyncpg.Pool:
    """Extract the asyncpg pool stored on app.state by the lifespan handler."""
    return request.app.state.db_pool


async def get_auth_service(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
) -> AuthService:
    """Construct an AuthService with per-request repository instances."""
    return AuthService(
        user_repo=UserRepository(pool),
        magic_link_repo=MagicLinkRepository(pool),
        session_repo=SessionRepository(pool),
        resend_api_key=os.environ["RESEND_API_KEY"],
        email_from=os.environ["EMAIL_FROM"],
        base_url=os.environ.get("BASE_URL", "http://localhost:8000"),
        skip_email=os.environ.get("SKIP_EMAIL", "").lower() in ("1", "true", "yes"),
    )


async def get_current_user(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserRow:
    """Require an authenticated user. Raises HTTP 401 if the session is missing or invalid."""
    token = request.cookies.get(_SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user = await auth_service.get_user_from_session(token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired")

    return user


async def get_profile_service(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
) -> ProfileService:
    """Construct a ProfileService with a per-request repository instance."""
    return ProfileService(profile_repo=ProfileRepository(pool))


async def get_search_config_service(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
) -> SearchConfigService:
    """Construct a SearchConfigService with a per-request repository instance."""
    return SearchConfigService(search_config_repo=SearchConfigRepository(pool))


async def get_job_result_repo(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
) -> JobResultRepository:
    """Construct a JobResultRepository with a per-request pool."""
    return JobResultRepository(pool)


async def get_run_manager(request: Request) -> RunManager:
    """Return the RunManager instance stored on app.state by the lifespan handler."""
    return request.app.state.run_manager


async def get_current_user_optional(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserRow | None:
    """Return the authenticated user, or None if there is no valid session."""
    token = request.cookies.get(_SESSION_COOKIE)
    if not token:
        return None
    return await auth_service.get_user_from_session(token)
