"""CompanyBlacklistService — validation and business logic for company blacklist."""

import logging
from uuid import UUID

from repositories.company_blacklist import CompanyBlacklistEntry, CompanyBlacklistRepository

logger = logging.getLogger(__name__)

_MAX_ENTRIES = 500
_MIN_NAME_LEN = 3
_MAX_NAME_LEN = 200


class CompanyBlacklistError(Exception):
    """Raised for expected blacklist validation or state failures."""


class CompanyBlacklistService:
    def __init__(self, repo: CompanyBlacklistRepository) -> None:
        self._repo = repo

    async def list(self, user_id: UUID) -> list[CompanyBlacklistEntry]:
        """Return all blacklist entries for the user."""
        return await self._repo.find_by_user_id(user_id)

    async def add(self, user_id: UUID, name: str) -> CompanyBlacklistEntry:
        """Validate and add a company to the user's blacklist."""
        name = name.strip()
        if not name:
            raise CompanyBlacklistError("Name cannot be empty")
        if len(name) < _MIN_NAME_LEN:
            raise CompanyBlacklistError("Name must be at least 3 characters")
        if len(name) > _MAX_NAME_LEN:
            raise CompanyBlacklistError("Name must be at most 200 characters")

        entries = await self._repo.find_by_user_id(user_id)
        if len(entries) >= _MAX_ENTRIES:
            raise CompanyBlacklistError("Blacklist limit reached (500)")

        entry = await self._repo.insert(user_id, name)
        if entry is None:
            raise CompanyBlacklistError("Company already blacklisted")

        logger.info("Added blacklist entry user_id=%s name=%s", user_id, name)
        return entry

    async def remove(self, user_id: UUID, entry_id: UUID) -> None:
        """Remove a blacklist entry; raises CompanyBlacklistError if not found."""
        deleted = await self._repo.delete(user_id, entry_id)
        if not deleted:
            raise CompanyBlacklistError("Entry not found")
        logger.info("Removed blacklist entry id=%s user_id=%s", entry_id, user_id)
