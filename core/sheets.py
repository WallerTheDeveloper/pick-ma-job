"""Google Sheets output — batch-appends evaluated job rows.

Uses gspread with a service account. Each platform writes to its own named
worksheet. The column order is defined in ``config["sheet"]["columns"]`` for
each platform config.
"""

import logging

from core.evaluator import EvaluationResult
from scrapers.base import NormalizedJob

logger = logging.getLogger(__name__)


class SheetsClient:
    """Appends evaluated job rows to a Google Sheets spreadsheet.

    Args:
        spreadsheet_id: The Google Sheets document ID.
        service_account_path: Path to the service account JSON key file.
    """

    def __init__(self, spreadsheet_id: str, service_account_path: str) -> None:
        ...

    def append_row(
        self,
        job: NormalizedJob,
        result: EvaluationResult,
        platform_config: dict,
    ) -> None:
        """Append a single evaluated job row to the platform's worksheet.

        Column order is determined by ``platform_config["sheet"]["columns"]``.
        The worksheet is created automatically if it doesn't exist.

        Args:
            job: The normalized job.
            result: The Claude evaluation result.
            platform_config: The loaded platform config dict.
        """
        ...

    def _get_or_create_worksheet(self, name: str):
        """Return the named worksheet, creating it if absent."""
        ...

    def _build_row(
        self,
        job: NormalizedJob,
        result: EvaluationResult,
        columns: list[str],
    ) -> list[str]:
        """Build an ordered row list from job + result fields per column spec."""
        ...
