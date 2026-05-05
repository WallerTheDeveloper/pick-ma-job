"""Unit tests for services.pipeline.PipelineService.

All external I/O is mocked:
- ProfileRepository, SearchConfigRepository, JobResultRepository → AsyncMock
- Evaluator → patched at services.pipeline.Evaluator
- get_scraper → patched at services.pipeline.get_scraper
The static config files (configs/platforms/, configs/settings.json) are loaded
for real since they exist on disk and drive real behaviour.
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from core.settings import Settings
from repositories.job_result import JobResultRow
from repositories.profile import ProfileRow
from repositories.search_config import SearchConfigRow
from scrapers.base import NormalizedJob
from services.pipeline import PipelineError, PipelineStats, PipelineService, _merge_config

# ---------------------------------------------------------------------------
# Factories
# ---------------------------------------------------------------------------

_USER_ID = uuid4()
_RUBRIC = {
    "scoring": {"9-10": "Excellent"},
    "evaluation_factors": ["Skills Match"],
    "system_instructions": "Evaluate the job.",
}

# Default settings with exclude keywords matching configs/settings.json
_DEFAULT_SETTINGS = Settings(
    exclude_title_keywords=[
        "unreal",
        "godot",
        "react native",
        "flutter",
        "devops",
        "data science",
        "machine learning",
        "data engineer",
        "android developer",
        "ios developer",
    ],
)


def _make_profile(**overrides) -> ProfileRow:
    defaults = dict(
        id=uuid4(),
        user_id=_USER_ID,
        role="Unity Developer",
        experience="mid-level — 4 years",
        rate="€20/hr",
        primary_skills=["Unity"],
        secondary_skills=["Rust"],
        tertiary_skills=["Vue.js"],
        not_a_good_fit=["Pure frontend"],
        background=["2 years at ZAUBAR"],
        notable_projects=[],
        languages=["English"],
        rubric=_RUBRIC,
        cv_customize_threshold=7,
        updated_at=datetime(2026, 1, 1),
    )
    defaults.update(overrides)
    return ProfileRow(**defaults)


def _make_search_config(**overrides) -> SearchConfigRow:
    defaults = dict(
        id=uuid4(),
        user_id=_USER_ID,
        platform="upwork",
        query="unity developer",
        filters={},
        updated_at=datetime(2026, 1, 1),
    )
    defaults.update(overrides)
    return SearchConfigRow(**defaults)


def _make_job(**overrides) -> NormalizedJob:
    defaults = dict(
        id="job-001",
        platform="upwork",
        title="Unity AR Developer",
        description="Build an AR app in Unity.",
        url="https://upwork.com/jobs/job-001",
        budget="$2,000",
        job_type="Fixed",
        experience_level="Intermediate",
        skills=["Unity", "ARCore"],
        extras={"client_rating": "4.9"},
    )
    defaults.update(overrides)
    return NormalizedJob(**defaults)


def _make_job_result_row(**overrides) -> JobResultRow:
    defaults = dict(
        id=uuid4(),
        user_id=_USER_ID,
        platform="upwork",
        job_id="job-001",
        title="Unity AR Developer",
        url="https://upwork.com/jobs/job-001",
        score=8,
        evaluation={"relevancy_score": 8},
        status="new",
        created_at=datetime(2026, 1, 1),
    )
    defaults.update(overrides)
    return JobResultRow(**defaults)


def _make_evaluation_result(score: int = 8):
    from core.evaluator import EvaluationResult
    return EvaluationResult.from_dict({
        "scratchpad": "...",
        "evaluation": "Good fit.",
        "relevancy_score": score,
        "recommendation": "Yes apply",
        "flags": "clear scope",
        "summary": "Good AR fit.",
    })


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def profile_repo():
    repo = AsyncMock()
    repo.find_by_user_id.return_value = _make_profile()
    return repo


@pytest.fixture
def search_config_repo():
    repo = AsyncMock()
    repo.find_by_user_id.return_value = [_make_search_config()]
    repo.find_by_user_and_platform.return_value = _make_search_config()
    return repo


@pytest.fixture
def job_result_repo():
    repo = AsyncMock()
    repo.exists.return_value = False
    repo.insert.return_value = _make_job_result_row()
    return repo


@pytest.fixture
def mock_scraper():
    scraper = AsyncMock()
    scraper.fetch_jobs.return_value = [_make_job()]
    return scraper


@pytest.fixture
def mock_evaluator():
    evaluator = AsyncMock()
    evaluator.evaluate.return_value = _make_evaluation_result()
    # Mock _call_score to return (score, parse_failed, meta)
    from unittest.mock import MagicMock
    meta = MagicMock()
    meta.model = "test-model"
    meta.duration_ms = 100
    meta.input_tokens = 50
    meta.output_tokens = 10
    evaluator._call_score.return_value = (8, False, meta)
    return evaluator


def _make_service(profile_repo, search_config_repo, job_result_repo, company_blacklist_repo=None) -> PipelineService:
    if company_blacklist_repo is None:
        company_blacklist_repo = AsyncMock()
        company_blacklist_repo.find_names_by_user_id.return_value = ()
    return PipelineService(
        profile_repo=profile_repo,
        search_config_repo=search_config_repo,
        job_result_repo=job_result_repo,
        job_list_repo=AsyncMock(),
        company_blacklist_repo=company_blacklist_repo,
        llm_client=MagicMock(),
        settings=_DEFAULT_SETTINGS,
    )


# ---------------------------------------------------------------------------
# PipelineError cases
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_pipeline_raises_if_profile_missing(
    search_config_repo, job_result_repo
):
    profile_repo = AsyncMock()
    profile_repo.find_by_user_id.return_value = None
    svc = _make_service(profile_repo, search_config_repo, job_result_repo)

    with pytest.raises(PipelineError, match="complete your profile"):
        await svc.run_pipeline(_USER_ID)


@pytest.mark.asyncio
async def test_run_pipeline_raises_if_no_search_configs(
    profile_repo, job_result_repo
):
    search_config_repo = AsyncMock()
    search_config_repo.find_by_user_id.return_value = []
    svc = _make_service(profile_repo, search_config_repo, job_result_repo)

    with pytest.raises(PipelineError, match="No search configurations"):
        await svc.run_pipeline(_USER_ID)


@pytest.mark.asyncio
async def test_run_pipeline_single_platform_not_found_raises(
    profile_repo, job_result_repo
):
    search_config_repo = AsyncMock()
    search_config_repo.find_by_user_id.return_value = []
    svc = _make_service(profile_repo, search_config_repo, job_result_repo)

    with pytest.raises(PipelineError, match="No search configurations"):
        await svc.run_pipeline(_USER_ID, platforms=["upwork"])


# ---------------------------------------------------------------------------
# T-06 — platform list filtering and validation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_pipeline_empty_platforms_raises():
    svc = _make_service_no_repos()

    with pytest.raises(PipelineError, match="No platforms selected"):
        await svc.run_pipeline(_USER_ID, platforms=[])


@pytest.mark.asyncio
async def test_run_pipeline_unknown_platform_raises():
    svc = _make_service_no_repos()

    with pytest.raises(PipelineError, match="Unknown platform"):
        await svc.run_pipeline(_USER_ID, platforms=["fakeplatform"])


@pytest.mark.asyncio
async def test_run_pipeline_filters_to_requested_platforms(
    profile_repo, job_result_repo, mock_scraper, mock_evaluator
):
    """Two configs (upwork + linkedin); passing platforms=["upwork"] runs only Upwork."""
    upwork_config = _make_search_config(platform="upwork")
    linkedin_config = _make_search_config(platform="linkedin")

    search_config_repo = AsyncMock()
    search_config_repo.find_by_user_id.return_value = [upwork_config, linkedin_config]

    svc = _make_service(profile_repo, search_config_repo, job_result_repo)

    with patch("services.pipeline.get_scraper", return_value=mock_scraper), \
         patch("services.pipeline.Evaluator", return_value=mock_evaluator):
        result = await svc.run_pipeline(_USER_ID, platforms=["upwork"])

    # scraper should only be called once (for the one upwork config)
    assert mock_scraper.fetch_jobs.call_count == 1
    assert result.jobs_found == 1


@pytest.mark.asyncio
async def test_run_pipeline_none_platforms_runs_all(
    profile_repo, job_result_repo, mock_evaluator
):
    """platforms=None (default) runs all configured platforms."""
    upwork_config = _make_search_config(platform="upwork")
    linkedin_config = _make_search_config(platform="linkedin")

    search_config_repo = AsyncMock()
    search_config_repo.find_by_user_id.return_value = [upwork_config, linkedin_config]

    scraper = AsyncMock()
    scraper.fetch_jobs.return_value = [_make_job()]

    svc = _make_service(profile_repo, search_config_repo, job_result_repo)

    with patch("services.pipeline.get_scraper", return_value=scraper), \
         patch("services.pipeline.Evaluator", return_value=mock_evaluator):
        result = await svc.run_pipeline(_USER_ID)

    # scraper called once per config (one upwork + one linkedin)
    assert scraper.fetch_jobs.call_count == 2
    assert result.jobs_found == 2


# ---------------------------------------------------------------------------
# Happy path — correct counts
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_pipeline_returns_pipeline_run_result(
    profile_repo, search_config_repo, job_result_repo, mock_scraper, mock_evaluator
):
    svc = _make_service(profile_repo, search_config_repo, job_result_repo)

    with patch("services.pipeline.get_scraper", return_value=mock_scraper), \
         patch("services.pipeline.Evaluator", return_value=mock_evaluator):
        result = await svc.run_pipeline(_USER_ID)

    assert isinstance(result, PipelineStats)


@pytest.mark.asyncio
async def test_run_pipeline_counts_found_evaluated_stored(
    profile_repo, search_config_repo, job_result_repo, mock_scraper, mock_evaluator
):
    svc = _make_service(profile_repo, search_config_repo, job_result_repo)

    with patch("services.pipeline.get_scraper", return_value=mock_scraper), \
         patch("services.pipeline.Evaluator", return_value=mock_evaluator):
        result = await svc.run_pipeline(_USER_ID)

    assert result.jobs_found == 1
    assert result.jobs_stored == 1
    assert result.jobs_skipped_dedup == 0
    assert result.jobs_skipped_filter == 0
    # All jobs now have score only (no Pass 2 evaluation), so jobs_skipped_low_score counts all scored jobs
    assert result.jobs_skipped_low_score == 1
    assert result.jobs_failed == 0
    assert result.errors == ()


@pytest.mark.asyncio
async def test_run_pipeline_single_platform(
    profile_repo, search_config_repo, job_result_repo, mock_scraper, mock_evaluator
):
    svc = _make_service(profile_repo, search_config_repo, job_result_repo)

    with patch("services.pipeline.get_scraper", return_value=mock_scraper), \
         patch("services.pipeline.Evaluator", return_value=mock_evaluator):
        result = await svc.run_pipeline(_USER_ID, platforms=["upwork"])

    search_config_repo.find_by_user_id.assert_called_once_with(_USER_ID)
    assert result.jobs_found == 1


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_dedup_skips_already_seen_jobs(
    profile_repo, search_config_repo, mock_scraper, mock_evaluator
):
    job_result_repo = AsyncMock()
    job_result_repo.exists.return_value = True  # job already in DB
    # Mock find_existing_ids to return the job ID (simulating dedup)
    job_result_repo.find_existing_ids.return_value = {"job-001"}

    svc = _make_service(profile_repo, search_config_repo, job_result_repo)

    with patch("services.pipeline.get_scraper", return_value=mock_scraper), \
         patch("services.pipeline.Evaluator", return_value=mock_evaluator):
        result = await svc.run_pipeline(_USER_ID)

    assert result.jobs_skipped_dedup == 1
    mock_evaluator._call_score.assert_not_called()


@pytest.mark.asyncio
async def test_dedup_stores_new_job_when_not_seen(
    profile_repo, search_config_repo, job_result_repo, mock_scraper, mock_evaluator
):
    job_result_repo.exists.return_value = False

    svc = _make_service(profile_repo, search_config_repo, job_result_repo)

    with patch("services.pipeline.get_scraper", return_value=mock_scraper), \
         patch("services.pipeline.Evaluator", return_value=mock_evaluator):
        result = await svc.run_pipeline(_USER_ID)

    assert result.jobs_skipped_dedup == 0
    assert result.jobs_stored == 1


# ---------------------------------------------------------------------------
# Pre-filter
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_filter_skips_excluded_title_keyword(
    profile_repo, search_config_repo, job_result_repo, mock_evaluator
):
    filtered_job = _make_job(title="Unreal Engine Developer")
    scraper = AsyncMock()
    scraper.fetch_jobs.return_value = [filtered_job]

    svc = _make_service(profile_repo, search_config_repo, job_result_repo)

    with patch("services.pipeline.get_scraper", return_value=scraper), \
         patch("services.pipeline.Evaluator", return_value=mock_evaluator):
        result = await svc.run_pipeline(_USER_ID)

    assert result.jobs_skipped_filter == 1
    mock_evaluator.evaluate.assert_not_called()


@pytest.mark.asyncio
async def test_filter_is_case_insensitive(
    profile_repo, search_config_repo, job_result_repo, mock_evaluator
):
    filtered_job = _make_job(title="FLUTTER Developer Needed")
    scraper = AsyncMock()
    scraper.fetch_jobs.return_value = [filtered_job]

    svc = _make_service(profile_repo, search_config_repo, job_result_repo)

    with patch("services.pipeline.get_scraper", return_value=scraper), \
         patch("services.pipeline.Evaluator", return_value=mock_evaluator):
        result = await svc.run_pipeline(_USER_ID)

    assert result.jobs_skipped_filter == 1


@pytest.mark.asyncio
async def test_filter_does_not_skip_clean_title(
    profile_repo, search_config_repo, job_result_repo, mock_scraper, mock_evaluator
):
    svc = _make_service(profile_repo, search_config_repo, job_result_repo)

    with patch("services.pipeline.get_scraper", return_value=mock_scraper), \
         patch("services.pipeline.Evaluator", return_value=mock_evaluator):
        result = await svc.run_pipeline(_USER_ID)

    assert result.jobs_skipped_filter == 0


# ---------------------------------------------------------------------------
# Error resilience
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_evaluation_error_does_not_abort_run(
    profile_repo, search_config_repo, job_result_repo
):
    job_a = _make_job(id="job-a", title="Unity AR Dev")
    job_b = _make_job(id="job-b", title="Unity VR Dev")
    scraper = AsyncMock()
    scraper.fetch_jobs.return_value = [job_a, job_b]

    evaluator = AsyncMock()
    from unittest.mock import MagicMock
    meta = MagicMock()
    meta.model = "test-model"
    meta.duration_ms = 100
    meta.input_tokens = 50
    meta.output_tokens = 10
    evaluator._call_score.side_effect = [
        ValueError("Claude error"),
        (8, False, meta),
    ]

    svc = _make_service(profile_repo, search_config_repo, job_result_repo)

    with patch("services.pipeline.get_scraper", return_value=scraper), \
         patch("services.pipeline.Evaluator", return_value=evaluator):
        result = await svc.run_pipeline(_USER_ID)

    assert result.jobs_found == 2
    assert result.jobs_stored == 1
    assert len(result.errors) == 1
    assert "Claude error" in result.errors[0]


@pytest.mark.asyncio
async def test_scraper_error_recorded_in_errors(
    profile_repo, search_config_repo, job_result_repo
):
    scraper = AsyncMock()
    scraper.fetch_jobs.side_effect = RuntimeError("Apify timeout")

    svc = _make_service(profile_repo, search_config_repo, job_result_repo)

    with patch("services.pipeline.get_scraper", return_value=scraper), \
         patch("services.pipeline.Evaluator", return_value=AsyncMock()):
        result = await svc.run_pipeline(_USER_ID)

    assert len(result.errors) == 1
    assert "Apify timeout" in result.errors[0]
    assert result.jobs_found == 0


@pytest.mark.asyncio
async def test_insert_error_recorded_but_run_continues(
    profile_repo, search_config_repo, mock_scraper, mock_evaluator
):
    job_result_repo = AsyncMock()
    job_result_repo.exists.return_value = False
    job_result_repo.insert.side_effect = RuntimeError("DB connection lost")

    svc = _make_service(profile_repo, search_config_repo, job_result_repo)

    with patch("services.pipeline.get_scraper", return_value=mock_scraper), \
         patch("services.pipeline.Evaluator", return_value=mock_evaluator):
        result = await svc.run_pipeline(_USER_ID)

    assert result.jobs_stored == 0
    assert len(result.errors) == 1


@pytest.mark.asyncio
async def test_db_dedup_via_insert_returning_none(
    profile_repo, search_config_repo, mock_scraper, mock_evaluator
):
    """insert() returning None (ON CONFLICT DO NOTHING) should not count as stored."""
    job_result_repo = AsyncMock()
    job_result_repo.exists.return_value = False
    job_result_repo.insert.return_value = None  # conflict, row not inserted

    svc = _make_service(profile_repo, search_config_repo, job_result_repo)

    with patch("services.pipeline.get_scraper", return_value=mock_scraper), \
         patch("services.pipeline.Evaluator", return_value=mock_evaluator):
        result = await svc.run_pipeline(_USER_ID)

    assert result.jobs_stored == 0


# ---------------------------------------------------------------------------
# PipelineStats — immutability
# ---------------------------------------------------------------------------

def test_pipeline_stats_is_frozen():
    r = PipelineStats(
        jobs_found=5,
        jobs_skipped_dedup=1,
        jobs_skipped_filter=1,
        jobs_skipped_blacklist=0,
        jobs_skipped_low_score=0,
        jobs_stored=3,
        jobs_failed=0,
        errors=(),
    )
    with pytest.raises(Exception):
        r.jobs_found = 99  # type: ignore[misc]


def test_pipeline_stats_errors_is_tuple():
    r = PipelineStats(
        jobs_found=1,
        jobs_skipped_dedup=0,
        jobs_skipped_filter=0,
        jobs_skipped_blacklist=0,
        jobs_skipped_low_score=0,
        jobs_stored=1,
        jobs_failed=0,
        errors=("some error",),
    )
    assert isinstance(r.errors, tuple)


# ---------------------------------------------------------------------------
# _merge_config (pure function)
# ---------------------------------------------------------------------------

def _static_config() -> dict:
    return {
        "platform": "upwork",
        "scraper": {
            "actor_id": "abc123",
            "input": {
                "query": "unity developer",
                "experienceLevel": ["entry", "intermediate"],
                "perPage": 50,
            },
        },
        "field_mappings": {"id": "id", "title": "title"},
    }


def test_merge_config_preserves_actor_id_and_field_mappings():
    config_row = _make_search_config(query=None, filters={})
    merged = _merge_config(_static_config(), config_row)
    assert merged["scraper"]["actor_id"] == "abc123"
    assert merged["field_mappings"] == {"id": "id", "title": "title"}


def test_merge_config_user_filters_replace_scraper_input():
    user_filters = {"experienceLevel": ["intermediate"], "perPage": 10}
    config_row = _make_search_config(query=None, filters=user_filters)
    merged = _merge_config(_static_config(), config_row)
    assert merged["scraper"]["input"] == user_filters


def test_merge_config_query_overrides_scraper_input_query():
    config_row = _make_search_config(query="rust game developer", filters={})
    merged = _merge_config(_static_config(), config_row)
    assert merged["scraper"]["input"]["query"] == "rust game developer"


def test_merge_config_query_override_with_user_filters():
    user_filters = {"experienceLevel": ["entry"], "perPage": 20}
    config_row = _make_search_config(query="ar developer", filters=user_filters)
    merged = _merge_config(_static_config(), config_row)
    assert merged["scraper"]["input"]["query"] == "ar developer"
    assert merged["scraper"]["input"]["experienceLevel"] == ["entry"]


def test_merge_config_empty_filters_keeps_static_input():
    config_row = _make_search_config(query=None, filters={})
    merged = _merge_config(_static_config(), config_row)
    assert merged["scraper"]["input"]["experienceLevel"] == ["entry", "intermediate"]
    assert merged["scraper"]["input"]["perPage"] == 50


def test_merge_config_does_not_mutate_static_config():
    static = _static_config()
    config_row = _make_search_config(query="different query", filters={"perPage": 99})
    _merge_config(static, config_row)
    assert static["scraper"]["input"]["query"] == "unity developer"
    assert static["scraper"]["input"]["perPage"] == 50


# ---------------------------------------------------------------------------
# _is_filtered (via PipelineService instance)
# ---------------------------------------------------------------------------

def _make_service_no_repos() -> PipelineService:
    blacklist_repo = AsyncMock()
    blacklist_repo.find_names_by_user_id.return_value = ()
    return PipelineService(
        profile_repo=AsyncMock(),
        search_config_repo=AsyncMock(),
        job_result_repo=AsyncMock(),
        job_list_repo=AsyncMock(),
        company_blacklist_repo=blacklist_repo,
        llm_client=MagicMock(),
        settings=_DEFAULT_SETTINGS,
    )


def test_is_filtered_matches_excluded_keyword():
    svc = _make_service_no_repos()
    assert svc._is_filtered("Unreal Engine AR Developer") is True


def test_is_filtered_case_insensitive():
    svc = _make_service_no_repos()
    assert svc._is_filtered("GODOT Game Developer") is True


def test_is_filtered_returns_false_for_clean_title():
    svc = _make_service_no_repos()
    assert svc._is_filtered("Unity AR Developer — Mobile App") is False


def test_is_filtered_partial_word_match():
    svc = _make_service_no_repos()
    # "flutter" is in the exclude list
    assert svc._is_filtered("Flutter/Unity Hybrid App") is True


# ---------------------------------------------------------------------------
# _is_blacklisted
# ---------------------------------------------------------------------------

def test_is_blacklisted_matches_substring():
    svc = _make_service_no_repos()
    job = _make_job(extras={"company_name": "Google DeepMind"})
    assert svc._is_blacklisted(job, ("google",)) is True


def test_is_blacklisted_blocks_exact_name():
    svc = _make_service_no_repos()
    job = _make_job(extras={"company_name": "Google LLC"})
    assert svc._is_blacklisted(job, ("google",)) is True


def test_is_blacklisted_no_company_name_returns_false():
    svc = _make_service_no_repos()
    job = _make_job(extras={})
    assert svc._is_blacklisted(job, ("google",)) is False


def test_is_blacklisted_empty_blacklist_returns_false():
    svc = _make_service_no_repos()
    job = _make_job(extras={"company_name": "Google"})
    assert svc._is_blacklisted(job, ()) is False


def test_is_blacklisted_case_insensitive():
    svc = _make_service_no_repos()
    job = _make_job(extras={"company_name": "GOOGLE INC"})
    assert svc._is_blacklisted(job, ("google",)) is True


# ---------------------------------------------------------------------------
# Blacklist filter in pipeline run
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_blacklisted_job_skips_evaluator(
    profile_repo, search_config_repo, job_result_repo, mock_evaluator
):
    blacklisted_job = _make_job(extras={"company_name": "Google DeepMind"})
    scraper = AsyncMock()
    scraper.fetch_jobs.return_value = [blacklisted_job]

    blacklist_repo = AsyncMock()
    blacklist_repo.find_names_by_user_id.return_value = ("google",)

    svc = _make_service(profile_repo, search_config_repo, job_result_repo, blacklist_repo)

    with patch("services.pipeline.get_scraper", return_value=scraper), \
         patch("services.pipeline.Evaluator", return_value=mock_evaluator):
        result = await svc.run_pipeline(_USER_ID)

    assert result.jobs_skipped_blacklist == 1
    mock_evaluator.evaluate.assert_not_called()


@pytest.mark.asyncio
async def test_job_without_company_name_not_blacklisted(
    profile_repo, search_config_repo, job_result_repo, mock_evaluator
):
    job = _make_job(extras={})
    scraper = AsyncMock()
    scraper.fetch_jobs.return_value = [job]

    blacklist_repo = AsyncMock()
    blacklist_repo.find_names_by_user_id.return_value = ("google",)

    svc = _make_service(profile_repo, search_config_repo, job_result_repo, blacklist_repo)

    with patch("services.pipeline.get_scraper", return_value=scraper), \
         patch("services.pipeline.Evaluator", return_value=mock_evaluator):
        result = await svc.run_pipeline(_USER_ID)

    assert result.jobs_skipped_blacklist == 0
    mock_evaluator._call_score.assert_called_once()


@pytest.mark.asyncio
async def test_empty_blacklist_does_not_skip_jobs(
    profile_repo, search_config_repo, job_result_repo, mock_evaluator
):
    job = _make_job(extras={"company_name": "Google"})
    scraper = AsyncMock()
    scraper.fetch_jobs.return_value = [job]

    blacklist_repo = AsyncMock()
    blacklist_repo.find_names_by_user_id.return_value = ()

    svc = _make_service(profile_repo, search_config_repo, job_result_repo, blacklist_repo)

    with patch("services.pipeline.get_scraper", return_value=scraper), \
         patch("services.pipeline.Evaluator", return_value=mock_evaluator):
        result = await svc.run_pipeline(_USER_ID)

    assert result.jobs_skipped_blacklist == 0
    mock_evaluator._call_score.assert_called_once()


@pytest.mark.asyncio
async def test_blacklist_count_aggregated_across_platforms(
    profile_repo, job_result_repo, mock_evaluator
):
    upwork_config = _make_search_config(platform="upwork")
    linkedin_config = _make_search_config(platform="linkedin")
    search_config_repo = AsyncMock()
    search_config_repo.find_by_user_id.return_value = [upwork_config, linkedin_config]

    blacklist_repo = AsyncMock()
    blacklist_repo.find_names_by_user_id.return_value = ("google",)

    google_job = _make_job(extras={"company_name": "Google"})
    scraper = AsyncMock()
    scraper.fetch_jobs.return_value = [google_job]

    svc = _make_service(profile_repo, search_config_repo, job_result_repo, blacklist_repo)

    with patch("services.pipeline.get_scraper", return_value=scraper), \
         patch("services.pipeline.Evaluator", return_value=mock_evaluator):
        result = await svc.run_pipeline(_USER_ID)

    assert result.jobs_skipped_blacklist == 2  # one per platform
