"""LinkedIn scraper adapter.

Calls the Apify LinkedIn Jobs actor and maps raw results to NormalizedJob objects.
"""

import logging

from scrapers.base import BaseScraper, NormalizedJob

logger = logging.getLogger(__name__)


class LinkedInScraper(BaseScraper):
    """Fetches LinkedIn job postings via the Apify LinkedIn Jobs actor.

    The actor input is passed through as-is from ``config["scraper"]["input"]``.
    Field mapping from raw Apify output to NormalizedJob is driven by
    ``config["field_mappings"]``.

    LinkedIn-specific extras populated into ``NormalizedJob.extras``:
    - ``company_name``
    - ``company_size``
    """

    platform = "linkedin"

    async def fetch_jobs(self, config: dict) -> list[NormalizedJob]:
        """Run the Apify LinkedIn Jobs actor and return normalized job listings.

        Args:
            config: Loaded ``configs/platforms/linkedin.json``.

        Returns:
            List of NormalizedJob objects.
        """
        ...
