"""Google Sheets output — batch-appends evaluated job rows.

Uses gspread with a service account. Each platform writes to its own named
worksheet. The column order is defined in ``config["sheet"]["columns"]`` for
each platform config.
"""

import logging

import gspread
from gspread.exceptions import WorksheetNotFound
from google.oauth2.service_account import Credentials

from core.evaluator import EvaluationResult
from scrapers.base import NormalizedJob

logger = logging.getLogger(__name__)

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Maps column name strings (from platform config) to their data source.
# Values are resolved against a flat dict built from job + result fields.
_RESULT_FIELDS = {"relevancy_score", "evaluation", "recommendation", "flags", "summary", "scratchpad"}
_JOB_FIELDS = {"title", "description", "budget", "url", "job_type", "experience_level", "platform"}


class SheetsClient:
    """Appends evaluated job rows to a Google Sheets spreadsheet.

    Args:
        spreadsheet_id: The Google Sheets document ID.
        service_account_path: Path to the service account JSON key file.
    """

    def __init__(self, spreadsheet_id: str, service_account_path: str) -> None:
        creds = Credentials.from_service_account_file(service_account_path, scopes=_SCOPES)
        self._gc = gspread.authorize(creds)
        self._spreadsheet = self._gc.open_by_key(spreadsheet_id)
        logger.info("SheetsClient connected to spreadsheet %s", spreadsheet_id)

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
        sheet_cfg = platform_config["sheet"]
        worksheet = self._get_or_create_worksheet(sheet_cfg["worksheet_name"])
        columns: list[str] = sheet_cfg["columns"]
        row = self._build_row(job, result, columns)
        worksheet.append_row(row, value_input_option="RAW")
        logger.debug("Appended row for job %s to worksheet '%s'", job.id, sheet_cfg["worksheet_name"])

    def _get_or_create_worksheet(self, name: str) -> gspread.Worksheet:
        """Return the named worksheet, creating it if absent."""
        try:
            return self._spreadsheet.worksheet(name)
        except WorksheetNotFound:
            logger.info("Worksheet '%s' not found — creating it", name)
            return self._spreadsheet.add_worksheet(title=name, rows=1000, cols=20)

    def _build_row(
        self,
        job: NormalizedJob,
        result: EvaluationResult,
        columns: list[str],
    ) -> list[str]:
        """Build an ordered row list from job + result fields per column spec.

        Resolution order for each column name:
        1. EvaluationResult fields (relevancy_score, evaluation, etc.)
        2. NormalizedJob standard fields (title, budget, url, etc.)
        3. NormalizedJob.extras (client_rating, client_location, proposals, etc.)
        4. NormalizedJob.skills joined as comma-separated string
        5. Empty string if not found
        """
        flat: dict[str, str] = {}

        # EvaluationResult fields
        for field in _RESULT_FIELDS:
            flat[field] = str(getattr(result, field, "") or "")

        # NormalizedJob standard fields
        for field in _JOB_FIELDS:
            value = getattr(job, field, None)
            flat[field] = str(value) if value is not None else ""

        # skills as comma-separated string
        flat["skills"] = ", ".join(job.skills) if job.skills else ""

        # NormalizedJob.extras (platform-specific, e.g. client_rating)
        for key, value in job.extras.items():
            flat[key] = str(value) if value is not None else ""

        return [flat.get(col, "") for col in columns]
