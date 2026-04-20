"""CV JSON API — upload, retrieve, delete, and customize CVs."""

import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status

from api.csrf import require_csrf
from api.deps import get_current_user, get_db_pool
from api.limiter import limiter
from api.schemas import (
    CVCustomizeRequest,
    CVCustomizeResponse,
    CVGetResponse,
    CVMetadataResponse,
    CVUploadResponse,
    OkResponse,
)
from repositories.cv import CVRepository
from repositories.cv_customization import CVCustomizationRepository
from repositories.job_result import JobResultRepository
from repositories.user import UserRow
from services.cv_service import CVError, CVService

import asyncpg

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cv", tags=["api-cv"])

_ALLOWED_CONTENT_TYPES = {"application/pdf", "application/x-pdf"}


async def get_cv_service(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
) -> CVService:
    """Construct a CVService with per-request repository instances."""
    return CVService(
        cv_repo=CVRepository(pool),
        cv_customization_repo=CVCustomizationRepository(pool),
        job_result_repo=JobResultRepository(pool),
        api_key=os.environ["ANTHROPIC_API_KEY"],
    )


@router.post("/upload", response_model=CVUploadResponse)
@limiter.limit("5/hour")
async def api_upload_cv(
    request: Request,
    file: UploadFile,
    user: Annotated[UserRow, Depends(get_current_user)],
    _csrf: Annotated[None, Depends(require_csrf)],
    cv_service: Annotated[CVService, Depends(get_cv_service)],
) -> CVUploadResponse:
    """Upload a PDF CV (max 5 MB). Replaces any existing CV for this user."""
    content_type = file.content_type or ""
    if content_type not in _ALLOWED_CONTENT_TYPES and not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are accepted.",
        )

    file_bytes = await file.read()
    try:
        cv = await cv_service.upload_cv(
            user_id=user.id,
            filename=file.filename or "cv.pdf",
            file_bytes=file_bytes,
        )
    except CVError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return CVUploadResponse(
        filename=cv.filename,
        structured=cv.structured,
        updated_at=cv.updated_at,
    )


@router.get("", response_model=CVGetResponse)
async def api_get_cv(
    user: Annotated[UserRow, Depends(get_current_user)],
    cv_service: Annotated[CVService, Depends(get_cv_service)],
) -> CVGetResponse:
    """Return CV metadata and structured preview, or null if no CV uploaded."""
    cv = await cv_service.get_cv(user.id)
    if cv is None:
        return CVGetResponse(cv=None)
    return CVGetResponse(
        cv=CVMetadataResponse(
            filename=cv.filename,
            structured=cv.structured,
            updated_at=cv.updated_at,
        )
    )


@router.delete("", response_model=OkResponse)
async def api_delete_cv(
    user: Annotated[UserRow, Depends(get_current_user)],
    _csrf: Annotated[None, Depends(require_csrf)],
    cv_service: Annotated[CVService, Depends(get_cv_service)],
) -> OkResponse:
    """Delete the user's CV and all cached customizations."""
    await cv_service.delete_cv(user.id)
    return OkResponse()


@router.post("/customize", response_model=CVCustomizeResponse)
@limiter.limit("30/hour")
async def api_customize_cv(
    request: Request,
    body: CVCustomizeRequest,
    user: Annotated[UserRow, Depends(get_current_user)],
    _csrf: Annotated[None, Depends(require_csrf)],
    cv_service: Annotated[CVService, Depends(get_cv_service)],
) -> CVCustomizeResponse:
    """Generate or return a cached AI-tailored CV for a specific job result."""
    from repositories.profile import ProfileRepository

    profile_repo = ProfileRepository(request.app.state.db_pool)
    profile = await profile_repo.find_by_user_id(user.id)
    threshold = profile.cv_customize_threshold if profile else 7

    try:
        customized_text, from_cache = await cv_service.customize_cv(
            user_id=user.id,
            job_result_id=body.job_result_id,
            cv_customize_threshold=threshold,
            force_regenerate=body.force_regenerate,
            adjustment_notes=body.adjustment_notes,
        )
    except CVError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return CVCustomizeResponse(customized_text=customized_text, from_cache=from_cache)
