"""Unit tests for core.sheets.SheetsClient.

gspread and google-auth are mocked throughout — no network calls, no credentials needed.
"""

from unittest.mock import MagicMock, patch, call

import pytest
from gspread.exceptions import WorksheetNotFound

from core.evaluator import EvaluationResult
from core.sheets import SheetsClient
from scrapers.base import NormalizedJob

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SPREADSHEET_ID = "sheet-abc-123"
SERVICE_ACCOUNT_PATH = "/fake/service_account.json"

UPWORK_PLATFORM_CONFIG = {
    "sheet": {
        "worksheet_name": "Upwork",
        "columns": [
            "relevancy_score",
            "title",
            "budget",
            "summary",
            "recommendation",
            "evaluation",
            "flags",
            "skills",
            "client_rating",
            "client_location",
            "url",
        ],
    }
}

FULL_JOB = NormalizedJob(
    id="job-001",
    platform="upwork",
    title="Unity AR Developer",
    description="Build AR app.",
    url="https://upwork.com/jobs/job-001",
    budget="$2,000 fixed",
    job_type="Fixed",
    experience_level="Intermediate",
    skills=["Unity", "AR Foundation", "C#"],
    extras={
        "client_rating": "4.9",
        "client_location": "United States",
        "proposals": "5",
    },
)

FULL_RESULT = EvaluationResult({
    "scratchpad": "Checking skills...",
    "evaluation": "Strong Unity AR match.",
    "relevancy_score": 8,
    "recommendation": "Yes apply — strong match",
    "flags": "Verified client, clear scope",
    "summary": "Great AR fit.",
})


def _make_sheets_client(mock_spreadsheet: MagicMock) -> SheetsClient:
    """Construct a SheetsClient with gspread and google-auth fully mocked."""
    with patch("core.sheets.Credentials.from_service_account_file"):
        with patch("core.sheets.gspread.authorize", return_value=MagicMock()) as mock_auth:
            mock_auth.return_value.open_by_key.return_value = mock_spreadsheet
            return SheetsClient(SPREADSHEET_ID, SERVICE_ACCOUNT_PATH)


# ---------------------------------------------------------------------------
# __init__
# ---------------------------------------------------------------------------


def test_init_opens_spreadsheet_by_key():
    mock_gc = MagicMock()
    with patch("core.sheets.Credentials.from_service_account_file"):
        with patch("core.sheets.gspread.authorize", return_value=mock_gc):
            SheetsClient(SPREADSHEET_ID, SERVICE_ACCOUNT_PATH)

    mock_gc.open_by_key.assert_called_once_with(SPREADSHEET_ID)


def test_init_loads_credentials_from_path():
    with patch("core.sheets.Credentials.from_service_account_file") as mock_creds:
        with patch("core.sheets.gspread.authorize", return_value=MagicMock()):
            SheetsClient(SPREADSHEET_ID, SERVICE_ACCOUNT_PATH)

    mock_creds.assert_called_once_with(SERVICE_ACCOUNT_PATH, scopes=pytest.approx(mock_creds.call_args.kwargs["scopes"]))
    assert mock_creds.called


# ---------------------------------------------------------------------------
# _get_or_create_worksheet
# ---------------------------------------------------------------------------


def test_get_or_create_returns_existing_worksheet():
    mock_ws = MagicMock()
    mock_spreadsheet = MagicMock()
    mock_spreadsheet.worksheet.return_value = mock_ws

    client = _make_sheets_client(mock_spreadsheet)
    result = client._get_or_create_worksheet("Upwork")

    assert result is mock_ws
    mock_spreadsheet.worksheet.assert_called_once_with("Upwork")
    mock_spreadsheet.add_worksheet.assert_not_called()


def test_get_or_create_creates_worksheet_when_not_found():
    mock_new_ws = MagicMock()
    mock_spreadsheet = MagicMock()
    mock_spreadsheet.worksheet.side_effect = WorksheetNotFound
    mock_spreadsheet.add_worksheet.return_value = mock_new_ws

    client = _make_sheets_client(mock_spreadsheet)
    result = client._get_or_create_worksheet("LinkedIn")

    assert result is mock_new_ws
    mock_spreadsheet.add_worksheet.assert_called_once_with(title="LinkedIn", rows=1000, cols=20)


# ---------------------------------------------------------------------------
# _build_row
# ---------------------------------------------------------------------------


