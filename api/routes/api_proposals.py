"""Proposal JSON API — generate and retrieve Upwork proposals."""

import logging
from typing import Annotated
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, Request

from api.csrf import require_csrf
from api.deps import get_current_user, get_db_pool, get_llm_client
from api.limiter import limiter
from api.schemas import ProposalGenerateRequest, ProposalResponse
from core.exceptions import DomainError, NotFoundError
from core.llm_client import LLMClient
from repositories.job_result import JobResultRepository
from repositories.profile import ProfileRepository
from repositories.proposal import ProposalRepository
from repositories.user import UserRow
from services.proposal_service import ProposalService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/results", tags=["api-proposals"])


async def get_proposal_service(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
    llm_client: Annotated[LLMClient, Depends(get_llm_client)],
) -> ProposalService:
    """Construct a ProposalService with per-request repository instances."""
    return ProposalService(
        proposal_repo=ProposalRepository(pool),
        job_result_repo=JobResultRepository(pool),
        profile_repo=ProfileRepository(pool),
        llm_client=llm_client,
    )


async def get_proposal_repo(
    pool: Annotated[asyncpg.Pool, Depends(get_db_pool)],
) -> ProposalRepository:
    """Construct a ProposalRepository with a per-request pool."""
    return ProposalRepository(pool)


@router.post("/{result_id}/proposal", response_model=ProposalResponse)
@limiter.limit("30/hour")
async def api_generate_proposal(
    request: Request,
    result_id: UUID,
    body: ProposalGenerateRequest,
    _csrf: Annotated[None, Depends(require_csrf)],
    user: Annotated[UserRow, Depends(get_current_user)],
    proposal_service: Annotated[ProposalService, Depends(get_proposal_service)],
) -> ProposalResponse:
    """Generate or return a cached Upwork proposal for a job result.

    If force_regenerate is True, always calls Claude (overwriting cache).
    Optional adjustment_notes allows feedback for regeneration.
    """
    if body.force_regenerate:
        proposal_text, from_cache = await proposal_service.regenerate_proposal(
            user_id=user.id,
            job_result_id=result_id,
            adjustment_notes=body.adjustment_notes,
        )
    else:
        proposal_text, from_cache = await proposal_service.generate_proposal(
            user_id=user.id,
            job_result_id=result_id,
        )

    return ProposalResponse(
        proposal_text=proposal_text,
        from_cache=from_cache,
    )


@router.get("/{result_id}/proposal", response_model=ProposalResponse)
async def api_get_cached_proposal(
    result_id: UUID,
    user: Annotated[UserRow, Depends(get_current_user)],
    proposal_repo: Annotated[ProposalRepository, Depends(get_proposal_repo)],
) -> ProposalResponse:
    """Return a cached proposal or 404 if none exists."""
    cached = await proposal_repo.find_by_user_and_job(user.id, result_id)
    if cached is None:
        raise NotFoundError("No proposal found for this job result.")

    return ProposalResponse(
        proposal_text=cached.proposal_text,
        from_cache=True,
    )