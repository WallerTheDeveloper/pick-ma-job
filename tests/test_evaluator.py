"""Unit tests for core.evaluator — LLMClient is mocked throughout."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.evaluator import EvaluationResult, Evaluator
from core.llm_client import LLMClient
from core.settings import Settings
from scrapers.base import NormalizedJob

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

BASE_PROFILE = {
    "system_instructions": "You are a job-fit evaluator. Return ONLY a raw JSON object.",
    "candidate": {"name": "Danylo", "role": "Unity Developer"},
    "skills": {"primary": ["Unity"], "secondary": ["Rust"], "tertiary": ["Vue.js"]},
    "scoring_rubric": {"9-10": "Excellent match"},
    "evaluation_factors": ["Skills Match"],
}

SETTINGS = Settings(
    claude_model="claude-haiku-4-5-20251001",
    claude_temperature=0.0,
)

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


def _make_anthropic_mock(response_text: str) -> MagicMock:
    """Return a mock AsyncAnthropic whose messages.create() returns response_text."""
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=response_text)]
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(return_value=mock_message)
    return mock_client


def _make_llm_mock(response_text: str) -> LLMClient:
    """Return an LLMClient wrapping a mock Anthropic client."""
    return LLMClient(
        client=_make_anthropic_mock(response_text),
        default_model="test-model",
    )


def _make_evaluator(mock_client_or_llm) -> Evaluator:
    """Create an Evaluator. Accepts either a MagicMock (Anthropic) or LLMClient."""
    if isinstance(mock_client_or_llm, LLMClient):
        return Evaluator(BASE_PROFILE, SETTINGS, llm_client=mock_client_or_llm)
    # Legacy: wrap an Anthropic mock in LLMClient
    llm = LLMClient(client=mock_client_or_llm, default_model="test-model")
    return Evaluator(BASE_PROFILE, SETTINGS, llm_client=llm)


# ---------------------------------------------------------------------------
# EvaluationResult
# ---------------------------------------------------------------------------


def test_evaluation_result_fields_populated():
    result = EvaluationResult.from_dict(VALID_RESPONSE)
    assert result.scratchpad == "Checking skills..."
    assert result.evaluation == "Strong Unity AR match."
    assert result.relevancy_score == 8
    assert result.recommendation == "Yes apply"
    assert result.flags == "Verified client, clear scope"
    assert result.summary == "Good AR fit."
    assert result.raw == VALID_RESPONSE


def test_evaluation_result_missing_fields_default_to_empty():
    result = EvaluationResult.from_dict({})
    assert result.scratchpad is None
    assert result.relevancy_score == 0


def test_evaluation_result_score_cast_to_int():
    result = EvaluationResult.from_dict({"relevancy_score": "7"})
    assert result.relevancy_score == 7
    assert isinstance(result.relevancy_score, int)


def test_evaluation_result_is_immutable():
    result = EvaluationResult.from_dict(VALID_RESPONSE)
    with pytest.raises(Exception):
        result.relevancy_score = 99  # type: ignore[misc]


def test_evaluation_result_raw_is_defensive_copy():
    original = {"relevancy_score": 5, "evaluation": "ok"}
    result = EvaluationResult.from_dict(original)
    original["relevancy_score"] = 99
    assert result.raw["relevancy_score"] == 5


# ---------------------------------------------------------------------------
# _assemble_user_message
# ---------------------------------------------------------------------------


def test_user_message_contains_job_fields():
    llm = _make_llm_mock("")
    evaluator = _make_evaluator(llm)
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
    llm = _make_llm_mock("")
    evaluator = _make_evaluator(llm)
    msg = evaluator._assemble_user_message(job, PLATFORM_CONTEXT)
    assert "N/A" in msg


# ---------------------------------------------------------------------------
# _assemble_system_prompt
# ---------------------------------------------------------------------------


def test_system_prompt_contains_platform_name():
    llm = _make_llm_mock("")
    evaluator = _make_evaluator(llm)
    prompt = evaluator._assemble_system_prompt(PLATFORM_CONTEXT)
    assert "upwork" in prompt.lower()


def test_system_prompt_contains_evaluation_notes():
    llm = _make_llm_mock("")
    evaluator = _make_evaluator(llm)
    prompt = evaluator._assemble_system_prompt(PLATFORM_CONTEXT)
    assert "Check payment verification." in prompt


def test_system_prompt_contains_system_instructions():
    llm = _make_llm_mock("")
    evaluator = _make_evaluator(llm)
    prompt = evaluator._assemble_system_prompt(PLATFORM_CONTEXT)
    assert "Return ONLY a raw JSON object" in prompt


# ---------------------------------------------------------------------------
# evaluate() — full integration with mocked LLMClient
# ---------------------------------------------------------------------------


import asyncio


def run(coro):
    return asyncio.run(coro)


def _make_sequential_anthropic_mock(texts: list[str]) -> MagicMock:
    """Mock returning texts in sequence (score, then full response)."""
    messages = []
    for t in texts:
        msg = MagicMock()
        msg.content = [MagicMock(text=t)]
        messages.append(msg)
    mock_client = MagicMock()
    mock_client.messages.create = AsyncMock(side_effect=messages)
    return mock_client


def _make_sequential_evaluator(texts: list[str]) -> Evaluator:
    """Create an evaluator whose underlying Anthropic mock returns texts in sequence."""
    mock_client = _make_sequential_anthropic_mock(texts)
    llm = LLMClient(client=mock_client, default_model="test-model")
    return Evaluator(BASE_PROFILE, SETTINGS, llm_client=llm)


def test_evaluate_returns_evaluation_result():
    evaluator = _make_sequential_evaluator([
        "8",  # Pass 1 score
        json.dumps(VALID_RESPONSE),  # Pass 2 full eval
    ])
    result = run(evaluator.evaluate(JOB, PLATFORM_CONTEXT))
    assert isinstance(result, EvaluationResult)
    assert result.relevancy_score == 8


def test_evaluate_low_score_skips_full_evaluation():
    """Jobs scoring below threshold return score-only result with a single API call."""
    mock_client = _make_sequential_anthropic_mock([
        "3",  # low score
        json.dumps(VALID_RESPONSE),  # should NOT be called
    ])
    llm = LLMClient(client=mock_client, default_model="test-model")
    evaluator = _make_evaluator(llm)
    result = run(evaluator.evaluate(JOB, PLATFORM_CONTEXT))
    assert result.relevancy_score == 3
    assert result.evaluation is None
    assert result.summary is None
    # Only one API call — full evaluation was skipped
    assert mock_client.messages.create.call_count == 1


def test_evaluate_raises_on_bad_json_response():
    evaluator = _make_sequential_evaluator([
        "8",  # Pass 1 score
        "not json",  # Pass 2 invalid
    ])
    with pytest.raises(Exception):  # LLMError from generate_json
        run(evaluator.evaluate(JOB, PLATFORM_CONTEXT))


def test_evaluate_parse_failure_skips_pass2():
    """When Pass 1 returns unparseable text, score falls below threshold and Pass 2 is skipped."""
    mock_client = _make_sequential_anthropic_mock([
        "I cannot rate this",  # unparseable Pass 1 response
        json.dumps(VALID_RESPONSE),  # should NOT be called
    ])
    llm = LLMClient(client=mock_client, default_model="test-model")
    evaluator = _make_evaluator(llm)
    result = run(evaluator.evaluate(JOB, PLATFORM_CONTEXT))
    # score_threshold is 5 (default), so fallback is 4
    assert result.relevancy_score == 4
    assert result.evaluation is None
    assert result.pass1_parse_failed is True
    # Only one API call — Pass 2 was skipped
    assert mock_client.messages.create.call_count == 1


def test_evaluate_parse_failure_logs_warning(caplog):
    """When Pass 1 returns unparseable text, a warning is logged with truncated raw response."""
    import logging

    mock_client = _make_sequential_anthropic_mock([
        "some gibberish response that is not a number",
    ])
    llm = LLMClient(client=mock_client, default_model="test-model")
    evaluator = _make_evaluator(llm)
    with caplog.at_level(logging.WARNING):
        run(evaluator.evaluate(JOB, PLATFORM_CONTEXT))
    assert any("pass1_parse_failed" in record.message for record in caplog.records)
