"""Unit tests for main.py — load_config, _resolve_env_vars, _parse_cron,
run_platform orchestration, and API endpoints.

All external I/O (file reads, scraper, evaluator, sheets, notifier, dedup) is mocked.
"""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import _parse_cron, _resolve_env_vars, app, load_config

# ---------------------------------------------------------------------------
# _resolve_env_vars
# ---------------------------------------------------------------------------


def test_resolve_env_vars_plain_string_unchanged():
    assert _resolve_env_vars("hello") == "hello"


def test_resolve_env_vars_replaces_dollar_var(monkeypatch):
    monkeypatch.setenv("MY_TOKEN", "secret123")
    assert _resolve_env_vars("$MY_TOKEN") == "secret123"


def test_resolve_env_vars_nested_dict(monkeypatch):
    monkeypatch.setenv("API_KEY_VAL", "abc")
    result = _resolve_env_vars({"key": "$API_KEY_VAL", "other": "plain"})
    assert result == {"key": "abc", "other": "plain"}


def test_resolve_env_vars_nested_list(monkeypatch):
    monkeypatch.setenv("TOKEN", "tok")
    result = _resolve_env_vars(["$TOKEN", "static"])
    assert result == ["tok", "static"]


def test_resolve_env_vars_deeply_nested(monkeypatch):
    monkeypatch.setenv("DEEP_VAR", "deep_value")
    obj = {"a": {"b": ["$DEEP_VAR"]}}
    assert _resolve_env_vars(obj) == {"a": {"b": ["deep_value"]}}


def test_resolve_env_vars_missing_var_raises(monkeypatch):
    monkeypatch.delenv("MISSING_VAR", raising=False)
    with pytest.raises(KeyError, match="MISSING_VAR"):
        _resolve_env_vars("$MISSING_VAR")


def test_resolve_env_vars_non_string_passthrough():
    assert _resolve_env_vars(42) == 42
    assert _resolve_env_vars(True) is True
    assert _resolve_env_vars(None) is None


# ---------------------------------------------------------------------------
# load_config
# ---------------------------------------------------------------------------


def test_load_config_parses_json(tmp_path):
    cfg = {"model": "haiku", "threshold": 7}
    f = tmp_path / "settings.json"
    f.write_text(json.dumps(cfg))
    result = load_config(str(f))
    assert result == cfg


def test_load_config_resolves_env_vars(tmp_path, monkeypatch):
    monkeypatch.setenv("SHEET_ID", "real-sheet-id")
    cfg = {"spreadsheet_id": "$SHEET_ID"}
    f = tmp_path / "cfg.json"
    f.write_text(json.dumps(cfg))
    result = load_config(str(f))
    assert result["spreadsheet_id"] == "real-sheet-id"


def test_load_config_missing_file_raises():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path/config.json")


# ---------------------------------------------------------------------------
# _parse_cron
# ---------------------------------------------------------------------------


def test_parse_cron_every_6_hours():
    result = _parse_cron("0 */6 * * *")
    assert result == {"minute": "0", "hour": "*/6", "day": "*", "month": "*", "day_of_week": "*"}


def test_parse_cron_daily_midnight():
    result = _parse_cron("0 0 * * *")
    assert result == {"minute": "0", "hour": "0", "day": "*", "month": "*", "day_of_week": "*"}


def test_parse_cron_wrong_field_count_raises():
    with pytest.raises(ValueError, match="5-field"):
        _parse_cron("0 */6 * *")


def test_parse_cron_too_many_fields_raises():
    with pytest.raises(ValueError):
        _parse_cron("0 */6 * * * extra")


# ---------------------------------------------------------------------------
# Fixtures for API + run_platform tests
# ---------------------------------------------------------------------------

SETTINGS = {
    "model": "claude-haiku-4-5-20251001",
    "temperature": 0,
    "alert_threshold": 7,
    "dedup_db_path": "data/seen_jobs.db",
    "sheets": {"spreadsheet_id": "sheet-id"},
    "pre_filters": {"exclude_title_keywords": ["unreal", "godot"]},
}

