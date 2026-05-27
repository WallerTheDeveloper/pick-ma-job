"""Integration tests for /api/results/{id}/evaluate and /api/results/evaluate-bulk endpoints.

Tests the T03 change: manual evaluation bypasses the score threshold (force=True),
while bulk evaluation still skips low-score jobs.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from api.csrf import require_csrf
from api.deps import (
    get_current_user,
    get_job_result_repo,
    get_llm_client,
    get_profile_repo,
    get_settings,
)
from core.llm_client import LLMClient, LLMResponse
from core.settings import Settings
from repositories.job_result import JobResultRow
from repositories.profile import ProfileRow
from repositories.user import UserRow


def _make_user(email: str = "user@example.com") -> UserRow:
    return UserRow(id=uuid4(), email=email, created_at=datetime.now(timezone.utc), last_login=None)


def _make_result(
    user_id: uuid4,
    result_id: uuid4 | None = None,
    score: int | None = 3,
    evaluation: dict | None = None,
    platform: str = "upwork",
) -> JobResultRow:
    return JobResultRow(
        id=result_id or uuid4(),
        user_id=user_id,
        platform=platform,
        job_id=f"job-{uuid4().hex[:8]}",
        title="Test Job",
        url="https://upwork.com/jobs/test",
        score=score,
        evaluation=evaluation,
        status="new",
        created_at=datetime.now(timezone.utc),
    )


def _make_profile(user_id: uuid4) -> ProfileRow:
    return ProfileRow(
        id=uuid4(),
        user_id=user_id,
        role="Developer",
        experience="5 years",
        rate="$50/hr",
        primary_skills=["Python", "FastAPI"],
        secondary_skills=["JavaScript"],
        tertiary_skills=["DevOps"],
        not_a_good_fit=["Java"],
        background=["5 years backend development"],
        notable_projects=[{"name": "Project A", "description": "Built an API"}],
        languages=["English"],
        rubric={},
        cv_customize_threshold=7,
        exclude_keywords=[],
        updated_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def test_app(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://fake/fake")
    monkeypatch.setenv("MAGIC_LINK_SECRET", "test-secret")
    monkeypatch.setenv("RESEND_API_KEY", "re_test")
    monkeypatch.setenv("EMAIL_FROM", "test@example.com")
    monkeypatch.setenv("BASE_URL", "http://localhost:8000")
    monkeypatch.setenv("SKIP_EMAIL", "true")

    from main import create_app
    app = create_app()
    app.state.db_pool = MagicMock()
    app.state.run_manager = MagicMock()
    return app


@pytest.fixture
async def client(test_app):
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as c:
        yield c


def _clear_overrides(test_app):
    test_app.dependency_overrides.clear()


def _make_llm_client_mock(eval_raw: dict) -> MagicMock:
    """Create a mock LLMClient that returns the given evaluation dict."""
    mock_llm = MagicMock(spec=LLMClient)
    llm_response = LLMResponse(
        text=json.dumps(eval_raw),
        model="test-model",
        input_tokens=100,
        output_tokens=200,
        duration_ms=500,
    )
    mock_llm.generate_json_with_metadata = AsyncMock(return_value=(eval_raw, llm_response))
    return mock_llm


# ── POST /api/results/{id}/evaluate ───────────────────────────────────


@pytest.mark.asyncio
async def test_evaluate_low_score_job_returns_200(test_app, client):
    """Manual evaluation of a low-score job should succeed with force=True (T03)."""
    user = _make_user()
    result_id = uuid4()
    low_score_result = _make_result(user_id=user.id, result_id=result_id, score=3, evaluation=None)
    profile = _make_profile(user_id=user.id)

    mock_repo = AsyncMock()
    mock_repo.find_by_id_and_user.return_value = low_score_result
    mock_repo.update_evaluation.return_value = _make_result(
        user_id=user.id,
        result_id=result_id,
        score=3,
        evaluation={"scratchpad": "...", "evaluation": "Some match", "relevancy_score": 3,
                     "recommendation": "Consider", "flags": "Low budget", "summary": "Low-score job"},
    )

    mock_profile_repo = AsyncMock()
    mock_profile_repo.find_by_user_id.return_value = profile

    eval_raw = {
        "scratchpad": "Checking...",
        "evaluation": "Some match",
        "relevancy_score": 3,
        "recommendation": "Consider",
        "flags": "Low budget",
        "summary": "Low-score job but forced eval",
    }
    mock_llm = _make_llm_client_mock(eval_raw)

    settings = Settings(claude_model="test-model", claude_temperature=0.0)

    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[require_csrf] = lambda: None
    test_app.dependency_overrides[get_job_result_repo] = lambda: mock_repo
    test_app.dependency_overrides[get_profile_repo] = lambda: mock_profile_repo
    test_app.dependency_overrides[get_llm_client] = lambda: mock_llm
    test_app.dependency_overrides[get_settings] = lambda: settings

    platform_context = {
        "platform": "upwork",
        "evaluation_notes": ["Check budget carefully"],
        "available_fields": ["title", "description", "budget"],
        "user_message_template": "Job: {title}\n{description}",
    }

    try:
        with patch("api.routes.api_results.load_platform_context", return_value=platform_context):
            resp = await client.post(f"/api/results/{result_id}/evaluate")
        assert resp.status_code == 200
        data = resp.json()
        assert data["result"]["evaluation"] is not None
        assert data["result"]["score"] == 3
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_evaluate_already_evaluated_returns_409(test_app, client):
    """Already-evaluated jobs should return 409 (conflict)."""
    user = _make_user()
    result_id = uuid4()
    already_evaluated = _make_result(
        user_id=user.id,
        result_id=result_id,
        score=8,
        evaluation={"evaluation": "Good match", "relevancy_score": 8},
    )

    mock_repo = AsyncMock()
    mock_repo.find_by_id_and_user.return_value = already_evaluated

    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[require_csrf] = lambda: None
    test_app.dependency_overrides[get_job_result_repo] = lambda: mock_repo

    try:
        resp = await client.post(f"/api/results/{result_id}/evaluate")
        assert resp.status_code == 409
        assert "already evaluated" in resp.json()["detail"].lower()
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_evaluate_no_score_returns_422(test_app, client):
    """Jobs without a score should return 422."""
    user = _make_user()
    result_id = uuid4()
    no_score_result = _make_result(user_id=user.id, result_id=result_id, score=None)

    mock_repo = AsyncMock()
    mock_repo.find_by_id_and_user.return_value = no_score_result

    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[require_csrf] = lambda: None
    test_app.dependency_overrides[get_job_result_repo] = lambda: mock_repo

    try:
        resp = await client.post(f"/api/results/{result_id}/evaluate")
        assert resp.status_code == 422
        assert "no score" in resp.json()["detail"].lower()
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_evaluate_not_found_returns_404(test_app, client):
    """Non-existent result should return 404."""
    user = _make_user()

    mock_repo = AsyncMock()
    mock_repo.find_by_id_and_user.return_value = None

    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[require_csrf] = lambda: None
    test_app.dependency_overrides[get_job_result_repo] = lambda: mock_repo

    try:
        resp = await client.post(f"/api/results/{uuid4()}/evaluate")
        assert resp.status_code == 404
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_evaluate_unauthenticated_returns_401(test_app, client):
    """Unauthenticated requests should return 401."""
    resp = await client.post(f"/api/results/{uuid4()}/evaluate")
    assert resp.status_code == 401


# ── POST /api/results/evaluate-bulk ───────────────────────────────────


@pytest.mark.asyncio
async def test_evaluate_bulk_with_result_ids(test_app, client):
    """Bulk evaluation with explicit result_ids should evaluate and return counts."""
    user = _make_user()
    profile = _make_profile(user_id=user.id)

    result_id_1 = uuid4()
    result_id_2 = uuid4()
    result_1 = _make_result(user_id=user.id, result_id=result_id_1, score=7, evaluation=None)
    result_2 = _make_result(user_id=user.id, result_id=result_id_2, score=8, evaluation=None)

    mock_repo = AsyncMock()
    mock_repo.find_by_id_and_user.side_effect = [result_1, result_2]
    mock_repo.update_evaluation.side_effect = [
        _make_result(user_id=user.id, result_id=result_id_1, score=7,
                     evaluation={"evaluation": "Good", "relevancy_score": 7, "summary": "Good match"}),
        _make_result(user_id=user.id, result_id=result_id_2, score=8,
                     evaluation={"evaluation": "Great", "relevancy_score": 8, "summary": "Great match"}),
    ]

    mock_profile_repo = AsyncMock()
    mock_profile_repo.find_by_user_id.return_value = profile

    eval_raw = {
        "scratchpad": "...",
        "evaluation": "Good match",
        "relevancy_score": 7,
        "recommendation": "Apply",
        "flags": "None",
        "summary": "Good match for the role",
    }
    mock_llm = _make_llm_client_mock(eval_raw)

    settings = Settings(claude_model="test-model", claude_temperature=0.0)

    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[require_csrf] = lambda: None
    test_app.dependency_overrides[get_job_result_repo] = lambda: mock_repo
    test_app.dependency_overrides[get_profile_repo] = lambda: mock_profile_repo
    test_app.dependency_overrides[get_llm_client] = lambda: mock_llm
    test_app.dependency_overrides[get_settings] = lambda: settings

    platform_context = {
        "platform": "upwork",
        "evaluation_notes": ["Check budget"],
        "available_fields": ["title", "description"],
        "user_message_template": "Job: {title}\n{description}",
    }

    try:
        with patch("api.routes.api_results.load_platform_context", return_value=platform_context):
            resp = await client.post(
                "/api/results/evaluate-bulk",
                json={"result_ids": [str(result_id_1), str(result_id_2)]},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["evaluated"] == 2
        assert data["failed"] == 0
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_evaluate_bulk_skips_low_score(test_app, client):
    """Bulk evaluation should skip jobs below the score threshold (force=False)."""
    user = _make_user()
    profile = _make_profile(user_id=user.id)

    result_id = uuid4()
    low_score_result = _make_result(user_id=user.id, result_id=result_id, score=3, evaluation=None)

    mock_repo = AsyncMock()
    mock_repo.find_by_id_and_user.return_value = low_score_result

    mock_profile_repo = AsyncMock()
    mock_profile_repo.find_by_user_id.return_value = profile

    # LLM returns a low score - evaluator will skip full eval
    mock_llm = MagicMock(spec=LLMClient)
    settings = Settings(claude_model="test-model", claude_temperature=0.0, score_threshold=5)

    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[require_csrf] = lambda: None
    test_app.dependency_overrides[get_job_result_repo] = lambda: mock_repo
    test_app.dependency_overrides[get_profile_repo] = lambda: mock_profile_repo
    test_app.dependency_overrides[get_llm_client] = lambda: mock_llm
    test_app.dependency_overrides[get_settings] = lambda: settings

    platform_context = {
        "platform": "upwork",
        "evaluation_notes": [],
        "available_fields": ["title"],
        "user_message_template": "Job: {title}",
    }

    try:
        with patch("api.routes.api_results.load_platform_context", return_value=platform_context):
            resp = await client.post(
                "/api/results/evaluate-bulk",
                json={"result_ids": [str(result_id)]},
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["skipped_low_score"] == 1
        assert data["evaluated"] == 0
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_evaluate_bulk_no_ids_no_filter_returns_422(test_app, client):
    """Bulk evaluation without result_ids or filter should return 422."""
    user = _make_user()

    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[require_csrf] = lambda: None

    try:
        resp = await client.post("/api/results/evaluate-bulk", json={})
        assert resp.status_code == 422
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_evaluate_bulk_empty_ids_returns_zero(test_app, client):
    """Bulk evaluation with empty result_ids should return zero counts."""
    user = _make_user()

    mock_repo = AsyncMock()

    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[require_csrf] = lambda: None
    test_app.dependency_overrides[get_job_result_repo] = lambda: mock_repo

    try:
        resp = await client.post(
            "/api/results/evaluate-bulk",
            json={"result_ids": []},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0
        assert data["evaluated"] == 0
    finally:
        _clear_overrides(test_app)


@pytest.mark.asyncio
async def test_evaluate_bulk_unauthenticated_returns_401(test_app, client):
    """Unauthenticated bulk evaluation should return 401."""
    resp = await client.post(
        "/api/results/evaluate-bulk",
        json={"result_ids": [str(uuid4())]},
    )
    assert resp.status_code == 401
