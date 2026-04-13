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
from pathlib import Path
from uuid import UUID

from core.evaluator import Evaluator
from core.prompt_adapter import load_platform_context, profile_row_to_prompt_dict
from repositories.job_result import JobResultRepository
from repositories.profile import ProfileRepository
from repositories.search_config import SearchConfigRepository, SearchConfigRow
from scrapers.registry import get_scraper, list_platforms

logger = logging.getLogger(__name__)

_PLATFORMS_DIR = Path(__file__).parent.parent / "configs" / "platforms"
_SETTINGS_PATH = Path(__file__).parent.parent / "configs" / "settings.json"


class PipelineError(Exception):
    """Raised for expected pipeline failures (missing profile, bad config, etc.)."""


@dataclass(frozen=True)
class PlatformResult:
    """Immutable result from running the pipeline on a single platform."""

    jobs_found: int
    jobs_skipped_dedup: int
    jobs_skipped_filter: int
    jobs_skipped_low_score: int
    jobs_evaluated: int
    jobs_stored: int
    errors: tuple[str, ...]


@dataclass(frozen=True)
class PipelineRunResult:
    """Immutable summary of a completed pipeline run."""

    jobs_found: int
    jobs_skipped_dedup: int
    jobs_skipped_filter: int
    jobs_skipped_low_score: int
    jobs_evaluated: int
    jobs_stored: int
    errors: tuple[str, ...]


class PipelineService:
    """Orchestrates the scrape → dedup → filter → evaluate → store pipeline.

    Args:
        profile_repo: Repository for loading user profiles.
        search_config_repo: Repository for loading user search configs.
        job_result_repo: Repository for dedup checks and result storage.
        anthropic_api_key: API key passed to the Evaluator.
    """

    def __init__(
        self,
        profile_repo: ProfileRepository,
        search_config_repo: SearchConfigRepository,
        job_result_repo: JobResultRepository,
        anthropic_api_key: str,
    ) -> None:
        self._profile_repo = profile_repo
        self._search_config_repo = search_config_repo
        self._job_result_repo = job_result_repo
        self._anthropic_api_key = anthropic_api_key
        settings = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        self._settings = settings
        self._exclude_keywords: tuple[str, ...] = tuple(
            kw.lower()
            for kw in settings.get("pre_filters", {}).get("exclude_title_keywords", [])
        )

    async def run_pipeline(
        self,
        user_id: UUID,
        platforms: list[str] | None = None,
    ) -> PipelineRunResult:
        """Run the full pipeline for a user on one or all configured platforms.

        Args:
            user_id: The authenticated user.
            platforms: If given, only run these platforms. None means run all
                configured platforms.

        Returns:
            A ``PipelineRunResult`` summarising counts and any non-fatal errors.

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
        evaluator = Evaluator(prompt_dict, self._settings, api_key=self._anthropic_api_key)

        platform_results = [
            await self._run_platform(
                user_id=user_id,
                config_row=config_row,
                evaluator=evaluator,
            )
            for config_row in search_configs
        ]

        return PipelineRunResult(
            jobs_found=sum(r.jobs_found for r in platform_results),
            jobs_skipped_dedup=sum(r.jobs_skipped_dedup for r in platform_results),
            jobs_skipped_filter=sum(r.jobs_skipped_filter for r in platform_results),
            jobs_skipped_low_score=sum(r.jobs_skipped_low_score for r in platform_results),
            jobs_evaluated=sum(r.jobs_evaluated for r in platform_results),
            jobs_stored=sum(r.jobs_stored for r in platform_results),
            errors=tuple(e for r in platform_results for e in r.errors),
        )

    async def _run_platform(
        self,
        user_id: UUID,
        config_row: SearchConfigRow,
        evaluator: Evaluator,
    ) -> PlatformResult:
        platform = config_row.platform
        logger.info("Pipeline starting: user_id=%s platform=%s", user_id, platform)

        platform_config_path = _PLATFORMS_DIR / f"{platform}.json"
        if not platform_config_path.exists():
            msg = f"No platform config file for '{platform}'"
            logger.warning("%s — skipping.", msg)
            return PlatformResult(0, 0, 0, 0, 0, 0, (msg,))

        static_config = json.loads(platform_config_path.read_text(encoding="utf-8"))
        merged_config = _merge_config(static_config, config_row)

        try:
            platform_context = load_platform_context(platform)
        except FileNotFoundError:
            msg = f"No platform context file for '{platform}'"
            logger.warning("%s — skipping.", msg)
            return PlatformResult(0, 0, 0, 0, 0, 0, (msg,))

        scraper = get_scraper(platform)
        try:
            jobs = await scraper.fetch_jobs(merged_config)
        except Exception as exc:
            msg = f"Scraper failed for '{platform}': {exc}"
            logger.error(msg)
            return PlatformResult(0, 0, 0, 0, 0, 0, (msg,))

        jobs_found = len(jobs)
        logger.info("Fetched %d jobs from platform=%s", jobs_found, platform)

        jobs_skipped_dedup = 0
        jobs_skipped_filter = 0
        jobs_skipped_low_score = 0
        jobs_evaluated = 0
        jobs_stored = 0
        errors: list[str] = []

        for job in jobs:
            already_seen = await self._job_result_repo.exists(user_id, platform, job.id)
            if already_seen:
                jobs_skipped_dedup += 1
                continue

            if self._is_filtered(job.title):
                logger.debug("Pre-filter skipped: '%s'", job.title)
                jobs_skipped_filter += 1
                continue

            try:
                result = await evaluator.evaluate(job, platform_context)
            except Exception as exc:
                msg = f"Evaluation failed for '{job.title}': {exc}"
                logger.error(msg)
                errors.append(msg)
                continue

            if result.evaluation is None:
                jobs_skipped_low_score += 1
            else:
                jobs_evaluated += 1

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
                if stored is not None:
                    jobs_stored += 1
            except Exception as exc:
                msg = f"DB insert failed for '{job.title}': {exc}"
                logger.error(msg)
                errors.append(msg)

        logger.info(
            "Pipeline done: platform=%s found=%d dedup=%d filter=%d low_score=%d evaluated=%d stored=%d",
            platform,
            jobs_found,
            jobs_skipped_dedup,
            jobs_skipped_filter,
            jobs_skipped_low_score,
            jobs_evaluated,
            jobs_stored,
        )

        return PlatformResult(
            jobs_found=jobs_found,
            jobs_skipped_dedup=jobs_skipped_dedup,
            jobs_skipped_filter=jobs_skipped_filter,
            jobs_skipped_low_score=jobs_skipped_low_score,
            jobs_evaluated=jobs_evaluated,
            jobs_stored=jobs_stored,
            errors=tuple(errors),
        )

    def _is_filtered(self, title: str) -> bool:
        """Return True if the job title matches any excluded keyword (case-insensitive)."""
        title_lower = title.lower()
        return any(kw in title_lower for kw in self._exclude_keywords)


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
