"""Unit tests for scrapers.upwork.UpworkScraper.

Apify is mocked — no network calls, no credits consumed.
Raw item fixtures match the actual Apify Upwork actor output schema.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from scrapers.upwork import UpworkScraper

# ---------------------------------------------------------------------------
# Config fixture — mirrors configs/platforms/upwork.json field_mappings
# ---------------------------------------------------------------------------

UPWORK_CONFIG = {
    "scraper": {
        "actor_id": "apify/upwork-scraper",
        "input": {"query": "unity developer"},
    },
    "field_mappings": {
        "id": "id",
        "title": "title",
        "description": "description",
        "url": "url",
        "skills": "tags",
        "budget": "budget",
        "job_type": "jobType",
        "experience_level": "experienceLevel",
        "extras": {
            "client_rating": "clientRating",
            "client_location": "clientLocation",
            "proposals": "proposals",
        },
    },
}

# Realistic raw item matching the Apify actor output schema
FULL_RAW_ITEM = {
    "id": "~01234567890abcdef0",
    "subId": "1234567890",
    "title": "Unity AR Developer — Indoor Navigation App",
    "description": "Build an AR indoor navigation app using AR Foundation and ARCore.",
    "url": "https://www.upwork.com/jobs/~01234567890abcdef0",
    "budget": "$2,000",
    "relativeDate": "Posted 2 hours ago",
    "absoluteDate": "2026-03-27T10:00:00Z",
    "jobType": "Fixed",
    "experienceLevel": "Intermediate",
    "clientLocation": "United States",
    "paymentVerified": True,
    "allowedApplicantCountries": None,
    "clientName": "John",
    "clientNameConfidence": 0.9,
    "clientAvgHourlyRate": 25.0,
    "clientRating": 4.9,
    "clientHireRatePercent": 90,
    "clientTotalSpent": 15000.0,
    "hasHired": True,
    "proposals": 7,
    "questions": [{"question": "Describe your AR experience.", "position": 1}],
    "tags": ["Unity", "AR Foundation", "C#", "ARCore"],
}


def _make_apify_mock(items: list[dict]) -> MagicMock:
    """Return a mock ApifyClient whose actor().call() and dataset().iterate_items() work."""
    mock_client = MagicMock()
    mock_client.actor.return_value.call.return_value = {"defaultDatasetId": "ds-abc"}
    mock_client.dataset.return_value.iterate_items.return_value = iter(items)
    return mock_client


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Happy path — full item
# ---------------------------------------------------------------------------


def test_full_item_core_fields():
    with patch("scrapers.upwork.ApifyClient", return_value=_make_apify_mock([FULL_RAW_ITEM])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(UpworkScraper().fetch_jobs(UPWORK_CONFIG))

    assert len(jobs) == 1
    job = jobs[0]
    assert job.id == "~01234567890abcdef0"
    assert job.platform == "upwork"
    assert job.title == "Unity AR Developer — Indoor Navigation App"
    assert job.url == "https://www.upwork.com/jobs/~01234567890abcdef0"
    assert job.budget == "$2,000"
    assert job.job_type == "Fixed"
    assert job.experience_level == "Intermediate"


def test_tags_mapped_to_skills():
    with patch("scrapers.upwork.ApifyClient", return_value=_make_apify_mock([FULL_RAW_ITEM])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(UpworkScraper().fetch_jobs(UPWORK_CONFIG))

    assert jobs[0].skills == ["Unity", "AR Foundation", "C#", "ARCore"]


def test_extras_populated_with_correct_types():
    """clientRating and proposals are numbers in the schema — verify they pass through as-is."""
    with patch("scrapers.upwork.ApifyClient", return_value=_make_apify_mock([FULL_RAW_ITEM])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(UpworkScraper().fetch_jobs(UPWORK_CONFIG))

    extras = jobs[0].extras
    assert extras["client_rating"] == 4.9
    assert extras["client_location"] == "United States"
    assert extras["proposals"] == 7


def test_multiple_items_all_returned():
    items = [
        {**FULL_RAW_ITEM, "id": "job-1", "title": "Job One"},
        {**FULL_RAW_ITEM, "id": "job-2", "title": "Job Two"},
        {**FULL_RAW_ITEM, "id": "job-3", "title": "Job Three"},
    ]
    with patch("scrapers.upwork.ApifyClient", return_value=_make_apify_mock(items)):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(UpworkScraper().fetch_jobs(UPWORK_CONFIG))

    assert [j.id for j in jobs] == ["job-1", "job-2", "job-3"]


# ---------------------------------------------------------------------------
# Nullable fields present as null
# ---------------------------------------------------------------------------


def test_null_budget_gives_none():
    item = {**FULL_RAW_ITEM, "budget": None}
    with patch("scrapers.upwork.ApifyClient", return_value=_make_apify_mock([item])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(UpworkScraper().fetch_jobs(UPWORK_CONFIG))

    assert jobs[0].budget is None


def test_null_client_rating_absent_from_extras():
    item = {**FULL_RAW_ITEM, "clientRating": None}
    with patch("scrapers.upwork.ApifyClient", return_value=_make_apify_mock([item])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(UpworkScraper().fetch_jobs(UPWORK_CONFIG))

    assert "client_rating" not in jobs[0].extras


def test_null_proposals_absent_from_extras():
    item = {**FULL_RAW_ITEM, "proposals": None}
    with patch("scrapers.upwork.ApifyClient", return_value=_make_apify_mock([item])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(UpworkScraper().fetch_jobs(UPWORK_CONFIG))

    assert "proposals" not in jobs[0].extras


def test_null_client_location_absent_from_extras():
    item = {**FULL_RAW_ITEM, "clientLocation": None}
    with patch("scrapers.upwork.ApifyClient", return_value=_make_apify_mock([item])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(UpworkScraper().fetch_jobs(UPWORK_CONFIG))

    assert "client_location" not in jobs[0].extras


# ---------------------------------------------------------------------------
# Missing required fields — item skipped
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("missing_field", ["id", "title", "description", "url"])
def test_item_missing_required_field_is_skipped(missing_field: str):
    item = {k: v for k, v in FULL_RAW_ITEM.items() if k != missing_field}
    with patch("scrapers.upwork.ApifyClient", return_value=_make_apify_mock([item])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(UpworkScraper().fetch_jobs(UPWORK_CONFIG))

    assert jobs == []


def test_mix_of_valid_and_invalid_items():
    invalid = {k: v for k, v in FULL_RAW_ITEM.items() if k != "id"}
    valid = {**FULL_RAW_ITEM, "id": "job-ok"}
    with patch("scrapers.upwork.ApifyClient", return_value=_make_apify_mock([invalid, valid])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(UpworkScraper().fetch_jobs(UPWORK_CONFIG))

    assert len(jobs) == 1
    assert jobs[0].id == "job-ok"


# ---------------------------------------------------------------------------
# Minimal item — only required fields present
# ---------------------------------------------------------------------------


def test_minimal_item_optional_fields_are_none():
    item = {
        "id": "job-min",
        "title": "Minimal Job",
        "description": "Some description.",
        "url": "https://www.upwork.com/jobs/job-min",
    }
    with patch("scrapers.upwork.ApifyClient", return_value=_make_apify_mock([item])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(UpworkScraper().fetch_jobs(UPWORK_CONFIG))

    job = jobs[0]
    assert job.budget is None
    assert job.job_type is None
    assert job.experience_level is None
    assert job.skills is None
    assert job.extras == {}


# ---------------------------------------------------------------------------
# Empty dataset and actor failure
# ---------------------------------------------------------------------------


def test_empty_dataset_returns_empty_list():
    with patch("scrapers.upwork.ApifyClient", return_value=_make_apify_mock([])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(UpworkScraper().fetch_jobs(UPWORK_CONFIG))

    assert jobs == []


def test_actor_returns_none_gives_empty_list():
    mock_client = MagicMock()
    mock_client.actor.return_value.call.return_value = None
    with patch("scrapers.upwork.ApifyClient", return_value=mock_client):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(UpworkScraper().fetch_jobs(UPWORK_CONFIG))

    assert jobs == []


# ---------------------------------------------------------------------------
# Platform attribute
# ---------------------------------------------------------------------------


def test_platform_attribute():
    assert UpworkScraper.platform == "upwork"
