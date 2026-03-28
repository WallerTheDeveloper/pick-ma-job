"""Scraper registry — auto-discovers and resolves platform adapters by name.

Adding a new platform requires only:
1. A scraper class with ``platform = "<name>"`` in ``scrapers/<name>.py``.
2. Importing it in the ``_SCRAPERS`` registry below.

No changes to orchestration or core logic are needed.
"""

import logging

from scrapers.base import BaseScraper
from scrapers.linkedin import LinkedInScraper
from scrapers.upwork import UpworkScraper

logger = logging.getLogger(__name__)

_SCRAPERS: dict[str, type[BaseScraper]] = {
    UpworkScraper.platform: UpworkScraper,
    LinkedInScraper.platform: LinkedInScraper,
}


def get_scraper(platform: str) -> BaseScraper:
    """Return an instantiated scraper for the given platform slug.

    Args:
        platform: The platform name (e.g. ``"upwork"``, ``"linkedin"``).

    Returns:
        An instantiated ``BaseScraper`` subclass.

    Raises:
        ValueError: If no scraper is registered for the given platform.
    """
    cls = _SCRAPERS.get(platform)
    if cls is None:
        raise ValueError(f"No scraper registered for platform: {platform!r}. Known: {list(_SCRAPERS)}")
    return cls()


def list_platforms() -> list[str]:
    """Return all registered platform slugs."""
    return list(_SCRAPERS.keys())