UPWORK_CONFIG = {
    "platform": "upwork",
    "enabled": True,
    "scraper": {"actor_id": "apify/upwork-scraper", "input": {}},
    "schedule": {"cron": "0 */6 * * *"},
    "field_mappings": {},
    "sheet": {"worksheet_name": "Upwork", "columns": ["relevancy_score", "title", "url"]},
}

UPWORK_CONTEXT = {
    "platform": "upwork",
    "evaluation_notes": [],
    "available_fields": ["title"],
    "user_message_template": "Title: {title}\nURL: {url}",
}

from scrapers.base import NormalizedJob
from core.evaluator import EvaluationResult

SAMPLE_JOB = NormalizedJob(
    id="job-001",
    platform="upwork",
    title="Unity AR Developer",
    description="Build AR app.",
    url="https://upwork.com/jobs/job-001",
    budget="$2000",
    extras={"client_location": "US"},
)

SAMPLE_RESULT = EvaluationResult({
    "relevancy_score": 8,
    "recommendation": "Yes apply",
    "summary": "Great fit.",
    "evaluation": "Strong match.",
    "flags": "Verified client",
    "scratchpad": "",
})

LOW_RESULT = EvaluationResult({
    "relevancy_score": 5,
    "recommendation": "Consider applying",
    "summary": "Moderate fit.",
    "evaluation": "Some overlap.",
    "flags": "",
    "scratchpad": "",
})


def _patch_globals(
    jobs=None,
    result=None,
    is_seen=False,
):
    """Return a dict of patches that wire up all shared state in main.py."""
    import main

    if jobs is None:
        jobs = [SAMPLE_JOB]
    if result is None:
        result = SAMPLE_RESULT

    main._settings = SETTINGS
    main._platform_configs = {"upwork": UPWORK_CONFIG}
    main._prompt_contexts = {"upwork": UPWORK_CONTEXT}
    main._last_run = {}

    mock_evaluator = MagicMock()
    mock_evaluator.evaluate = AsyncMock(return_value=result)
    main._evaluator = mock_evaluator

    mock_dedup = MagicMock()
    mock_dedup.is_seen.return_value = is_seen
    main._dedup = mock_dedup

    mock_sheets = MagicMock()
    main._sheets = mock_sheets

    mock_notifier = MagicMock()
    main._notifier = mock_notifier

    mock_scraper = MagicMock()
    mock_scraper.fetch_jobs = AsyncMock(return_value=jobs)

    return {
        "evaluator": mock_evaluator,
        "dedup": mock_dedup,
        "sheets": mock_sheets,
        "notifier": mock_notifier,
        "scraper": mock_scraper,
    }


# ---------------------------------------------------------------------------
# run_platform
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_platform_returns_correct_summary():
    import main
    mocks = _patch_globals()
    with patch("main.get_scraper", return_value=mocks["scraper"]):
        summary = await main.run_platform("upwork")

    assert summary["platform"] == "upwork"
    assert summary["fetched"] == 1
    assert summary["evaluated"] == 1
    assert summary["skipped_dedup"] == 0
    assert summary["skipped_filter"] == 0
    assert summary["alerted"] == 1


@pytest.mark.asyncio
async def test_run_platform_skips_seen_jobs():
    import main
    mocks = _patch_globals(is_seen=True)
    with patch("main.get_scraper", return_value=mocks["scraper"]):
        summary = await main.run_platform("upwork")

    assert summary["skipped_dedup"] == 1
    assert summary["evaluated"] == 0
    mocks["evaluator"].evaluate.assert_not_called()


@pytest.mark.asyncio
async def test_run_platform_filters_excluded_keywords():
    import main
    job = NormalizedJob(
        id="job-unreal", platform="upwork", title="Unreal Engine Developer",
        description="...", url="https://upwork.com/jobs/job-unreal",
    )
    mocks = _patch_globals(jobs=[job])
    with patch("main.get_scraper", return_value=mocks["scraper"]):
        summary = await main.run_platform("upwork")

    assert summary["skipped_filter"] == 1
    assert summary["evaluated"] == 0
    mocks["evaluator"].evaluate.assert_not_called()


