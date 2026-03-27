"""Upwork scraper adapter.

Calls the Apify Upwork actor and maps raw results to NormalizedJob objects.
Authentication is handled internally by the Apify actor — no user cookies needed.
"""

import logging

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
        ...