def test_build_row_result_fields_correct():
    client = _make_sheets_client(MagicMock())
    columns = ["relevancy_score", "summary", "recommendation", "evaluation", "flags"]
    row = client._build_row(FULL_JOB, FULL_RESULT, columns)

    assert row[0] == "8"
    assert row[1] == "Great AR fit."
    assert row[2] == "Yes apply — strong match"
    assert row[3] == "Strong Unity AR match."
    assert row[4] == "Verified client, clear scope"


def test_build_row_job_standard_fields_correct():
    client = _make_sheets_client(MagicMock())
    columns = ["title", "budget", "url", "job_type", "experience_level", "platform"]
    row = client._build_row(FULL_JOB, FULL_RESULT, columns)

    assert row[0] == "Unity AR Developer"
    assert row[1] == "$2,000 fixed"
    assert row[2] == "https://upwork.com/jobs/job-001"
    assert row[3] == "Fixed"
    assert row[4] == "Intermediate"
    assert row[5] == "upwork"


def test_build_row_extras_fields_correct():
    client = _make_sheets_client(MagicMock())
    columns = ["client_rating", "client_location", "proposals"]
    row = client._build_row(FULL_JOB, FULL_RESULT, columns)

    assert row[0] == "4.9"
    assert row[1] == "United States"
    assert row[2] == "5"


def test_build_row_skills_joined_as_csv():
    client = _make_sheets_client(MagicMock())
    row = client._build_row(FULL_JOB, FULL_RESULT, ["skills"])

    assert row[0] == "Unity, AR Foundation, C#"


def test_build_row_skills_none_gives_empty_string():
    job = NormalizedJob(
        id="j", platform="upwork", title="T", description="D", url="U", skills=None
    )
    client = _make_sheets_client(MagicMock())
    row = client._build_row(job, FULL_RESULT, ["skills"])

    assert row[0] == ""


def test_build_row_unknown_column_gives_empty_string():
    client = _make_sheets_client(MagicMock())
    row = client._build_row(FULL_JOB, FULL_RESULT, ["nonexistent_column"])

    assert row[0] == ""


def test_build_row_full_upwork_column_order():
    client = _make_sheets_client(MagicMock())
    columns = UPWORK_PLATFORM_CONFIG["sheet"]["columns"]
    row = client._build_row(FULL_JOB, FULL_RESULT, columns)

    assert len(row) == len(columns)
    assert row[0] == "8"            # relevancy_score
    assert row[1] == "Unity AR Developer"  # title
    assert row[2] == "$2,000 fixed"  # budget
    assert row[10] == "https://upwork.com/jobs/job-001"  # url


def test_build_row_none_job_fields_become_empty_string():
    job = NormalizedJob(
        id="j", platform="upwork", title="T", description="D", url="U",
        budget=None, job_type=None, experience_level=None,
    )
    client = _make_sheets_client(MagicMock())
    row = client._build_row(job, FULL_RESULT, ["budget", "job_type", "experience_level"])

    assert row == ["", "", ""]


# ---------------------------------------------------------------------------
# append_row
# ---------------------------------------------------------------------------


def test_append_row_calls_worksheet_append():
    mock_ws = MagicMock()
    mock_spreadsheet = MagicMock()
    mock_spreadsheet.worksheet.return_value = mock_ws

    client = _make_sheets_client(mock_spreadsheet)
    client.append_row(FULL_JOB, FULL_RESULT, UPWORK_PLATFORM_CONFIG)

    mock_ws.append_row.assert_called_once()
    args = mock_ws.append_row.call_args
    row = args[0][0]
    assert isinstance(row, list)
    assert len(row) == len(UPWORK_PLATFORM_CONFIG["sheet"]["columns"])


def test_append_row_uses_raw_value_input_option():
    mock_ws = MagicMock()
    mock_spreadsheet = MagicMock()
    mock_spreadsheet.worksheet.return_value = mock_ws

    client = _make_sheets_client(mock_spreadsheet)
    client.append_row(FULL_JOB, FULL_RESULT, UPWORK_PLATFORM_CONFIG)

    call_kwargs = mock_ws.append_row.call_args.kwargs
    assert call_kwargs.get("value_input_option") == "RAW"


def test_append_row_creates_worksheet_if_missing():
    mock_ws = MagicMock()
    mock_spreadsheet = MagicMock()
    mock_spreadsheet.worksheet.side_effect = WorksheetNotFound
    mock_spreadsheet.add_worksheet.return_value = mock_ws

    client = _make_sheets_client(mock_spreadsheet)
    client.append_row(FULL_JOB, FULL_RESULT, UPWORK_PLATFORM_CONFIG)

    mock_spreadsheet.add_worksheet.assert_called_once()
    mock_ws.append_row.assert_called_once()
