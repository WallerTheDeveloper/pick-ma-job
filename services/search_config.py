"""SearchConfigService — search configuration business logic."""

import logging
from dataclasses import dataclass, field
from uuid import UUID

from repositories.search_config import SearchConfigRepository, SearchConfigRow
from scrapers.registry import list_platforms

logger = logging.getLogger(__name__)

KNOWN_PLATFORMS: frozenset[str] = frozenset(list_platforms())


class SearchConfigError(Exception):
    """Raised for expected search config validation failures."""


@dataclass(frozen=True)
class SearchConfigData:
    """Validated payload used for create/update operations."""

    platform: str
    query: str | None
    filters: dict = field(default_factory=dict)


class SearchConfigService:
    def __init__(self, search_config_repo: SearchConfigRepository) -> None:
        self._repo = search_config_repo

    async def get_all(self, user_id: UUID) -> list[SearchConfigRow]:
        """Return all search configs for a user."""
        return await self._repo.find_by_user_id(user_id)

    async def get_by_platform(self, user_id: UUID, platform: str) -> list[SearchConfigRow]:
        """Return all configs for a specific platform."""
        return await self._repo.find_by_user_and_platform(user_id, platform)

    async def create(self, user_id: UUID, data: SearchConfigData) -> SearchConfigRow:
        """Validate and create a search config. Raises SearchConfigError on invalid input."""
        _validate(data)
        row = await self._repo.create(
            user_id=user_id,
            platform=data.platform,
            query=data.query or None,
            filters=data.filters,
        )
        logger.info("Search config created user_id=%s platform=%s", user_id, data.platform)
        return row

    async def delete(self, config_id: UUID, user_id: UUID) -> bool:
        """Delete a search config by id, scoped to user_id. Returns True if deleted."""
        deleted = await self._repo.delete(config_id, user_id)
        if deleted:
            logger.info("Search config deleted id=%s user_id=%s", config_id, user_id)
        return deleted


def _validate(data: SearchConfigData) -> None:
    """Raise SearchConfigError if the data fails basic validation."""
    if data.platform not in KNOWN_PLATFORMS:
        raise SearchConfigError(
            f"Unknown platform {data.platform!r}. Known platforms: {sorted(KNOWN_PLATFORMS)}"
        )
    if not isinstance(data.filters, dict):
        raise SearchConfigError("Filters must be a JSON object.")
