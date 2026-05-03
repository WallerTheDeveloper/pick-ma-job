"""PipelineService — orchestrates scrape → deduplicate → filter → evaluate → store.

One ``run_pipeline`` call handles the full lifecycle for a user on one or all
platforms. Heavy work (Apify, Claude) runs sequentially within the call — the
caller (RunManager in 4.4) is responsible for wrapping this in a background
task.
"""

import copy
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import asyncio

from core.evaluator import Evaluator
from core.llm_client import LLMClient
from core.prompt_adapter import load_platform_context, profile_row_to_prompt_dict
from core.settings import Settings
from repositories.company_blacklist import CompanyBlacklistRepository
from repositories.job_list import JobListRepository
from repositories.job_result import JobResultRepository
from repositories.profile import ProfileRepository
from repositories.search_config import SearchConfigRepository, SearchConfigRow
from scrapers.base import NormalizedJob
from scrapers.registry import get_scraper, list_platforms

logger = logging.getLogger(__name__)

_PLATFORMS_DIR = Path(__file__).parent.parent / "configs" / "platforms"


class PipelineError(Exception):
    """Raised for expected pipeline failures (missing profile, bad config, etc.)."""


@dataclass(frozen=True)
class PipelineStats:
    """Immutable pipeline statistics that supports addition (monoid).

    Use ``+`` to combine two ``PipelineStats`` instances, or ``sum()``
    with ``PipelineStats.zero()`` as the start value to aggregate a list.
    """

    jobs_found: int = 0
    jobs_skipped_dedup: int = 0
    jobs_skipped_filter: int = 0
    jobs_skipped_blacklist: int = 0
    jobs_skipped_low_score: int = 0
    jobs_evaluated: int = 0
    jobs_stored: int = 0
    jobs_failed: int = 0
    errors: tuple[str, ...] = ()

    def __add__(self, other: "PipelineStats") -> "PipelineStats":
        return PipelineStats(
            jobs_found=self.jobs_found + other.jobs_found,
            jobs_skipped_dedup=self.jobs_skipped_dedup + other.jobs_skipped_dedup,
            jobs_skipped_filter=self.jobs_skipped_filter + other.jobs_skipped_filter,
            jobs_skipped_blacklist=self.jobs_skipped_blacklist + other.jobs_skipped_blacklist,
            jobs_skipped_low_score=self.jobs_skipped_low_score + other.jobs_skipped_low_score,
            jobs_evaluated=self.jobs_evaluated + other.jobs_evaluated,
            jobs_stored=self.jobs_stored + other.jobs_stored,
            jobs_failed=self.jobs_failed + other.jobs_failed,
            errors=self.errors + other.errors,
        )

    @classmethod
    def zero(cls) -> "PipelineStats":
        """Return the identity element (all zeros)."""
        return cls()


@dataclass(frozen=True)
class _EvalResult:
    """Internal result from evaluating and storing a single job."""

    job_id: UUID
    evaluation: dict | None  # None means low score (skipped full eval)
    stored: bool
    errors: tuple[str, ...]


