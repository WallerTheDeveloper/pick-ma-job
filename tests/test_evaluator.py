"""Unit tests for core.evaluator — LLMClient is mocked throughout."""

import json

import pytest

from core.evaluator import EvaluationResult, Evaluator
from core.llm_client import LLMClient, LLMResponse
from core.settings import Settings
from scrapers.base import NormalizedJob

# ---------------------------------------------------------------------------
# Mock providers
# ---------------------------------------------------------------------------


class MockProvider:
    """A mock LLMProvider that returns a fixed response on every call."""

    def __init__(self, response_text: str = "mock response") -> None:
        self._response_text = response_text
        self._index = 0

    async def complete(self, *, system, user, model, max_tokens=1024, temperature=0) -> LLMResponse:
        self._index += 1
        return LLMResponse(
            text=self._response_text,
            model=model,
            input_tokens=10,
            output_tokens=20,
            duration_ms=100,
        )


class SequentialProvider:
    """A mock provider that returns texts in sequence, then repeats the last."""

    def __init__(self, texts: list[str]) -> None:
        self._texts = list(texts)
        self._index = 0

    async def complete(self, *, system, user, model, max_tokens=1024, temperature=0) -> LLMResponse:
        idx = min(self._index, len(self._texts) - 1)
        text = self._texts[idx]
        self._index += 1
        return LLMResponse(
            text=text,
            model=model,
            input_tokens=10,
            output_tokens=20,
            duration_ms=100,
        )


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


def _make_llm_mock(response_text: str) -> LLMClient:
    """Return an LLMClient wrapping a MockProvider."""
    return LLMClient(
        provider=MockProvider(response_text),
        default_model="test-model",
    )


def _make_evaluator(llm_client: LLMClient) -> Evaluator:
    """Create an Evaluator backed by the given LLMClient."""
    return Evaluator(BASE_PROFILE, SETTINGS, llm_client=llm_client)


def _make_sequential_evaluator(texts: list[str]) -> Evaluator:
    """Create an evaluator whose underlying provider returns texts in sequence."""
    provider = SequentialProvider(texts)
    llm = LLMClient(provider=provider, default_model="test-model")
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
    provider = SequentialProvider([
        "3",  # low score
        json.dumps(VALID_RESPONSE),  # should NOT be called
    ])
    llm = LLMClient(provider=provider, default_model="test-model")
    evaluator = _make_evaluator(llm)
    result = run(evaluator.evaluate(JOB, PLATFORM_CONTEXT))
    assert result.relevancy_score == 3
    assert result.evaluation is None
    assert result.summary is None
    # Only one API call — full evaluation was skipped
    assert provider._index == 1


def test_evaluate_raises_on_bad_json_response():
    evaluator = _make_sequential_evaluator([
        "8",  # Pass 1 score
        "not json",  # Pass 2 invalid
    ])
    with pytest.raises(Exception):  # LLMError from generate_json
        run(evaluator.evaluate(JOB, PLATFORM_CONTEXT))


def test_evaluate_parse_failure_skips_pass2():
    """When Pass 1 returns unparseable text, score falls below threshold and Pass 2 is skipped."""
    provider = SequentialProvider([
        "I cannot rate this",  # unparseable Pass 1 response
        json.dumps(VALID_RESPONSE),  # should NOT be called
    ])
    llm = LLMClient(provider=provider, default_model="test-model")
    evaluator = _make_evaluator(llm)
    result = run(evaluator.evaluate(JOB, PLATFORM_CONTEXT))
    # score_threshold is 5 (default), so fallback is 4
    assert result.relevancy_score == 4
    assert result.evaluation is None
    assert result.pass1_parse_failed is True
    # Only one API call — Pass 2 was skipped
    assert provider._index == 1


