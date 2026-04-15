"""Upwork scraper adapter.

Calls the Apify Upwork actor and maps raw results to NormalizedJob objects.
Authentication is handled internally by the Apify actor — no user cookies needed.
"""

import asyncio
import logging
import os
import time

from apify_client import ApifyClient

from scrapers.base import BaseScraper, NormalizedJob

logger = logging.getLogger(__name__)


class UpworkScraper(BaseScraper):
    """Fetches Upwork job postings via the Apify Upwork actor.

    The actor input is passed through as-is from ``config["scraper"]["input"]``.
    Field mapping from raw Apify output to NormalizedJob is driven by
    ``config["field_mappings"]``.

    Upwork-specific extras populated into ``NormalizedJob.extras``:
    - ``client_rating``
    - ``client_location``
    - ``proposals``
    """

    platform = "upwork"

    async def fetch_jobs(self, config: dict) -> list[NormalizedJob]:
        """Run the Apify Upwork actor and return normalized job listings.

        Args:
            config: Loaded ``configs/platforms/upwork.json``.

        Returns:
            List of NormalizedJob objects.
        """
        return await asyncio.to_thread(self._fetch_jobs_sync, config)

    def _fetch_jobs_sync(self, config: dict) -> list[NormalizedJob]:
        """Synchronous implementation — runs in a thread via fetch_jobs."""
        token = os.environ["APIFY_API_TOKEN"]
        actor_id: str = config["scraper"]["actor_id"]
        actor_input: dict = config["scraper"]["input"]
        mappings: dict = config["field_mappings"]
        extras_map: dict = mappings.get("extras", {})

        client = ApifyClient(token)

        logger.info("Starting Apify actor %s for platform=upwork", actor_id)
        _MAX_APIFY_ATTEMPTS = 3
        run = None
        for _attempt in range(_MAX_APIFY_ATTEMPTS):
            try:
                run = client.actor(actor_id).call(run_input=actor_input)
                if _attempt > 0:
                    logger.info(
                        "Apify call succeeded on attempt %d/%d", _attempt + 1, _MAX_APIFY_ATTEMPTS
                    )
                break
            except Exception as exc:
                if _attempt < _MAX_APIFY_ATTEMPTS - 1:
                    _wait = 2 ** _attempt
                    logger.warning(
                        "Apify call failed (attempt %d/%d), retrying in %ds: %s",
                        _attempt + 1,
                        _MAX_APIFY_ATTEMPTS,
                        _wait,
                        exc,
                    )
                    time.sleep(_wait)
                else:
                    raise

        if run is None:
            logger.error("Apify actor run returned None for actor=%s", actor_id)
            return []

        dataset_id: str = run["defaultDatasetId"]
        raw_items = list(client.dataset(dataset_id).iterate_items())
        logger.info("Apify actor returned %d raw items", len(raw_items))

        jobs: list[NormalizedJob] = []
        for item in raw_items:
            job = self._normalize(item, mappings, extras_map)
            if job is not None:
                jobs.append(job)

        logger.info("Normalized %d/%d jobs for platform=upwork", len(jobs), len(raw_items))
        return jobs

    def _normalize(
        self,
        item: dict,
        mappings: dict,
        extras_map: dict,
    ) -> NormalizedJob | None:
        """Map a single raw Apify item to a NormalizedJob.

        Returns None if required fields (id, title, description, url) are missing.
        """
        job_id = _get(item, mappings["id"])
        title = _get(item, mappings["title"])
        description = _get(item, mappings["description"])
        url = _get(item, mappings["url"])

        if not all([job_id, title, description, url]):
            logger.debug(
                "Skipping item missing required fields: id=%s title=%s url=%s",
                job_id,
                title,
                url,
            )
            return None

        skills_raw = _get(item, mappings.get("skills", "skills"))
        skills: list[str] | None = None
        if isinstance(skills_raw, list):
            skills = [str(s) for s in skills_raw if s]
        elif isinstance(skills_raw, str) and skills_raw:
            skills = [skills_raw]

        budget_raw = _get(item, mappings.get("budget", "budget"))
        budget = str(budget_raw) if budget_raw is not None else None

        extras: dict = {}
        for extra_key, raw_key in extras_map.items():
            value = _get(item, raw_key)
            if value is not None:
                extras[extra_key] = value

        return NormalizedJob(
            id=str(job_id),
            platform=self.platform,
            title=str(title),
            description=str(description),
            url=str(url),
            skills=skills,
            budget=budget,
            job_type=_str_or_none(_get(item, mappings.get("job_type", "jobType"))),
            experience_level=_str_or_none(
                _get(item, mappings.get("experience_level", "experienceLevel"))
            ),
            extras=extras,
        )


def _get(item: dict, key: str) -> object:
    """Return ``item[key]``, or None if the key is absent."""
    return item.get(key)


def _str_or_none(value: object) -> str | None:
    """Return str(value) if value is truthy, else None."""
    return str(value) if value else None
