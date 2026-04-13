"""Unit tests for scrapers.linkedin.LinkedInScraper.

Apify is mocked — no network calls, no credits consumed.
Raw item fixtures match the Apify LinkedIn Jobs actor output schema.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from scrapers.linkedin import LinkedInScraper, _normalize_salary

# ---------------------------------------------------------------------------
# Config fixture — mirrors configs/platforms/linkedin.json field_mappings
# ---------------------------------------------------------------------------

LINKEDIN_CONFIG = {
    "scraper": {
        "actor_id": "2rJKkhh7vjpX7pvjg",
        "input": {"searchTerms": ["unity developer"], "location": "Remote"},
    },
    "field_mappings": {
        "id": "jobId",
        "title": "jobTitle",
        "description": "jobDescription",
        "url": "jobUrl",
        "skills": None,
        "budget": "salaryInfo",
        "job_type": "contractType",
        "experience_level": "experienceLevel",
        "extras": {
            "company_name": "companyName",
            "location": "location",
            "work_type": "workType",
            "sector": "sector",
            "applications_count": "applicationsCount",
            "apply_type": "applyType",
            "posted_time": "postedTime",
            "poster_name": "posterName",
            "company_url": "companyUrl",
        },
    },
}

# Realistic raw item matching the Apify LinkedIn Jobs actor output schema
FULL_RAW_ITEM = {
    "jobId": "3987654321",
    "jobTitle": "Unity AR Developer",
    "jobDescription": "Build AR applications using Unity and AR Foundation.",
    "jobUrl": "https://www.linkedin.com/jobs/view/3987654321",
    "companyName": "Acme Corp",
    "location": "Berlin, Germany",
    "workType": "Remote",
    "sector": "Technology",
    "applicationsCount": 42,
    "applyType": "EASY_APPLY",
    "postedTime": "2 days ago",
    "posterName": "Jane Smith",
    "companyUrl": "https://www.linkedin.com/company/acme-corp",
    "contractType": "Full-time",
    "experienceLevel": "Mid-Senior level",
    "salaryInfo": ["$80,000/yr", "$120,000/yr"],
}


def _make_apify_mock(items: list[dict]) -> MagicMock:
    """Return a mock ApifyClient whose actor().call() and dataset().iterate_items() work."""
    mock_client = MagicMock()
    mock_client.actor.return_value.call.return_value = {"defaultDatasetId": "ds-linkedin"}
    mock_client.dataset.return_value.iterate_items.return_value = iter(items)
    return mock_client


def run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# _normalize_salary unit tests
# ---------------------------------------------------------------------------


def test_normalize_salary_two_values():
    assert _normalize_salary(["$80,000/yr", "$120,000/yr"]) == "$80,000/yr – $120,000/yr"


def test_normalize_salary_single_value():
    assert _normalize_salary(["$50/hr"]) == "$50/hr"


def test_normalize_salary_empty_list():
    assert _normalize_salary([]) is None


def test_normalize_salary_none_input():
    assert _normalize_salary(None) is None


def test_normalize_salary_non_list():
    assert _normalize_salary("$50,000") is None


def test_normalize_salary_list_with_empty_strings():
    assert _normalize_salary(["", ""]) is None


def test_normalize_salary_list_with_one_empty_one_value():
    assert _normalize_salary(["", "$60/hr"]) == "$60/hr"


# ---------------------------------------------------------------------------
# Happy path — full item
# ---------------------------------------------------------------------------


def test_full_item_core_fields():
    with patch("scrapers.linkedin.ApifyClient", return_value=_make_apify_mock([FULL_RAW_ITEM])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(LinkedInScraper().fetch_jobs(LINKEDIN_CONFIG))

    assert len(jobs) == 1
    job = jobs[0]
    assert job.id == "3987654321"
    assert job.platform == "linkedin"
    assert job.title == "Unity AR Developer"
    assert job.description == "Build AR applications using Unity and AR Foundation."
    assert job.url == "https://www.linkedin.com/jobs/view/3987654321"
    assert job.job_type == "Full-time"
    assert job.experience_level == "Mid-Senior level"


def test_salary_info_joined_as_range():
    with patch("scrapers.linkedin.ApifyClient", return_value=_make_apify_mock([FULL_RAW_ITEM])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(LinkedInScraper().fetch_jobs(LINKEDIN_CONFIG))

    assert jobs[0].budget == "$80,000/yr – $120,000/yr"


def test_skills_always_none():
    """LinkedIn actor does not provide skills — field is always None."""
    with patch("scrapers.linkedin.ApifyClient", return_value=_make_apify_mock([FULL_RAW_ITEM])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(LinkedInScraper().fetch_jobs(LINKEDIN_CONFIG))

    assert jobs[0].skills is None


def test_all_extras_populated():
    with patch("scrapers.linkedin.ApifyClient", return_value=_make_apify_mock([FULL_RAW_ITEM])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(LinkedInScraper().fetch_jobs(LINKEDIN_CONFIG))

    extras = jobs[0].extras
    assert extras["company_name"] == "Acme Corp"
    assert extras["location"] == "Berlin, Germany"
    assert extras["work_type"] == "Remote"
    assert extras["sector"] == "Technology"
    assert extras["applications_count"] == 42
    assert extras["apply_type"] == "EASY_APPLY"
    assert extras["posted_time"] == "2 days ago"
    assert extras["poster_name"] == "Jane Smith"
    assert extras["company_url"] == "https://www.linkedin.com/company/acme-corp"


def test_multiple_items_all_returned():
    items = [
        {**FULL_RAW_ITEM, "jobId": "job-1", "jobTitle": "Job One"},
        {**FULL_RAW_ITEM, "jobId": "job-2", "jobTitle": "Job Two"},
        {**FULL_RAW_ITEM, "jobId": "job-3", "jobTitle": "Job Three"},
    ]
    with patch("scrapers.linkedin.ApifyClient", return_value=_make_apify_mock(items)):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(LinkedInScraper().fetch_jobs(LINKEDIN_CONFIG))

    assert [j.id for j in jobs] == ["job-1", "job-2", "job-3"]


# ---------------------------------------------------------------------------
# salaryInfo variations
# ---------------------------------------------------------------------------


def test_empty_salary_info_gives_none_budget():
    item = {**FULL_RAW_ITEM, "salaryInfo": []}
    with patch("scrapers.linkedin.ApifyClient", return_value=_make_apify_mock([item])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(LinkedInScraper().fetch_jobs(LINKEDIN_CONFIG))

    assert jobs[0].budget is None


def test_null_salary_info_gives_none_budget():
    item = {**FULL_RAW_ITEM, "salaryInfo": None}
    with patch("scrapers.linkedin.ApifyClient", return_value=_make_apify_mock([item])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(LinkedInScraper().fetch_jobs(LINKEDIN_CONFIG))

    assert jobs[0].budget is None


def test_absent_salary_info_gives_none_budget():
    item = {k: v for k, v in FULL_RAW_ITEM.items() if k != "salaryInfo"}
    with patch("scrapers.linkedin.ApifyClient", return_value=_make_apify_mock([item])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(LinkedInScraper().fetch_jobs(LINKEDIN_CONFIG))

    assert jobs[0].budget is None


def test_single_entry_salary_info():
    item = {**FULL_RAW_ITEM, "salaryInfo": ["$50/hr"]}
    with patch("scrapers.linkedin.ApifyClient", return_value=_make_apify_mock([item])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(LinkedInScraper().fetch_jobs(LINKEDIN_CONFIG))

    assert jobs[0].budget == "$50/hr"


# ---------------------------------------------------------------------------
# Missing required fields — item skipped
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "missing_field",
    ["jobId", "jobTitle", "jobDescription", "jobUrl"],
)
def test_item_missing_required_field_is_skipped(missing_field: str):
    item = {k: v for k, v in FULL_RAW_ITEM.items() if k != missing_field}
    with patch("scrapers.linkedin.ApifyClient", return_value=_make_apify_mock([item])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(LinkedInScraper().fetch_jobs(LINKEDIN_CONFIG))

    assert jobs == []


def test_mix_of_valid_and_invalid_items():
    invalid = {k: v for k, v in FULL_RAW_ITEM.items() if k != "jobId"}
    valid = {**FULL_RAW_ITEM, "jobId": "job-ok"}
    with patch("scrapers.linkedin.ApifyClient", return_value=_make_apify_mock([invalid, valid])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(LinkedInScraper().fetch_jobs(LINKEDIN_CONFIG))

    assert len(jobs) == 1
    assert jobs[0].id == "job-ok"


# ---------------------------------------------------------------------------
# Minimal item — only required fields present
# ---------------------------------------------------------------------------


def test_minimal_item_optional_fields_are_none():
    item = {
        "jobId": "job-min",
        "jobTitle": "Minimal LinkedIn Job",
        "jobDescription": "Some description.",
        "jobUrl": "https://www.linkedin.com/jobs/view/job-min",
    }
    with patch("scrapers.linkedin.ApifyClient", return_value=_make_apify_mock([item])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(LinkedInScraper().fetch_jobs(LINKEDIN_CONFIG))

    job = jobs[0]
    assert job.budget is None
    assert job.job_type is None
    assert job.experience_level is None
    assert job.skills is None
    assert job.extras == {}


# ---------------------------------------------------------------------------
# Absent extras — only present extras in dict
# ---------------------------------------------------------------------------


def test_null_extra_absent_from_extras_dict():
    item = {**FULL_RAW_ITEM, "companyName": None}
    with patch("scrapers.linkedin.ApifyClient", return_value=_make_apify_mock([item])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(LinkedInScraper().fetch_jobs(LINKEDIN_CONFIG))

    assert "company_name" not in jobs[0].extras


# ---------------------------------------------------------------------------
# Empty dataset and actor failure
# ---------------------------------------------------------------------------


def test_empty_dataset_returns_empty_list():
    with patch("scrapers.linkedin.ApifyClient", return_value=_make_apify_mock([])):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(LinkedInScraper().fetch_jobs(LINKEDIN_CONFIG))

    assert jobs == []


def test_actor_returns_none_gives_empty_list():
    mock_client = MagicMock()
    mock_client.actor.return_value.call.return_value = None
    with patch("scrapers.linkedin.ApifyClient", return_value=mock_client):
        with patch.dict("os.environ", {"APIFY_API_TOKEN": "test-token"}):
            jobs = run(LinkedInScraper().fetch_jobs(LINKEDIN_CONFIG))

    assert jobs == []


# ---------------------------------------------------------------------------
# Platform attribute
# ---------------------------------------------------------------------------


def test_platform_attribute():
    assert LinkedInScraper.platform == "linkedin"
