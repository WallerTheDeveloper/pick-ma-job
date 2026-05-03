"""AutoListService — creates post-pipeline job lists idempotently.

Extracted from ``services/pipeline._run_platform`` to decouple list creation
from scraping/evaluation orchestration and to prevent duplicate-name collisions
when a user runs the pipeline multiple times in one day.
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from repositories.job_list import JobListRepository

logger = logging.getLogger(__name__)


class AutoListService:
    """Creates a job list for a pipeline run, idempotent by (user_id, run_id, platform).

    Args:
        job_list_repo: Repository for job list CRUD operations.
    """

    def __init__(self, job_list_repo: JobListRepository) -> None:
        self._job_list_repo = job_list_repo

    async def create_for_run(
        self,
        user_id: UUID,
        run_id: UUID,
        job_result_ids: list[UUID],
        platform: str,
    ) -> UUID | None:
        """Create or reuse a job list for a specific pipeline run and platform.

        Idempotent: if a list with the generated name already exists for this
        user, new job IDs are appended (duplicates silently skipped).

        Name format: ``{platform}-{YYYY-MM-DD}-{run_id_first_8}`` to guarantee
        uniqueness across same-day runs.

        Args:
            user_id: The authenticated user.
            run_id: The pipeline run UUID.
            job_result_ids: Job result IDs to add to the list.
            platform: The platform slug (e.g. ``"upwork"``).

        Returns:
            The list UUID if created/updated, or None if ``job_result_ids`` is empty.
        """
        if not job_result_ids:
            return None

        list_name = f"{platform}-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-{str(run_id)[:8]}"

        # Check if list already exists (idempotency)
        existing_lists = await self._job_list_repo.find_by_user(user_id)
        existing = next((lst for lst in existing_lists if lst.name == list_name), None)

        if existing is not None:
            await self._job_list_repo.add_items(existing.id, job_result_ids)
            logger.info(
                "Appended %d items to existing list %r (id=%s) for user_id=%s",
                len(job_result_ids),
                list_name,
                existing.id,
                user_id,
            )
            return existing.id

        # Create new list
        job_list = await self._job_list_repo.create(user_id, list_name)
        await self._job_list_repo.add_items(job_list.id, job_result_ids)
        logger.info(
            "Auto-created list %r (id=%s) with %d jobs for user_id=%s",
            list_name,
            job_list.id,
            len(job_result_ids),
            user_id,
        )
        return job_list.id
