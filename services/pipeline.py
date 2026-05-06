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
from functools import lru_cache
from pathlib import Path
from uuid import UUID

import asyncio

from core.language_detector import LanguageDetector
from core.evaluator import Evaluator
from core.exceptions import DomainError
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
from services.auto_list_service import AutoListService

logger = logging.getLogger(__name__)

_PLATFORMS_DIR = Path(__file__).parent.parent / "configs" / "platforms"


@lru_cache(maxsize=None)
def _load_platform_config(platform: str) -> dict:
    """Load and cache the static platform config JSON from disk.

    The file is read once per process lifetime and cached thereafter.
    """
    path = _PLATFORMS_DIR / f"{platform}.json"
    return json.loads(path.read_text(encoding="utf-8"))

# Backward-compatible alias — existing tests catch PipelineError.
PipelineError = DomainError


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
    jobs_skipped_language: int = 0
    jobs_skipped_closed: int = 0
    jobs_skipped_low_score: int = 0
    jobs_stored: int = 0
    jobs_failed: int = 0
    jobs_score_parse_failed: int = 0
    errors: tuple[str, ...] = ()

    def __add__(self, other: "PipelineStats") -> "PipelineStats":
        return PipelineStats(
            jobs_found=self.jobs_found + other.jobs_found,
            jobs_skipped_dedup=self.jobs_skipped_dedup + other.jobs_skipped_dedup,
            jobs_skipped_filter=self.jobs_skipped_filter + other.jobs_skipped_filter,
            jobs_skipped_blacklist=self.jobs_skipped_blacklist + other.jobs_skipped_blacklist,
            jobs_skipped_language=self.jobs_skipped_language + other.jobs_skipped_language,
            jobs_skipped_closed=self.jobs_skipped_closed + other.jobs_skipped_closed,
            jobs_skipped_low_score=self.jobs_skipped_low_score + other.jobs_skipped_low_score,
            jobs_stored=self.jobs_stored + other.jobs_stored,
            jobs_failed=self.jobs_failed + other.jobs_failed,
            jobs_score_parse_failed=self.jobs_score_parse_failed + other.jobs_score_parse_failed,
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
    pass1_parse_failed: bool
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
        auto_list_service: AutoListService | None = None,
        language_detector: LanguageDetector | None = None,
    ) -> None:
        self._profile_repo = profile_repo
        self._search_config_repo = search_config_repo
        self._job_result_repo = job_result_repo
        self._job_list_repo = job_list_repo
        self._company_blacklist_repo = company_blacklist_repo
        self._llm_client = llm_client
        self._settings = settings
        self._auto_list_service = auto_list_service
        self._language_detector = language_detector or LanguageDetector(llm_client)
        self._concurrency: int = settings.evaluation_concurrency
        self._exclude_keywords: tuple[str, ...] = tuple(
            kw.lower() for kw in settings.exclude_title_keywords
        )

    async def run_pipeline(
        self,
        user_id: UUID,
        platforms: list[str] | None = None,
        run_id: UUID | None = None,
    ) -> PipelineStats:
        """Run the full pipeline for a user on one or all configured platforms.

        Args:
            user_id: The authenticated user.
            platforms: If given, only run these platforms. None means run all
                configured platforms.
            run_id: Optional pipeline run UUID. When provided, used by
                ``AutoListService`` to create idempotent per-run job lists.

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
        user_languages = list(profile.languages)
        evaluator = Evaluator(prompt_dict, self._settings, llm_client=self._llm_client)
        run_started_at = datetime.now(timezone.utc)

        # Determine effective exclude keywords: user's list if non-empty, else global defaults
        user_exclude = set(kw.lower() for kw in (profile.exclude_keywords or []))
        effective_exclude: tuple[str, ...] = (
            tuple(sorted(user_exclude)) if user_exclude
            else self._exclude_keywords
        )

        platform_results: list[tuple[PipelineStats, list[UUID], list[UUID], list[UUID], str]] = [
            await self._run_platform(
                user_id=user_id,
                config_row=config_row,
                evaluator=evaluator,
                run_started_at=run_started_at,
                user_languages=user_languages,
                exclude_keywords=effective_exclude,
            )
            for config_row in search_configs
        ]

        # Auto-create job lists after all platforms complete
        if self._auto_list_service is not None and run_id is not None:
            for _stats, new_job_ids, _skipped_lang_ids, _skipped_closed_ids, platform in platform_results:
                if new_job_ids:
                    try:
                        await self._auto_list_service.create_for_run(
                            user_id=user_id,
                            run_id=run_id,
                            job_result_ids=new_job_ids,
                            platform=platform,
                        )
                    except Exception as exc:
                        logger.error(
                            "Auto-list creation failed for platform=%s user_id=%s: %s",
                            platform,
                            user_id,
                            exc,
                        )

        # Auto-create skipped-jobs list for language-filtered and closed jobs
        all_skipped_language_ids: list[UUID] = []
        for _stats, _new_ids, skipped_ids, _skipped_closed_ids, _platform in platform_results:
            all_skipped_language_ids.extend(skipped_ids)

        if all_skipped_language_ids and self._job_list_repo is not None:
            skipped_list_name = f"Skipped jobs {run_started_at.strftime('%Y-%m-%d %H:%M:%S')}"
            try:
                skipped_list = await self._job_list_repo.create(user_id, skipped_list_name)
                await self._job_list_repo.add_items(skipped_list.id, all_skipped_language_ids)
                logger.info(
                    "Created skipped-jobs list %r with %d jobs for user_id=%s",
                    skipped_list_name,
                    len(all_skipped_language_ids),
                    user_id,
                )
            except Exception as exc:
                logger.error(
                    "Skipped-jobs list creation failed for user_id=%s: %s",
                    user_id,
                    exc,
                )

        # Also collect closed-job IDs for the skipped list
        all_skipped_closed_ids: list[UUID] = []
        for _stats, _new_ids, _skipped_lang_ids, skipped_closed_ids, _platform in platform_results:
            all_skipped_closed_ids.extend(skipped_closed_ids)

        if all_skipped_closed_ids and self._job_list_repo is not None:
            closed_list_name = f"Closed jobs {run_started_at.strftime('%Y-%m-%d %H:%M:%S')}"
            try:
                closed_list = await self._job_list_repo.create(user_id, closed_list_name)
                await self._job_list_repo.add_items(closed_list.id, all_skipped_closed_ids)
                logger.info(
                    "Created closed-jobs list %r with %d jobs for user_id=%s",
                    closed_list_name,
                    len(all_skipped_closed_ids),
                    user_id,
                )
            except Exception as exc:
                logger.error(
                    "Closed-jobs list creation failed for user_id=%s: %s",
                    user_id,
                    exc,
                )

        return sum((stats for stats, _, _, _, _ in platform_results), PipelineStats.zero())

    async def _run_platform(
        self,
        user_id: UUID,
        config_row: SearchConfigRow,
        evaluator: Evaluator,
        run_started_at: datetime,
        user_languages: list[str] | None = None,
        exclude_keywords: tuple[str, ...] = (),
    ) -> tuple[PipelineStats, list[UUID], list[UUID], list[UUID], str]:
        platform = config_row.platform
        logger.info("Pipeline starting: user_id=%s platform=%s", user_id, platform)

        platform_config_path = _PLATFORMS_DIR / f"{platform}.json"
        if not platform_config_path.exists():
            msg = f"No platform config file for '{platform}'"
            logger.warning("%s — skipping.", msg)
            return PipelineStats(errors=(msg,)), [], [], [], platform

        static_config = _load_platform_config(platform)
        merged_config = _merge_config(static_config, config_row)

        try:
            platform_context = load_platform_context(platform)
        except FileNotFoundError:
            msg = f"No platform context file for '{platform}'"
            logger.warning("%s — skipping.", msg)
            return PipelineStats(errors=(msg,)), [], [], [], platform

        scraper = get_scraper(platform)
        try:
            jobs = await scraper.fetch_jobs(merged_config)
        except Exception as exc:
            msg = f"Scraper failed for '{platform}': {exc}"
            logger.error(msg)
            return PipelineStats(errors=(msg,)), [], [], [], platform

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
                logger.debug("Blacklist skipped: '%s' (company: %s)", job.title, job.effective_company_name)
                jobs_skipped_blacklist += 1
                continue

            if self._is_filtered(job.title, exclude_keywords):
                logger.debug("Pre-filter skipped: '%s'", job.title)
                jobs_skipped_filter += 1
                continue

            jobs_to_evaluate.append(job)

        # Filter closed jobs — skip jobs no longer accepting applications
        jobs_skipped_closed = 0
        skipped_closed_ids: list[UUID] = []
        filtered_jobs: list[NormalizedJob] = []
        for job in jobs_to_evaluate:
            if job.is_closed:
                logger.debug("Closed job skipped: '%s'", job.title)
                jobs_skipped_closed += 1
                try:
                    skipped_row = await self._job_result_repo.insert(
                        user_id=user_id,
                        platform=platform,
                        job_id=job.id,
                        title=job.title,
                        url=job.url,
                        score=None,
                        evaluation=None,
                        skip_reason="job_closed",
                        is_closed=True,
                    )
                    if skipped_row is not None:
                        skipped_closed_ids.append(skipped_row.id)
                except Exception as exc:
                    logger.error(
                        "DB insert failed for closed job '%s': %s",
                        job.title,
                        exc,
                    )
                continue
            filtered_jobs.append(job)
        jobs_to_evaluate = filtered_jobs

        # Language filter: skip jobs whose description is in a language the user doesn't speak
        jobs_skipped_language = 0
        skipped_language_ids: list[UUID] = []

        if user_languages:
            user_languages_lower = {lang.lower() for lang in user_languages}
            filtered_jobs: list[NormalizedJob] = []
            for job in jobs_to_evaluate:
                try:
                    detected_lang = await self._language_detector.detect(job.description)
                except Exception as exc:
                    logger.warning(
                        "Language detection failed for '%s': %s — including job by default",
                        job.title,
                        exc,
                    )
                    filtered_jobs.append(job)
                    continue

                if detected_lang.lower() not in user_languages_lower:
                    logger.debug(
                        "Language filter skipped: '%s' (detected: %s, user langs: %s)",
                        job.title,
                        detected_lang,
                        user_languages,
                    )
                    jobs_skipped_language += 1

                    # Store the skipped job with skip reason so it appears in lists
                    try:
                        skipped_row = await self._job_result_repo.insert(
                            user_id=user_id,
                            platform=platform,
                            job_id=job.id,
                            title=job.title,
                            url=job.url,
                            score=None,
                            evaluation=None,
                            skip_reason="language",
                            detected_language=detected_lang,
                        )
                        if skipped_row is not None:
                            skipped_language_ids.append(skipped_row.id)
                    except Exception as exc:
                        logger.error(
                            "DB insert failed for language-skipped job '%s': %s",
                            job.title,
                            exc,
                        )
                    continue

                filtered_jobs.append(job)
            jobs_to_evaluate = filtered_jobs

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
        jobs_stored = 0
        jobs_failed = 0
        jobs_score_parse_failed = 0
        errors: list[str] = []
        new_job_ids: list[UUID] = []

        for result in eval_results:
            if isinstance(result, Exception):
                jobs_failed += 1
                errors.append(f"Job evaluation failed: {type(result).__name__}: {result}")
                logger.error("Job evaluation failed: %s", result, exc_info=True)
            elif isinstance(result, _EvalResult):
                if result.pass1_parse_failed:
                    jobs_score_parse_failed += 1
                # All jobs now have score only (no Pass 2 evaluation)
                jobs_skipped_low_score += 1
                if result.stored:
                    jobs_stored += 1
                    new_job_ids.append(result.job_id)
                errors.extend(result.errors)

        logger.info(
            "Pipeline done: platform=%s found=%d dedup=%d blacklist=%d filter=%d closed=%d language=%d low_score=%d stored=%d failed=%d parse_failed=%d",
            platform,
            jobs_found,
            jobs_skipped_dedup,
            jobs_skipped_blacklist,
            jobs_skipped_filter,
            jobs_skipped_closed,
            jobs_skipped_language,
            jobs_skipped_low_score,
            jobs_stored,
            jobs_failed,
            jobs_score_parse_failed,
        )

        return (
            PipelineStats(
                jobs_found=jobs_found,
                jobs_skipped_dedup=jobs_skipped_dedup,
                jobs_skipped_filter=jobs_skipped_filter,
                jobs_skipped_blacklist=jobs_skipped_blacklist,
                jobs_skipped_language=jobs_skipped_language,
                jobs_skipped_closed=jobs_skipped_closed,
                jobs_skipped_low_score=jobs_skipped_low_score,
                jobs_stored=jobs_stored,
                jobs_failed=jobs_failed,
                jobs_score_parse_failed=jobs_score_parse_failed,
                errors=tuple(errors),
            ),
            new_job_ids,
            skipped_language_ids,
            skipped_closed_ids,
            platform,
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
        """Score a single job (Pass 1 only) and store the result.

        This method is designed to be called concurrently with a semaphore to limit
        the number of simultaneous evaluations. Only Pass 1 (scoring) is run during
        pipeline execution. Full evaluation (Pass 2) is deferred to on-demand requests.

        Args:
            job: The normalized job to evaluate.
            user_id: The authenticated user.
            platform: The platform slug.
            evaluator: The Evaluator instance.
            platform_context: Loaded platform context.
            semaphore: Semaphore to limit concurrency.

        Returns:
            An _EvalResult with the job_id, evaluation result (always None), stored status, and any errors.
        """
        async with semaphore:
            # Run Pass 1 only — score the job
            try:
                score, parse_failed, meta = await evaluator._call_score(job)
                logger.info(
                    "llm_call",
                    extra={
                        "pass": 1,
                        "job_title": job.title,
                        "model": meta.model,
                        "duration_ms": meta.duration_ms,
                        "input_tokens": meta.input_tokens,
                        "output_tokens": meta.output_tokens,
                    },
                )
                logger.debug("Pass 1 score=%d for job '%s'", score, job.title)
            except Exception as exc:
                logger.error(
                    "Scoring failed for '%s': %s",
                    job.title,
                    exc,
                    exc_info=True,
                )
                return _EvalResult(
                    job_id=job.id,
                    evaluation=None,
                    stored=False,
                    pass1_parse_failed=False,
                    errors=(f"Scoring failed for '{job.title}': {type(exc).__name__}: {exc}",),
                )

            # Store job with score only (evaluation=None — deferred to on-demand)
            try:
                stored = await self._job_result_repo.insert(
                    user_id=user_id,
                    platform=platform,
                    job_id=job.id,
                    title=job.title,
                    url=job.url,
                    score=score,
                    evaluation=None,
                )
                return _EvalResult(
                    job_id=stored.id if stored else job.id,
                    evaluation=None,
                    stored=stored is not None,
                    pass1_parse_failed=parse_failed,
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
                    pass1_parse_failed=parse_failed,
                    errors=(f"DB insert failed for '{job.title}': {type(exc).__name__}: {exc}",),
                )

    def _is_filtered(self, title: str, keywords: tuple[str, ...] | None = None) -> bool:
        """Return True if the job title matches any excluded keyword (case-insensitive)."""
        kw = keywords if keywords is not None else self._exclude_keywords
        title_lower = title.lower()
        return any(k in title_lower for k in kw)

    def _is_blacklisted(self, job: NormalizedJob, blacklist: tuple[str, ...]) -> bool:
        """Return True if the job's company name matches any blacklisted entry (substring, case-insensitive)."""
        if not blacklist:
            return False
        company = job.effective_company_name
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
