"""Tests for configs/prompts/linkedin_context.json.

Verifies that the context file loads correctly and that a full mock evaluation
against a LinkedIn NormalizedJob produces valid JSON output via the Evaluator.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.evaluator import EvaluationResult, Evaluator
from core.llm_client import LLMClient
from core.prompt_adapter import load_platform_context
from scrapers.base import NormalizedJob

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BASE_PROFILE = {
    "system_instructions": "You are a job-fit evaluator. Return ONLY a raw JSON object.",
    "developer": {"role": "Unity Developer", "experience": "4 years", "rate": "€30/hr"},
    "skills": {"primary": ["Unity", "AR Foundation"], "secondary": ["Rust"], "tertiary": ["Vue.js"]},
    "not_a_good_fit": ["Pure frontend"],
    "scoring_rubric": {"9-10": "Excellent match"},
    "evaluation_factors": ["Skills Match", "Work Type"],
}

SETTINGS = {"model": "claude-haiku-4-5-20251001", "temperature": 0}

LINKEDIN_JOB = NormalizedJob(
    id="3987654321",
    platform="linkedin",
    title="Unity AR Developer",
    description="Build AR applications using Unity and AR Foundation for a Berlin startup.",
    url="https://www.linkedin.com/jobs/view/3987654321",
    skills=None,
    budget="$80,000/yr – $120,000/yr",
    job_type="Full-time",
    experience_level="Mid-Senior level",
    extras={
        "company_name": "Acme Corp",
        "location": "Berlin, Germany",
        "work_type": "Remote",
        "sector": "Technology",
        "applications_count": 42,
        "apply_type": "EASY_APPLY",
        "posted_time": "2 days ago",
        "poster_name": "Jane Smith",
        "company_url": "https://www.linkedin.com/company/acme-corp",
    },
)

VALID_CLAUDE_RESPONSE = json.dumps({
    "scratchpad": "Unity AR role in Berlin, remote, salary range provided.",
    "evaluation": "Strong match — Unity and AR Foundation are primary skills.",
    "relevancy_score": 8,
    "recommendation": "Yes apply",
    "flags": "Remote, clear scope, salary provided",
    "summary": "Excellent AR/Unity fit at a Berlin tech startup.",
})


def _make_client_mock(score_text: str, full_response_text: str) -> MagicMock:
    """Mock returning score on first call, full response on second."""
    score_message = MagicMock()
    score_message.content = [MagicMock(text=score_text)]

    full_message = MagicMock()
    full_message.content = [MagicMock(text=full_response_text)]

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=[score_message, full_message])
    return mock_client


def _make_evaluator(score_text: str, full_response_text: str) -> Evaluator:
    """Create an Evaluator backed by a mock Anthropic client."""
    mock_client = _make_client_mock(score_text, full_response_text)
    llm = LLMClient(client=mock_client, default_model="test-model")
    return Evaluator(BASE_PROFILE, SETTINGS, llm_client=llm)


# ---------------------------------------------------------------------------
# Context file structure
# ---------------------------------------------------------------------------


def test_linkedin_context_loads_without_error():
    ctx = load_platform_context("linkedin")
    assert isinstance(ctx, dict)


def test_linkedin_context_has_required_keys():
    ctx = load_platform_context("linkedin")
    assert ctx["platform"] == "linkedin"
    assert "evaluation_notes" in ctx
    assert "available_fields" in ctx
    assert "user_message_template" in ctx


def test_linkedin_context_evaluation_notes_is_non_empty_list():
    ctx = load_platform_context("linkedin")
    assert isinstance(ctx["evaluation_notes"], list)
    assert len(ctx["evaluation_notes"]) > 0


def test_linkedin_context_covers_no_skills_note():
    ctx = load_platform_context("linkedin")
    notes_text = " ".join(ctx["evaluation_notes"]).lower()
    assert "skills" in notes_text


def test_linkedin_context_covers_applications_count_note():
    ctx = load_platform_context("linkedin")
    notes_text = " ".join(ctx["evaluation_notes"])
    assert "applications_count" in notes_text


def test_linkedin_context_covers_work_type_note():
    ctx = load_platform_context("linkedin")
    notes_text = " ".join(ctx["evaluation_notes"]).lower()
    assert "work_type" in notes_text


def test_linkedin_context_available_fields_includes_extras():
    ctx = load_platform_context("linkedin")
    fields = ctx["available_fields"]
    for expected in [
        "company_name", "location", "work_type", "sector",
        "applications_count", "apply_type", "posted_time",
        "poster_name", "company_url",
    ]:
        assert expected in fields, f"Missing field: {expected}"


def test_linkedin_context_template_references_all_extras():
    ctx = load_platform_context("linkedin")
    template = ctx["user_message_template"]
    for extra in [
        "company_name", "location", "work_type", "sector",
        "applications_count", "apply_type", "posted_time",
        "poster_name", "company_url",
    ]:
        assert f"{{{extra}}}" in template, f"Template missing placeholder: {{{extra}}}"


def test_linkedin_context_template_references_budget():
    """budget is how the evaluator exposes job.budget (salaryInfo)."""
    ctx = load_platform_context("linkedin")
    assert "{budget}" in ctx["user_message_template"]


# ---------------------------------------------------------------------------
# End-to-end mock evaluation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mock_evaluation_produces_valid_evaluation_result():
    """Full pipeline: LinkedIn context + NormalizedJob → EvaluationResult."""
    ctx = load_platform_context("linkedin")
    evaluator = _make_evaluator(score_text="8", full_response_text=VALID_CLAUDE_RESPONSE)

    result = await evaluator.evaluate(LINKEDIN_JOB, ctx)

    assert isinstance(result, EvaluationResult)
    assert result.relevancy_score == 8
    assert result.evaluation is not None
    assert result.recommendation is not None
    assert result.summary is not None


@pytest.mark.asyncio
async def test_mock_evaluation_user_message_interpolates_extras():
    """Verify all LinkedIn extras reach the assembled user message."""
    ctx = load_platform_context("linkedin")

    captured_calls = []

    async def capture_create(**kwargs):
        captured_calls.append(kwargs)
        msg = MagicMock()
        if len(captured_calls) == 1:
            msg.content = [MagicMock(text="8")]
        else:
            msg.content = [MagicMock(text=VALID_CLAUDE_RESPONSE)]
        return msg

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=capture_create)

    llm = LLMClient(client=mock_client, default_model="test-model")
    evaluator = Evaluator(BASE_PROFILE, SETTINGS, llm_client=llm)

    await evaluator.evaluate(LINKEDIN_JOB, ctx)

    # The second call is the full evaluation — check its user message
    assert len(captured_calls) == 2
    user_msg = captured_calls[1]["messages"][0]["content"]
    assert "Acme Corp" in user_msg
    assert "Berlin, Germany" in user_msg
    assert "Remote" in user_msg
    assert "Technology" in user_msg
    assert "42" in user_msg
    assert "EASY_APPLY" in user_msg
    assert "Jane Smith" in user_msg
    assert "$80,000/yr – $120,000/yr" in user_msg


@pytest.mark.asyncio
async def test_low_score_linkedin_job_skips_full_evaluation():
    """Jobs scoring below threshold return score-only result."""
    ctx = load_platform_context("linkedin")
    evaluator = _make_evaluator(score_text="2", full_response_text=VALID_CLAUDE_RESPONSE)

    result = await evaluator.evaluate(LINKEDIN_JOB, ctx)

    assert result.relevancy_score == 2
    assert result.evaluation is None
    assert result.summary is None


@pytest.mark.asyncio
async def test_linkedin_job_with_no_extras_renders_na():
    """Minimal LinkedIn job (no extras) renders N/A for missing template placeholders."""
    ctx = load_platform_context("linkedin")
    minimal_job = NormalizedJob(
        id="min-1",
        platform="linkedin",
        title="Unity Developer",
        description="Basic Unity role.",
        url="https://www.linkedin.com/jobs/view/min-1",
        skills=None,
        budget=None,
        job_type=None,
        experience_level=None,
        extras={},
    )

    captured_calls = []

    async def capture_create(**kwargs):
        captured_calls.append(kwargs)
        msg = MagicMock()
        if len(captured_calls) == 1:
            msg.content = [MagicMock(text="7")]
        else:
            msg.content = [MagicMock(text=VALID_CLAUDE_RESPONSE)]
        return msg

    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=capture_create)

    llm = LLMClient(client=mock_client, default_model="test-model")
    evaluator = Evaluator(BASE_PROFILE, SETTINGS, llm_client=llm)

    result = await evaluator.evaluate(minimal_job, ctx)

    assert isinstance(result, EvaluationResult)
    user_msg = captured_calls[1]["messages"][0]["content"]
    # All missing extras should fall back to N/A
    assert "N/A" in user_msg