def test_evaluate_parse_failure_logs_warning(caplog):
    """When Pass 1 returns unparseable text, a warning is logged with truncated raw response."""
    import logging

    evaluator = _make_sequential_evaluator([
        "some gibberish response that is not a number",
    ])
    with caplog.at_level(logging.WARNING):
        run(evaluator.evaluate(JOB, PLATFORM_CONTEXT))
    assert any("pass1_parse_failed" in record.message for record in caplog.records)


# ---------------------------------------------------------------------------
# evaluate_full() — Pass 2 with existing score (used for manual + bulk eval)
# ---------------------------------------------------------------------------


def test_evaluate_full_above_threshold_returns_full_result():
    """evaluate_full with a score above threshold calls LLM and returns full result."""
    evaluator = _make_sequential_evaluator([
        json.dumps(VALID_RESPONSE),  # Pass 2 full eval
    ])
    result = run(evaluator.evaluate_full(JOB, PLATFORM_CONTEXT, existing_score=8))
    assert result.relevancy_score == 8
    assert result.evaluation == "Strong Unity AR match."
    assert result.summary == "Good AR fit."


def test_evaluate_full_below_threshold_returns_score_only():
    """evaluate_full with a score below threshold returns score-only result without calling LLM."""
    provider = SequentialProvider([
        json.dumps(VALID_RESPONSE),  # should NOT be called
    ])
    llm = LLMClient(provider=provider, default_model="test-model")
    evaluator = _make_evaluator(llm)
    result = run(evaluator.evaluate_full(JOB, PLATFORM_CONTEXT, existing_score=3))
    assert result.relevancy_score == 3
    assert result.evaluation is None
    assert result.summary is None
    # No LLM call was made
    assert provider._index == 0


def test_evaluate_full_force_true_bypasses_threshold():
    """evaluate_full with force=True bypasses the threshold and runs Pass 2 even for low scores."""
    evaluator = _make_sequential_evaluator([
        json.dumps(VALID_RESPONSE),  # Pass 2 full eval
    ])
    result = run(evaluator.evaluate_full(JOB, PLATFORM_CONTEXT, existing_score=3, force=True))
    assert result.relevancy_score == 8
    assert result.evaluation == "Strong Unity AR match."
    assert result.summary == "Good AR fit."


def test_evaluate_full_force_true_logs_forced_evaluation(caplog):
    """evaluate_full with force=True on a low-score job logs the forced evaluation."""
    import logging

    evaluator = _make_sequential_evaluator([
        json.dumps(VALID_RESPONSE),  # Pass 2 full eval
    ])
    with caplog.at_level(logging.INFO):
        result = run(evaluator.evaluate_full(JOB, PLATFORM_CONTEXT, existing_score=3, force=True))
    assert result.relevancy_score == 8
    assert any(
        "Forced full evaluation" in record.message and "score=3" in record.message
        for record in caplog.records
    )


def test_evaluate_full_force_false_default_skips_low_score():
    """evaluate_full defaults force=False, so low scores skip Pass 2."""
    provider = SequentialProvider([
        json.dumps(VALID_RESPONSE),  # should NOT be called
    ])
    llm = LLMClient(provider=provider, default_model="test-model")
    evaluator = _make_evaluator(llm)
    result = run(evaluator.evaluate_full(JOB, PLATFORM_CONTEXT, existing_score=2))
    assert result.relevancy_score == 2
    assert result.evaluation is None
    assert provider._index == 0


def test_evaluate_full_force_true_high_score_no_extra_log(caplog):
    """evaluate_full with force=True on a high-score job does not log the forced-evaluation message."""
    import logging

    evaluator = _make_sequential_evaluator([
        json.dumps(VALID_RESPONSE),
    ])
    with caplog.at_level(logging.INFO):
        result = run(evaluator.evaluate_full(JOB, PLATFORM_CONTEXT, existing_score=8, force=True))
    assert result.relevancy_score == 8
    # The "Forced full evaluation" log should NOT appear for score >= threshold
    assert not any(
        "Forced full evaluation" in record.message
        for record in caplog.records
    )
