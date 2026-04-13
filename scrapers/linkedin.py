"""LinkedIn scraper adapter.

Calls the Apify LinkedIn Jobs actor and maps raw results to NormalizedJob objects.
Authentication is handled internally by the Apify actor — no user cookies needed.
"""

import asyncio
import logging
import os

from apify_client import ApifyClient

from scrapers.base import BaseScraper, NormalizedJob

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    """Fetches LinkedIn job postings via the Apify LinkedIn Jobs actor.

    The actor input is passed through as-is from ``config["scraper"]["input"]``.
    Field mapping from raw Apify output to NormalizedJob is driven by
    ``config["field_mappings"]``.

    LinkedIn-specific extras populated into ``NormalizedJob.extras``:
    - ``company_name``
    - ``location``
    - ``work_type``
    - ``sector``
    - ``applications_count``
    - ``apply_type``
    - ``posted_time``
    - ``poster_name``
    - ``company_url``
    """

    platform = "linkedin"

    async def fetch_jobs(self, config: dict) -> list[NormalizedJob]:
        """Run the Apify LinkedIn Jobs actor and return normalized job listings.

        Args:
            config: Loaded ``configs/platforms/linkedin.json``.

        Returns:
            List of NormalizedJob objects.
        """
        return await asyncio.to_thread(self._fetch_jobs_sync, config)

    def _fetch_jobs_sync(self, config: dict) -> list[NormalizedJob]:
        """Synchronous implementation — runs in a thread via fetch_jobs."""
        token = os.environ["APIFY_API_TOKEN"]
        actor_id: str = config["scraper"]["actor_id"]
        actor_input: dict = dict(config["scraper"]["input"])
        mappings: dict = config["field_mappings"]

        # Map searchTerms (list) → keyword (string) as required by the Apify actor.
        # The form stores keywords as searchTerms; the actor only accepts 'keyword' or 'startUrls'.
        if "searchTerms" in actor_input:
            terms = actor_input.pop("searchTerms")
            if isinstance(terms, list) and terms:
                actor_input.setdefault("keyword", [str(t) for t in terms])

        # Remove the 'query' display label injected by _merge_config — not an actor field.
        actor_input.pop("query", None)

        # Fail fast if neither keyword nor startUrls is present.
        if "keyword" not in actor_input and "startUrls" not in actor_input:
            raise ValueError(
                "LinkedIn actor input requires 'keyword' or 'startUrls'. "
                "Add at least one keyword to your LinkedIn search config."
            )

        # Map experienceLevel values to the actor's expected format.
        _EXPERIENCE_LEVEL_MAP = {
            "internship": "internship",
            "entry_level": "entry-level",
            "associate": "associate",
            "mid_senior_level": "mid-senior",
            "director": "director",
            # "executive" has no equivalent in the actor's allowed values — drop it.
        }
        if "experienceLevel" in actor_input:
            original = actor_input["experienceLevel"]
            mapped = [_EXPERIENCE_LEVEL_MAP[v] for v in original if v in _EXPERIENCE_LEVEL_MAP]
            dropped = [v for v in original if v not in _EXPERIENCE_LEVEL_MAP]
            if dropped:
                logger.warning(
                    "Dropped unsupported LinkedIn experienceLevel values %s", dropped
                )
            actor_input["experienceLevel"] = mapped

        # Sanitize jobType: the Apify actor only accepts these exact values.
        _VALID_JOB_TYPES = frozenset(
            {"full-time", "part-time", "contract", "temporary", "internship"}
        )
        if "jobType" in actor_input:
            original = actor_input["jobType"]
            valid = [v for v in original if v in _VALID_JOB_TYPES]
            if len(valid) != len(original):
                invalid = [v for v in original if v not in _VALID_JOB_TYPES]
                logger.warning(
                    "Removed invalid LinkedIn jobType values %s; keeping %s",
                    invalid,
                    valid,
                )
            actor_input["jobType"] = valid

        # Sanitize maxItems: the Apify actor requires a minimum of 150.
        if "maxItems" in actor_input:
            try:
                max_items = int(actor_input["maxItems"])
                if max_items < 150:
                    logger.warning(
                        "LinkedIn maxItems %d is below minimum 150; clamping to 150.", max_items
                    )
                    actor_input["maxItems"] = 150
            except (TypeError, ValueError):
                logger.warning("Invalid LinkedIn maxItems value %r; removing.", actor_input["maxItems"])
                del actor_input["maxItems"]

        # Sanitize salaryBase: must be one of the allowed string values.
        _VALID_SALARY_BASE = frozenset({"", "40000", "60000", "80000", "100000", "120000"})
        if "salaryBase" in actor_input:
            value = str(actor_input["salaryBase"]) if not isinstance(actor_input["salaryBase"], str) else actor_input["salaryBase"]
            if value not in _VALID_SALARY_BASE:
                logger.warning(
                    "Removed invalid LinkedIn salaryBase value %r (not in allowed set)",
                    actor_input["salaryBase"],
                )
                del actor_input["salaryBase"]
            else:
                actor_input["salaryBase"] = value

        extras_map: dict = mappings.get("extras", {})

        client = ApifyClient(token)

        logger.info("Starting Apify actor %s for platform=linkedin", actor_id)
        run = client.actor(actor_id).call(run_input=actor_input)

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

        logger.info("Normalized %d/%d jobs for platform=linkedin", len(jobs), len(raw_items))
        return jobs

    def _normalize(
        self,
        item: dict,
        mappings: dict,
        extras_map: dict,
    ) -> NormalizedJob | None:
        """Map a single raw Apify item to a NormalizedJob.

        Returns None if required fields (id, title, description, url) are missing.
        Budget is derived from ``salaryInfo`` — a list of salary strings joined as
        "$X – $Y", or None if the list is empty or absent.
        Skills are always None — the LinkedIn actor does not provide them.
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

        # Skills are not provided by the LinkedIn actor.
        skills: list[str] | None = None

        # Budget comes from salaryInfo — a list that may contain 0, 1, or 2 entries.
        salary_key = mappings.get("budget")
        budget: str | None = None
        if salary_key:
            budget = _normalize_salary(_get(item, salary_key))

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
            job_type=_str_or_none(_get(item, mappings.get("job_type", "contractType"))),
            experience_level=_str_or_none(
                _get(item, mappings.get("experience_level", "experienceLevel"))
            ),
            extras=extras,
        )


def _normalize_salary(salary_info: object) -> str | None:
    """Convert a salaryInfo list to a "$X – $Y" string, or None if absent/empty.

    Args:
        salary_info: The raw salaryInfo value from the Apify response.
            Expected to be a list of strings like ``["$50/hr", "$80/hr"]``.

    Returns:
        A formatted salary range string, a single salary string, or None.
    """
    if not isinstance(salary_info, list):
        return None
    parts = [str(s) for s in salary_info if s]
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} – {parts[1]}"


def _get(item: dict, key: str) -> object:
    """Return ``item[key]``, or None if the key is absent."""
    return item.get(key)


def _str_or_none(value: object) -> str | None:
    """Return str(value) if value is truthy, else None."""
    return str(value) if value else None
