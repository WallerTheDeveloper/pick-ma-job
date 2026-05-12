"""ProposalRepository — cached Upwork proposal generation results."""

import logging
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import asyncpg

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProposalRow:
    id: UUID
    user_id: UUID
    job_result_id: UUID
    proposal_text: str
    created_at: datetime
    updated_at: datetime


def _row_to_proposal(row: asyncpg.Record) -> ProposalRow:
    return ProposalRow(
        id=row["id"],
        user_id=row["user_id"],
        job_result_id=row["job_result_id"],
        proposal_text=row["proposal_text"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class ProposalRepository:
    def __init__(self, pool: asyncpg.Pool) -> None:
        self._pool = pool

    async def find_by_user_and_job(
        self,
        user_id: UUID,
        job_result_id: UUID,
    ) -> ProposalRow | None:
        """Return a cached proposal, or None if not generated yet."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, job_result_id, proposal_text, created_at, updated_at
                FROM proposals
                WHERE user_id = $1 AND job_result_id = $2
                """,
                user_id,
                job_result_id,
            )
        return _row_to_proposal(row) if row else None

    async def upsert(
        self,
        user_id: UUID,
        job_result_id: UUID,
        proposal_text: str,
    ) -> ProposalRow:
        """Insert or replace a proposal for a specific job. Returns the row."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO proposals (user_id, job_result_id, proposal_text)
                VALUES ($1, $2, $3)
                ON CONFLICT (user_id, job_result_id) DO UPDATE SET
                    proposal_text = EXCLUDED.proposal_text,
                    updated_at      = now()
                RETURNING id, user_id, job_result_id, proposal_text, created_at, updated_at
                """,
                user_id,
                job_result_id,
                proposal_text,
            )
        logger.debug(
            "Upserted proposal user_id=%s job_result_id=%s", user_id, job_result_id
        )
        return _row_to_proposal(row)