"""Abstract base scraper and NormalizedJob data model.

All platform adapters must inherit from BaseScraper and return NormalizedJob objects.
This is the universal internal format that the rest of the pipeline works with.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class NormalizedJob:
    """Universal job representation produced by every scraper adapter.

    The ``extras`` dict carries platform-specific fields that don't map to the
    standard fields above (e.g. ``client_rating`` for Upwork, ``company_size``
    for LinkedIn). These are interpolated into the platform's
    ``user_message_template`` at evaluation time.
    """

    id: str
    platform: str
    title: str
    description: str
    url: str
    skills: list[str] | None = None
    budget: str | None = None
    job_type: str | None = None
    experience_level: str | None = None
    extras: dict = field(default_factory=dict)


class BaseScraper(ABC):
    """Abstract base class for all platform scraper adapters.

    To add a new platform:
    1. Create ``scrapers/<platform>.py`` and subclass ``BaseScraper``.
    2. Set the ``platform`` class attribute to the platform's slug.
    3. Implement ``fetch_jobs`` to call the Apify actor and return
       a list of ``NormalizedJob`` objects.
    4. Add matching JSON files in ``configs/platforms/`` and
       ``configs/prompts/``.
    """

    platform: str

    @abstractmethod
    async def fetch_jobs(self, config: dict) -> list[NormalizedJob]:
        """Fetch jobs from the platform and return normalized results.

        Args:
            config: The platform config dict loaded from
                    ``configs/platforms/<platform>.json``.

        Returns:
            A list of ``NormalizedJob`` instances ready for dedup + evaluation.
        """
        ...
