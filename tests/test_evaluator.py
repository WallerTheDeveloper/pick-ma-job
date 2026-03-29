"""Unit tests for core.evaluator — Anthropic client is mocked throughout."""

import json
from unittest.mock import MagicMock, patch

import pytest

from core.evaluator import EvaluationResult, Evaluator
from scrapers.base import NormalizedJob

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BASE_PROFILE = {
    "system_instructions": "You are a job-fit evaluator. Return ONLY a raw JSON object.",
    "developer": {"name": "Danylo", "role": "Unity Developer"},
    "skills": {"primary": ["Unity"], "secondary": ["Rust"], "tertiary": ["Vue.js"]},
    "scoring_rubric": {"9-10": "Excellent match"},
    "evaluation_factors": ["Skills Match"],
}

SETTINGS = {"model": "claude-haiku-4-5-20251001", "temperature": 0}

PLATFORM_CONTEXT = {
    "platform": "upwork",
    "evaluation_notes": ["Check payment verification."],
    "available_fields": ["title", "description", "budget"],
    "user_message_template": "Job Title: {title}\n\nDescription:\n{description}\n\nBudget: {budget}\nClient Rating: {client_rating}\nURL: {url}\n\nEvaluate this job.",
}

JOB = NormalizedJob(
    id="job-123",
    platform="upwork",
    title="Unity AR Developer",
    description="Build an AR app.",
    url="https://upwork.com/jobs/job-123",
    budget="$2,000",
    job_type="Fixed",
    experience_level="Intermediate",
    skills=["Unity", "ARCore"],
    extras={"client_rating": 4.9, "client_location": "United States"},
)

VALID_RESPONSE = {
    "scratchpad": "Checking skills...",
    "evaluation": "Strong Unity AR match.",
    "relevancy_score": 8,
    "recommendation": "Yes apply",
    "flags": "Verified client, clear scope",
    "summary": "Good AR fit.",
}


def _make_client_mock(response_text: str) -> MagicMock:
    """Return a mock Anthropic client whose messages.create() returns response_text."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=response_text)]
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message
    return mock_client


def _make_evaluator(mock_client: MagicMock) -> Evaluator:
    with patch("core.evaluator.anthropic.Anthropic", return_value=mock_client):
        return Evaluator(BASE_PROFILE, SETTINGS, api_key="test-key")


# ---------------------------------------------------------------------------
# EvaluationResult
# ---------------------------------------------------------------------------


def test_evaluation_result_fields_populated():
    result = EvaluationResult(VALID_RESPONSE)
    assert result.scratchpad == "Checking skills..."
    assert result.evaluation == "Strong Unity AR match."
    assert result.relevancy_score == 8
    assert result.recommendation == "Yes apply"
    assert result.flags == "Verified client, clear scope"
    assert result.summary == "Good AR fit."
    assert result.raw == VALID_RESPONSE


def test_evaluation_result_missing_fields_default_to_empty():
    result = EvaluationResult({})
    assert result.scratchpad == ""
    assert result.relevancy_score == 0


def test_evaluation_result_score_cast_to_int():
    result = EvaluationResult({"relevancy_score": "7"})
    assert result.relevancy_score == 7
    assert isinstance(result.relevancy_score, int)


# ---------------------------------------------------------------------------
# _parse_response
# ---------------------------------------------------------------------------


def test_parse_clean_json():
    mock_client = _make_client_mock("")
    evaluator = _make_evaluator(mock_client)
    result = evaluator._parse_response(json.dumps(VALID_RESPONSE))
    assert result["relevancy_score"] == 8


def test_parse_json_with_markdown_fences():
    fenced = f"```json\n{json.dumps(VALID_RESPONSE)}\n```"
    mock_client = _make_client_mock("")
    evaluator = _make_evaluator(mock_client)
    result = evaluator._parse_response(fenced)
    assert result["relevancy_score"] == 8


def test_parse_json_with_plain_fences():
    fenced = f"```\n{json.dumps(VALID_RESPONSE)}\n```"
    mock_client = _make_client_mock("")
    evaluator = _make_evaluator(mock_client)
    result = evaluator._parse_response(fenced)
    assert result["relevancy_score"] == 8


def test_parse_invalid_json_raises_value_error():
    mock_client = _make_client_mock("")
    evaluator = _make_evaluator(mock_client)
    with pytest.raises(ValueError, match="Claude returned invalid JSON"):
        evaluator._parse_response("not json at all")


# ---------------------------------------------------------------------------
# _assemble_user_message
# ---------------------------------------------------------------------------


def test_user_message_contains_job_fields():
    mock_client = _make_client_mock("")
    evaluator = _make_evaluator(mock_client)
    msg = evaluator._assemble_user_message(JOB, PLATFORM_CONTEXT)
    assert "Unity AR Developer" in msg
    assert "Build an AR app." in msg
    assert "$2,000" in msg
    assert "4.9" in msg
    assert "https://upwork.com/jobs/job-123" in msg


def test_user_message_none_fields_become_na():
    job = NormalizedJob(
        id="job-min", platform="upwork", title="Min Job",
        description="Desc", url="https://upwork.com/jobs/job-min",
    )
    mock_client = _make_client_mock("")
    evaluator = _make_evaluator(mock_client)
    msg = evaluator._assemble_user_message(job, PLATFORM_CONTEXT)
    assert "N/A" in msg


# ---------------------------------------------------------------------------
# _assemble_system_prompt
# ---------------------------------------------------------------------------


def test_system_prompt_contains_platform_name():
    mock_client = _make_client_mock("")
    evaluator = _make_evaluator(mock_client)
    prompt = evaluator._assemble_system_prompt(PLATFORM_CONTEXT)
    assert "upwork" in prompt.lower()


def test_system_prompt_contains_evaluation_notes():
    mock_client = _make_client_mock("")
    evaluator = _make_evaluator(mock_client)
    prompt = evaluator._assemble_system_prompt(PLATFORM_CONTEXT)
    assert "Check payment verification." in prompt


def test_system_prompt_contains_system_instructions():
    mock_client = _make_client_mock("")
    evaluator = _make_evaluator(mock_client)
    prompt = evaluator._assemble_system_prompt(PLATFORM_CONTEXT)
    assert "Return ONLY a raw JSON object" in prompt


# ---------------------------------------------------------------------------
# evaluate() — full integration with mocked client
# ---------------------------------------------------------------------------


import asyncio


def run(coro):
    return asyncio.run(coro)


def test_evaluate_returns_evaluation_result():
    mock_client = _make_client_mock(json.dumps(VALID_RESPONSE))
    evaluator = _make_evaluator(mock_client)
    result = run(evaluator.evaluate(JOB, PLATFORM_CONTEXT))
    assert isinstance(result, EvaluationResult)
    assert result.relevancy_score == 8


def test_evaluate_passes_correct_model_and_temperature():
    mock_client = _make_client_mock(json.dumps(VALID_RESPONSE))
    evaluator = _make_evaluator(mock_client)
    run(evaluator.evaluate(JOB, PLATFORM_CONTEXT))
    call_kwargs = mock_client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "claude-haiku-4-5-20251001"
    assert call_kwargs["temperature"] == 0


def test_evaluate_raises_on_bad_json_response():
    mock_client = _make_client_mock("not json")
    evaluator = _make_evaluator(mock_client)
    with pytest.raises(ValueError):
        run(evaluator.evaluate(JOB, PLATFORM_CONTEXT))