@pytest.mark.asyncio
async def test_run_platform_filtered_jobs_marked_seen():
    import main
    job = NormalizedJob(
        id="job-godot", platform="upwork", title="Godot Game Developer",
        description="...", url="https://upwork.com/jobs/job-godot",
    )
    mocks = _patch_globals(jobs=[job])
    with patch("main.get_scraper", return_value=mocks["scraper"]):
        await main.run_platform("upwork")

    mocks["dedup"].mark_seen.assert_called_once_with("job-godot", "upwork")


@pytest.mark.asyncio
async def test_run_platform_no_alert_below_threshold():
    import main
    mocks = _patch_globals(result=LOW_RESULT)
    with patch("main.get_scraper", return_value=mocks["scraper"]):
        summary = await main.run_platform("upwork")

    assert summary["alerted"] == 0


@pytest.mark.asyncio
async def test_run_platform_marks_evaluated_jobs_seen():
    import main
    mocks = _patch_globals()
    with patch("main.get_scraper", return_value=mocks["scraper"]):
        await main.run_platform("upwork")

    mocks["dedup"].mark_seen.assert_called_once_with("job-001", "upwork")


@pytest.mark.asyncio
async def test_run_platform_appends_to_sheets():
    import main
    mocks = _patch_globals()
    with patch("main.get_scraper", return_value=mocks["scraper"]):
        await main.run_platform("upwork")

    mocks["sheets"].append_row.assert_called_once_with(SAMPLE_JOB, SAMPLE_RESULT, UPWORK_CONFIG)


@pytest.mark.asyncio
async def test_run_platform_evaluation_error_continues():
    import main
    mocks = _patch_globals()
    mocks["evaluator"].evaluate.side_effect = ValueError("Claude failed")
    with patch("main.get_scraper", return_value=mocks["scraper"]):
        summary = await main.run_platform("upwork")

    assert summary["evaluated"] == 0
    mocks["sheets"].append_row.assert_not_called()


@pytest.mark.asyncio
async def test_run_platform_sheets_error_does_not_stop_pipeline():
    import main
    mocks = _patch_globals()
    mocks["sheets"].append_row.side_effect = Exception("Sheets unavailable")
    with patch("main.get_scraper", return_value=mocks["scraper"]):
        summary = await main.run_platform("upwork")

    # Job still counted as evaluated, notifier still called
    assert summary["evaluated"] == 1
    mocks["notifier"].notify.assert_called_once()


@pytest.mark.asyncio
async def test_run_platform_updates_last_run_timestamp():
    import main
    mocks = _patch_globals()
    with patch("main.get_scraper", return_value=mocks["scraper"]):
        await main.run_platform("upwork")

    assert "upwork" in main._last_run
    assert main._last_run["upwork"].endswith("+00:00")


# ---------------------------------------------------------------------------
# API endpoints
# ---------------------------------------------------------------------------


@pytest.fixture()
def client(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-api-key")
    return TestClient(app, raise_server_exceptions=False)


def test_status_returns_scheduler_state(client):
    import main
    _patch_globals()
    main._scheduler = None  # no real scheduler in unit tests
    resp = client.get("/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["scheduler"] in ("running", "stopped")
    assert "platforms" in data


def test_run_requires_api_key(client):
    resp = client.post("/run?platform=upwork")
    assert resp.status_code == 401


def test_run_rejects_wrong_api_key(client):
    resp = client.post("/run?platform=upwork", headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401


def test_run_unknown_platform_returns_404(client, monkeypatch):
    import main
    _patch_globals()
    resp = client.post("/run?platform=unknown", headers={"X-API-Key": "test-api-key"})
    assert resp.status_code == 404


def test_run_single_platform_returns_ok(client):
    import main
    mocks = _patch_globals()
    with patch("main.get_scraper", return_value=mocks["scraper"]):
        resp = client.post("/run?platform=upwork", headers={"X-API-Key": "test-api-key"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["platforms"][0]["platform"] == "upwork"


def test_run_all_platforms_returns_ok(client):
    import main
    mocks = _patch_globals()
    with patch("main.get_scraper", return_value=mocks["scraper"]):
        resp = client.post("/run", headers={"X-API-Key": "test-api-key"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert len(data["platforms"]) == 1  # only upwork is in _patch_globals