class PipelineService:
    """Orchestrates the scrape → dedup → filter → evaluate → store pipeline.

    Args:
        profile_repo: Repository for loading user profiles.
        search_config_repo: Repository for loading user search configs.
        job_result_repo: Repository for dedup checks and result storage.
        llm_client: Shared ``LLMClient`` passed through to the ``Evaluator``.
        settings: Validated application settings.
    """

    def __init__(
        self,
        profile_repo: ProfileRepository,
        search_config_repo: SearchConfigRepository,
        job_result_repo: JobResultRepository,
        job_list_repo: JobListRepository,
        company_blacklist_repo: CompanyBlacklistRepository,
        llm_client: LLMClient,
        settings: Settings,
    ) -> None:
        self._profile_repo = profile_repo
        self._search_config_repo = search_config_repo
        self._job_result_repo = job_result_repo
        self._job_list_repo = job_list_repo
        self._company_blacklist_repo = company_blacklist_repo
        self._llm_client = llm_client
        self._settings = settings
        self._concurrency: int = settings.evaluation_concurrency
        self._exclude_keywords: tuple[str, ...] = tuple(
            kw.lower() for kw in settings.exclude_title_keywords
        )

    async def run_pipeline(
        self,
        user_id: UUID,
        platforms: list[str] | None = None,
    ) -> PipelineStats:
        """Run the full pipeline for a user on one or all configured platforms.

        Args:
            user_id: The authenticated user.
            platforms: If given, only run these platforms. None means run all
                configured platforms.

        Returns:
            A ``PipelineStats`` summarising counts and any non-fatal errors.

        Raises:
            PipelineError: If platforms is empty, contains unknown slugs, the
                user has no profile, or no matching search configs exist.
        """
        if platforms is not None:
            if len(platforms) == 0:
                raise PipelineError("No platforms selected.")
            known = set(list_platforms())
            unknown = [p for p in platforms if p not in known]
            if unknown:
                raise PipelineError(
                    f"Unknown platform(s): {', '.join(repr(p) for p in unknown)}. "
                    f"Known: {', '.join(sorted(known))}."
                )

        profile = await self._profile_repo.find_by_user_id(user_id)
        if profile is None:
            logger.warning("Pipeline blocked: no profile for user_id=%s", user_id)
            raise PipelineError(
                "Please complete your profile before running the pipeline."
            )

        all_configs: list[SearchConfigRow] = await self._search_config_repo.find_by_user_id(user_id)
        if platforms is not None:
            platform_set = set(platforms)
            search_configs = [c for c in all_configs if c.platform in platform_set]
        else:
            search_configs = all_configs

        if not search_configs:
            raise PipelineError(
                "No search configurations found. "
                "Please set up at least one search config before running the pipeline."
            )

        prompt_dict = profile_row_to_prompt_dict(profile)
        evaluator = Evaluator(prompt_dict, self._settings, llm_client=self._llm_client)
        run_started_at = datetime.now(timezone.utc)

        platform_results = [
            await self._run_platform(
                user_id=user_id,
                config_row=config_row,
                evaluator=evaluator,
                run_started_at=run_started_at,
            )
            for config_row in search_configs
        ]

        return sum(platform_results, PipelineStats.zero())

    async def _run_platform(
        self,
        user_id: UUID,
        config_row: SearchConfigRow,
        evaluator: Evaluator,
        run_started_at: datetime,
    ) -> PipelineStats:
        platform = config_row.platform
        logger.info("Pipeline starting: user_id=%s platform=%s", user_id, platform)

        platform_config_path = _PLATFORMS_DIR / f"{platform}.json"
        if not platform_config_path.exists():
            msg = f"No platform config file for '{platform}'"
            logger.warning("%s — skipping.", msg)
            return PipelineStats(errors=(msg,))

        static_config = json.loads(platform_config_path.read_text(encoding="utf-8"))
        merged_config = _merge_config(static_config, config_row)

        try:
            platform_context = load_platform_context(platform)
        except FileNotFoundError:
            msg = f"No platform context file for '{platform}'"
            logger.warning("%s — skipping.", msg)
            return PipelineStats(errors=(msg,))

        scraper = get_scraper(platform)
        try:
            jobs = await scraper.fetch_jobs(merged_config)
        except Exception as exc:
            msg = f"Scraper failed for '{platform}': {exc}"
            logger.error(msg)
            return PipelineStats(errors=(msg,))

        jobs_found = len(jobs)
        logger.info("Fetched %d jobs from platform=%s", jobs_found, platform)

        blacklist = await self._company_blacklist_repo.find_names_by_user_id(user_id)

        # Pre-filter jobs serially (dedup, blacklist, keyword filter)
        existing_ids = await self._job_result_repo.find_existing_ids(
            user_id, platform, [j.id for j in jobs]
        )

        jobs_skipped_dedup = 0
        jobs_skipped_filter = 0
        jobs_skipped_blacklist = 0
        jobs_to_evaluate: list[NormalizedJob] = []

        for job in jobs:
            if job.id in existing_ids:
                jobs_skipped_dedup += 1
                continue

            if self._is_blacklisted(job, blacklist):
                logger.debug("Blacklist skipped: '%s' (company: %s)", job.title, job.company_name)
                jobs_skipped_blacklist += 1
                continue

            if self._is_filtered(job.title):
                logger.debug("Pre-filter skipped: '%s'", job.title)
                jobs_skipped_filter += 1
                continue

            jobs_to_evaluate.append(job)

        # Evaluate jobs concurrently with semaphore
        semaphore = asyncio.Semaphore(self._concurrency)
        eval_tasks = [
            self._evaluate_and_store(
                job=job,
                user_id=user_id,
                platform=platform,
                evaluator=evaluator,
                platform_context=platform_context,
                semaphore=semaphore,
            )
            for job in jobs_to_evaluate
        ]
        eval_results = await asyncio.gather(*eval_tasks, return_exceptions=True)

        # Aggregate results from concurrent evaluation
        jobs_skipped_low_score = 0
        jobs_evaluated = 0
        jobs_stored = 0
        jobs_failed = 0
        errors: list[str] = []
        new_job_ids: list[UUID] = []

        for result in eval_results:
            if isinstance(result, Exception):
                jobs_failed += 1
                errors.append(f"Job evaluation failed: {type(result).__name__}: {result}")
                logger.error("Job evaluation failed: %s", result, exc_info=True)
            elif isinstance(result, _EvalResult):
                if result.evaluation is None:
                    jobs_skipped_low_score += 1
                else:
                    jobs_evaluated += 1
                if result.stored:
                    jobs_stored += 1
                    new_job_ids.append(result.job_id)
                errors.extend(result.errors)

        if new_job_ids:
            list_name = f"{platform}-{run_started_at.strftime('%Y-%m-%d')}"
            try:
                job_list = await self._job_list_repo.create(user_id, list_name)
                await self._job_list_repo.add_items(job_list.id, new_job_ids)
                logger.info(
                    "Auto-created list %r (id=%s) with %d jobs for user_id=%s",
                    list_name,
                    job_list.id,
                    len(new_job_ids),
                    user_id,
                )
            except Exception as exc:
                logger.error(
                    "Auto-list creation failed for platform=%s user_id=%s: %s",
                    platform,
                    user_id,
                    exc,
                )

        logger.info(
            "Pipeline done: platform=%s found=%d dedup=%d blacklist=%d filter=%d low_score=%d evaluated=%d stored=%d failed=%d",
            platform,
            jobs_found,
            jobs_skipped_dedup,
            jobs_skipped_blacklist,
            jobs_skipped_filter,
            jobs_skipped_low_score,
            jobs_evaluated,
            jobs_stored,
            jobs_failed,
        )

        return PipelineStats(
            jobs_found=jobs_found,
            jobs_skipped_dedup=jobs_skipped_dedup,
            jobs_skipped_filter=jobs_skipped_filter,
            jobs_skipped_blacklist=jobs_skipped_blacklist,
            jobs_skipped_low_score=jobs_skipped_low_score,
            jobs_evaluated=jobs_evaluated,
            jobs_stored=jobs_stored,
            jobs_failed=jobs_failed,
            errors=tuple(errors),
        )

    async def _evaluate_and_store(
        self,
        job: NormalizedJob,
        user_id: UUID,
        platform: str,
        evaluator: Evaluator,
        platform_context: dict,
        semaphore: asyncio.Semaphore,
    ) -> _EvalResult:
        """Evaluate a single job and store the result.

        This method is designed to be called concurrently with a semaphore to limit
        the number of simultaneous evaluations.

        Args:
            job: The normalized job to evaluate.
            user_id: The authenticated user.
            platform: The platform slug.
            evaluator: The Evaluator instance.
            platform_context: Loaded platform context.
            semaphore: Semaphore to limit concurrency.

        Returns:
            An _EvalResult with the job_id, evaluation result, stored status, and any errors.
        """
        async with semaphore:
            errors: list[str] = []

            try:
                result = await evaluator.evaluate(job, platform_context)
            except Exception as exc:
                logger.error(
                    "Evaluation failed for '%s': %s",
                    job.title,
                    exc,
                    exc_info=True,
                )
                return _EvalResult(
                    job_id=job.id,
                    evaluation=None,
                    stored=False,
                    errors=(f"Evaluation failed for '{job.title}': {type(exc).__name__}: {exc}",),
                )

            if result.evaluation is None:
                # Low score - still store the job with score only
                try:
                    stored = await self._job_result_repo.insert(
                        user_id=user_id,
                        platform=platform,
                        job_id=job.id,
                        title=job.title,
                        url=job.url,
                        score=result.relevancy_score,
                        evaluation=None,
                    )
                    return _EvalResult(
                        job_id=stored.id if stored else job.id,
                        evaluation=None,
                        stored=stored is not None,
                        errors=(),
                    )
                except Exception as exc:
                    logger.error(
                        "DB insert failed for '%s': %s",
                        job.title,
                        exc,
                        exc_info=True,
                    )
                    return _EvalResult(
                        job_id=job.id,
                        evaluation=None,
                        stored=False,
                        errors=(f"DB insert failed for '{job.title}': {type(exc).__name__}: {exc}",),
                    )

            # High score - store with full evaluation
            try:
                stored = await self._job_result_repo.insert(
                    user_id=user_id,
                    platform=platform,
                    job_id=job.id,
                    title=job.title,
                    url=job.url,
                    score=result.relevancy_score,
                    evaluation=result.raw if result.evaluation is not None else None,
                )
                return _EvalResult(
                    job_id=stored.id if stored else job.id,
                    evaluation=result.raw if result.evaluation is not None else None,
                    stored=stored is not None,
                    errors=(),
                )
            except Exception as exc:
                logger.error(
                    "DB insert failed for '%s': %s",
                    job.title,
                    exc,
                    exc_info=True,
                )
                return _EvalResult(
                    job_id=job.id,
                    evaluation=None,
                    stored=False,
                    errors=(f"DB insert failed for '{job.title}': {type(exc).__name__}: {exc}",),
                )

    def _is_filtered(self, title: str) -> bool:
        """Return True if the job title matches any excluded keyword (case-insensitive)."""
        title_lower = title.lower()
        return any(kw in title_lower for kw in self._exclude_keywords)

    def _is_blacklisted(self, job: NormalizedJob, blacklist: tuple[str, ...]) -> bool:
        """Return True if the job's company name matches any blacklisted entry (substring, case-insensitive)."""
        if not blacklist:
            return False
        company = job.company_name
        if not company:
            return False
        company_lower = company.lower()
        return any(entry in company_lower for entry in blacklist)


def _merge_config(static_config: dict, config_row: SearchConfigRow) -> dict:
    """Merge static platform config with the user's DB-stored search config.

    The static config provides ``actor_id`` and ``field_mappings``.
    If the user has set filters, they replace ``scraper.input`` entirely.
    The user's ``query`` always overrides ``scraper.input.query``.

    Args:
        static_config: Parsed ``configs/platforms/<platform>.json``.
        config_row: The user's ``SearchConfigRow`` from the database.

    Returns:
        A new merged config dict ready to pass to ``scraper.fetch_jobs``.
    """
    merged = copy.deepcopy(static_config)

    if config_row.filters:
        merged.setdefault("scraper", {})["input"] = dict(config_row.filters)

    if config_row.query:
        merged.setdefault("scraper", {}).setdefault("input", {})["query"] = config_row.query

    return merged
