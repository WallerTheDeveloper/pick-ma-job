"""Integration tests for the CV humanization pipeline.

These tests verify the full CVService.customize_cv() flow with mocked
LLM providers — no real API calls are made.

Tests cover:
- Full pipeline with humanization (Passes 1-5)
- Pipeline without humanization (humanize=False, only Pass 1)
- Skeleton extraction from Pass 1 results
- Keyword patch application
- Post-processing (AI tell removal, sentence variety)
- Fabrication verification still catches issues after humanization
- Cached result bypasses pipeline
- force_regenerate re-runs the full pipeline
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from core.llm_client import LLMClient, LLMError, MultiModelLLMClient
from core.llm_provider import LLMResponse
from repositories.cv import CVRow
from repositories.cv_customization import CVCustomizationRow
from repositories.job_result import JobResultRow
from services.cv_service import (
    CVService,
    _diff_to_full_text,
    _verify_customization,
    _extract_verified_fields,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

USER_ID = uuid4()
JOB_RESULT_ID = uuid4()
CV_ID = uuid4()
NOW = "2024-01-15T12:00:00+00:00"


def _make_provider(response_text: str = "mock response") -> MagicMock:
    """Create a mock LLMProvider that records calls and returns fixed text."""
    provider = MagicMock()

    async def _complete(*, system: str, user: str, model: str, max_tokens: int = 1024, temperature: float = 0) -> LLMResponse:
        provider.calls.append({
            "system": system,
            "user": user,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
        })
        return LLMResponse(
            text=response_text,
            model=model,
            input_tokens=10,
            output_tokens=20,
            duration_ms=100,
        )

    provider.complete = _complete
    provider.calls = []
    return provider


class SequentialProvider:
    """A provider that returns a sequence of responses, then repeats the last."""

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self._index = 0
        self.calls: list[dict] = []

    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0,
    ) -> LLMResponse:
        self.calls.append({
            "system": system,
            "user": user,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
        })
        idx = min(self._index, len(self._responses) - 1)
        text = self._responses[idx]
        self._index += 1
        return LLMResponse(
            text=text,
            model=model,
            input_tokens=10,
            output_tokens=20,
            duration_ms=100,
        )


def _sample_cv_structured() -> dict:
    """Return a realistic structured CV payload."""
    return {
        "name": "Jane Developer",
        "email": "jane@example.com",
        "skills": {
            "primary": ["Python", "FastAPI", "PostgreSQL"],
            "secondary": ["Docker", "React"],
            "tertiary": ["AWS"],
        },
        "languages": ["English", "Spanish"],
        "certifications": ["AWS Certified Solutions Architect"],
        "experience": [
            {"company": "TechCorp", "title": "Senior Developer", "duration": "2020-2023"},
        ],
        "education": ["B.S. Computer Science"],
    }


def _sample_job_result() -> JobResultRow:
    """Return a sample JobResultRow with a qualifying score."""
    return JobResultRow(
        id=JOB_RESULT_ID,
        user_id=USER_ID,
        platform="upwork",
        job_id="job-123",
        title="Python Backend Developer",
        url="https://example.com/job/123",
        score=8,
        evaluation={
            "evaluation": "Strong match for Python backend role.",
            "recommendation": "Apply",
            "flags": "",
        },
        status="new",
        created_at="2024-01-14T10:00:00+00:00",  # type: ignore[arg-type]
    )


def _sample_cv_row() -> CVRow:
    """Return a sample CVRow."""
    return CVRow(
        id=CV_ID,
        user_id=USER_ID,
        filename="jane_cv.pdf",
        raw_text="Jane Developer\nSenior Developer at TechCorp\nPython, FastAPI, PostgreSQL",
        structured=_sample_cv_structured(),
        created_at="2024-01-13T09:00:00+00:00",  # type: ignore[arg-type]
        updated_at="2024-01-13T09:00:00+00:00",  # type: ignore[arg-type]
    )


# Sample LLM responses for the full pipeline:

OPTIMIZE_RESPONSE = json.dumps({
    "sections": [
        {"title": "SUMMARY", "content": "Furthermore, I leveraged cutting-edge Python and FastAPI to streamline backend systems. Additionally, I spearheaded the migration project.", "changed": True},
        {"title": "EXPERIENCE", "content": "Led the backend team utilizing Docker and PostgreSQL. Orchestrated microservices architecture for high-availability systems.", "changed": True},
        {"title": "SKILLS", "content": "Python, FastAPI, PostgreSQL, Docker, AWS", "changed": False},
        {"title": "LANGUAGES", "content": "English, Spanish", "changed": False},
    ]
})

HUMANIZE_RESPONSE = json.dumps({
    "sections": [
        {"title": "SUMMARY", "content": "Also, I used modern Python and FastAPI to simplify backend systems. And I led the migration project.", "changed": True},
        {"title": "EXPERIENCE", "content": "Led the backend team using Docker and PostgreSQL. Managed microservices architecture for high-availability systems.", "changed": True},
        {"title": "SKILLS", "content": "Python, FastAPI, PostgreSQL, Docker, AWS", "changed": False},
        {"title": "LANGUAGES", "content": "English, Spanish", "changed": False},
    ]
})

KEYWORD_AUDIT_RESPONSE = json.dumps({
    "present": ["Python"],
    "missing": ["FastAPI"],
    "forced": [],
    "patches": [
        {
            "section": "SUMMARY",
            "original_sentence": "Also, I used modern Python and FastAPI to simplify backend systems.",
            "new_sentence": "Also, I used modern Python and FastAPI to simplify backend systems, including REST APIs.",
        }
    ]
})

VOICE_FRAGMENTS_RESPONSE = json.dumps({
    "fragments": [
        {"section": "SUMMARY", "voice": "Really a backend person who spent years neck-deep in Python and FastAPI. The API work was honestly the most fun."},
        {"section": "EXPERIENCE", "voice": "The backend team stuff was where I learned the most. Shipping microservices at scale is always harder than people think."},
        {"section": "SKILLS", "voice": "Python and FastAPI are what I use daily. Docker is pretty much second nature."},
        {"section": "EDUCATION", "voice": "Got my CS degree mostly because the math classes were genuinely interesting."},
    ]
})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_repos():
    """Create mock repositories."""
    cv_repo = MagicMock()
    cv_customization_repo = MagicMock()
    job_result_repo = MagicMock()
    return cv_repo, cv_customization_repo, job_result_repo


@pytest.fixture
def mock_multi_client():
    """Create a MultiModelLLMClient with sequential mock providers for the 3 LLM passes."""
    optimize_provider = SequentialProvider([OPTIMIZE_RESPONSE])
    humanize_provider = SequentialProvider([VOICE_FRAGMENTS_RESPONSE])
    audit_provider = SequentialProvider([KEYWORD_AUDIT_RESPONSE])

    optimize_client = LLMClient(provider=optimize_provider, default_model="haiku-model", default_temperature=0)
    humanize_client = LLMClient(provider=humanize_provider, default_model="sonnet-model", default_temperature=0.3)
    audit_client = LLMClient(provider=audit_provider, default_model="haiku-model", default_temperature=0)

    multi = MultiModelLLMClient(clients={
        "optimize": optimize_client,
        "humanize": humanize_client,
        "keyword_audit": audit_client,
    })

    return multi, optimize_provider, humanize_provider, audit_provider


@pytest.fixture
def cv_service(mock_repos, mock_multi_client):
    """Create a CVService with mocked repos and LLM client."""
    cv_repo, cv_customization_repo, job_result_repo = mock_repos
    multi, _, _, _ = mock_multi_client
    return CVService(
        cv_repo=cv_repo,
        cv_customization_repo=cv_customization_repo,
        job_result_repo=job_result_repo,
        llm_client=multi,
    ), multi


# ---------------------------------------------------------------------------
# Test: customize_cv_with_humanization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_customize_cv_with_humanization(cv_service, mock_repos):
    """Full pipeline with humanization: verify LLM calls are made for all passes."""
    service, multi = cv_service
    cv_repo, cv_customization_repo, job_result_repo = mock_repos

    job = _sample_job_result()
    cv = _sample_cv_row()

    job_result_repo.find_by_id_and_user = AsyncMock(return_value=job)
    cv_repo.find_by_user = AsyncMock(return_value=cv)
    cv_customization_repo.find_by_user_and_job = AsyncMock(return_value=None)
    cv_customization_repo.upsert = AsyncMock(return_value=MagicMock())

    text, from_cache, warnings, sections = await service.customize_cv(
        user_id=USER_ID,
        job_result_id=JOB_RESULT_ID,
        humanize=True,
    )

    assert from_cache is False
    assert isinstance(text, str)
    assert len(text) > 0
    # The humanization pipeline should have transformed AI tells
    # "Furthermore" should have been removed by postprocess_humanization
    assert "Furthermore" not in text
    # "leveraged" should have been replaced
    assert "leveraged" not in text

    # Verify all 3 LLM providers were called (optimize, humanize, keyword_audit)
    optimize_client = multi.for_pass("optimize")
    humanize_client = multi.for_pass("humanize")
    audit_client = multi.for_pass("keyword_audit")

    opt_provider = optimize_client.provider  # type: ignore[attr-defined]
    hum_provider = humanize_client.provider  # type: ignore[attr-defined]
    audit_provider = audit_client.provider  # type: ignore[attr-defined]

    assert len(opt_provider.calls) >= 1  # at least the optimize call
    assert len(hum_provider.calls) >= 1  # at least the humanize call
    assert len(audit_provider.calls) >= 1  # at least the keyword audit call


# ---------------------------------------------------------------------------
# Test: customize_cv_without_humanization
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_customize_cv_without_humanization(cv_service, mock_repos):
    """With humanize=False, only Pass 1 (optimize) runs."""
    service, multi = cv_service
    cv_repo, cv_customization_repo, job_result_repo = mock_repos

    job = _sample_job_result()
    cv = _sample_cv_row()

    job_result_repo.find_by_id_and_user = AsyncMock(return_value=job)
    cv_repo.find_by_user = AsyncMock(return_value=cv)
    cv_customization_repo.find_by_user_and_job = AsyncMock(return_value=None)
    cv_customization_repo.upsert = AsyncMock(return_value=MagicMock())

    text, from_cache, warnings, sections = await service.customize_cv(
        user_id=USER_ID,
        job_result_id=JOB_RESULT_ID,
        humanize=False,
    )

    assert from_cache is False
    assert isinstance(text, str)
    assert len(text) > 0

    # Only optimize provider should have been called
    optimize_client = multi.for_pass("optimize")
    humanize_client = multi.for_pass("humanize")
    audit_client = multi.for_pass("keyword_audit")

    opt_provider = optimize_client.provider  # type: ignore[attr-defined]
    hum_provider = humanize_client.provider  # type: ignore[attr-defined]
    audit_provider = audit_client.provider  # type: ignore[attr-defined]

    assert len(opt_provider.calls) >= 1  # optimize call happened
    assert len(hum_provider.calls) == 0  # no humanize call
    assert len(audit_provider.calls) == 0  # no audit call


# ---------------------------------------------------------------------------
# Test: skeleton extraction
# ---------------------------------------------------------------------------


def test_skeleton_extraction():
    """_extract_skeleton produces correct target_keywords, must_include_facts, and positioning."""
    optimize_result = {
        "sections": [
            {"title": "SUMMARY", "content": "Experienced Python developer with 5 years building FastAPI backends. Led team of 8.", "changed": True},
            {"title": "EXPERIENCE", "content": "Senior Dev at TechCorp. Built microservices with Docker and PostgreSQL.", "changed": True},
        ]
    }
    cv_structured = _sample_cv_structured()
    job_description = "Looking for a Python FastAPI developer experienced with Docker and PostgreSQL."

    # Create a minimal CVService just for calling _extract_skeleton
    mock_llm = MultiModelLLMClient(clients={"optimize": LLMClient(provider=SequentialProvider([OPTIMIZE_RESPONSE]), default_model="test-model")})
    service = CVService(
        cv_repo=MagicMock(),
        cv_customization_repo=MagicMock(),
        job_result_repo=MagicMock(),
        llm_client=mock_llm,
    )

    skeleton = service._extract_skeleton(optimize_result, cv_structured, job_description)

    # Target keywords should include Python, FastAPI, Docker, PostgreSQL
    keywords_lower = [kw.lower() for kw in skeleton["target_keywords"]]
    assert "python" in keywords_lower
    assert "fastapi" in keywords_lower

    # Must-include facts should have entries with numbers
    assert len(skeleton["must_include_facts"]) > 0

    # Positioning should be extracted from SUMMARY
    assert len(skeleton["positioning"]) > 0

    # Verified fields should be populated
    assert skeleton["verified_skills"] != ""
    assert skeleton["verified_languages"] != ""

    # sections_json should be valid JSON
    parsed = json.loads(skeleton["sections_json"])
    assert "sections" in parsed


# ---------------------------------------------------------------------------
# Test: keyword patch application
# ---------------------------------------------------------------------------


def test_keyword_patch_application():
    """_apply_keyword_patches correctly applies audit patches to sections."""
    diff = {
        "sections": [
            {"title": "SUMMARY", "content": "I used Python and FastAPI to build systems.", "changed": True},
            {"title": "EXPERIENCE", "content": "Led the backend team for high-availability systems.", "changed": True},
        ]
    }
    audit = {
        "present": ["Python"],
        "missing": ["Docker"],
        "forced": [],
        "patches": [
            {
                "section": "SUMMARY",
                "original_sentence": "I used Python and FastAPI to build systems.",
                "new_sentence": "I used Python and FastAPI to build systems, including Docker deployment.",
            }
        ],
    }

    # Create a minimal CVService for calling _apply_keyword_patches
    mock_llm = MultiModelLLMClient(clients={"optimize": LLMClient(provider=SequentialProvider([OPTIMIZE_RESPONSE]), default_model="test-model")})
    service = CVService(
        cv_repo=MagicMock(),
        cv_customization_repo=MagicMock(),
        job_result_repo=MagicMock(),
        llm_client=mock_llm,
    )

    result = service._apply_keyword_patches(diff, audit)

    # The SUMMARY section should have the patched content
    summary_section = next(s for s in result["sections"] if s["title"] == "SUMMARY")
    assert "Docker deployment" in summary_section["content"]
    assert summary_section["changed"] is True


# ---------------------------------------------------------------------------
# Test: postprocess_humanization
# ---------------------------------------------------------------------------


def test_postprocess_humanization():
    """Post-processing removes AI tells and enforces sentence variety."""
    from core.humanizer import postprocess_humanization

    text = (
        "Furthermore, I leveraged cutting-edge technology to streamline the workflow. "
        "Additionally, I spearheaded the project. Moreover, I orchestrated the deployment. "
        "I do not think the team is not capable."
    )
    result = postprocess_humanization(text)

    # AI tells should be removed
    assert "Furthermore" not in result
    assert "leveraged" not in result
    assert "cutting-edge" not in result
    assert "streamlined" not in result
    assert "Additionally" not in result
    assert "spearheaded" not in result

    # Should be a non-empty string
    assert len(result) > 0


# ---------------------------------------------------------------------------
# Test: verification catches fabrication after humanization
# ---------------------------------------------------------------------------


def test_verification_still_catches_fabrication():
    """_verify_customization still catches fabricated certs and languages after humanization."""
    cv_structured = _sample_cv_structured()

    # Fabricated text with a language not in original CV (French)
    # and a certification not in original (PMP)
    fabricated_text = (
        "Jane Developer is fluent in French and holds a PMP certification. "
        "Experienced in Python and FastAPI. Speaks English and Spanish."
    )

    warnings = _verify_customization(fabricated_text, cv_structured)

    # Should flag French as language not in original
    language_warnings = [w for w in warnings if "french" in w.lower() or "Language" in w]
    assert len(language_warnings) > 0, f"Expected language fabrication warning, got: {warnings}"

    # Should flag PMP as certification not in original
    cert_warnings = [w for w in warnings if "PMP" in w or "Certification" in w]
    assert len(cert_warnings) > 0, f"Expected certification fabrication warning, got: {warnings}"


# ---------------------------------------------------------------------------
# Test: cached result bypasses pipeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cached_result_bypasses_pipeline(mock_repos):
    """When a cached result exists, no LLM calls are made."""
    cv_repo, cv_customization_repo, job_result_repo = mock_repos

    # Create providers that track calls
    optimize_provider = _make_provider("should not be called")
    humanize_provider = _make_provider("should not be called")
    audit_provider = _make_provider("should not be called")

    optimize_client = LLMClient(provider=optimize_provider, default_model="haiku-model", default_temperature=0)
    humanize_client = LLMClient(provider=humanize_provider, default_model="sonnet-model", default_temperature=0.3)
    audit_client = LLMClient(provider=audit_provider, default_model="haiku-model", default_temperature=0)

    multi = MultiModelLLMClient(clients={
        "optimize": optimize_client,
        "humanize": humanize_client,
        "keyword_audit": audit_client,
    })

    service = CVService(
        cv_repo=cv_repo,
        cv_customization_repo=cv_customization_repo,
        job_result_repo=job_result_repo,
        llm_client=multi,
    )

    cached_text = "Previously generated CV text with Python and FastAPI experience."
    cached_diff = {
        "sections": [
            {"title": "SUMMARY", "content": cached_text, "changed": True},
        ]
    }
    cached_row = CVCustomizationRow(
        id=uuid4(),
        user_id=USER_ID,
        job_result_id=JOB_RESULT_ID,
        customized_text=cached_text,
        customized_diff=cached_diff,
        created_at="2024-01-14T10:00:00+00:00",  # type: ignore[arg-type]
        updated_at="2024-01-14T10:00:00+00:00",  # type: ignore[arg-type]
    )

    job = _sample_job_result()

    job_result_repo.find_by_id_and_user = AsyncMock(return_value=job)
    cv_repo.find_by_user = AsyncMock(return_value=_sample_cv_row())
    cv_customization_repo.find_by_user_and_job = AsyncMock(return_value=cached_row)

    text, from_cache, warnings, sections = await service.customize_cv(
        user_id=USER_ID,
        job_result_id=JOB_RESULT_ID,
        humanize=True,
    )

    assert from_cache is True
    assert text == cached_text
    # No LLM calls should have been made
    assert len(optimize_provider.calls) == 0
    assert len(humanize_provider.calls) == 0
    assert len(audit_provider.calls) == 0


# ---------------------------------------------------------------------------
# Test: force_regenerate reruns pipeline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_force_regenerate_reruns_pipeline(mock_repos):
    """force_regenerate=True re-runs the full pipeline even with a cached result."""
    cv_repo, cv_customization_repo, job_result_repo = mock_repos

    # Full pipeline providers
    optimize_provider = SequentialProvider([OPTIMIZE_RESPONSE])
    humanize_provider = SequentialProvider([VOICE_FRAGMENTS_RESPONSE])
    audit_provider = SequentialProvider([KEYWORD_AUDIT_RESPONSE])

    optimize_client = LLMClient(provider=optimize_provider, default_model="haiku-model", default_temperature=0)
    humanize_client = LLMClient(provider=humanize_provider, default_model="sonnet-model", default_temperature=0.3)
    audit_client = LLMClient(provider=audit_provider, default_model="haiku-model", default_temperature=0)

    multi = MultiModelLLMClient(clients={
        "optimize": optimize_client,
        "humanize": humanize_client,
        "keyword_audit": audit_client,
    })

    service = CVService(
        cv_repo=cv_repo,
        cv_customization_repo=cv_customization_repo,
        job_result_repo=job_result_repo,
        llm_client=multi,
    )

    job = _sample_job_result()
    cv = _sample_cv_row()

    # Even though cached result exists...
    cached_text = "Old cached text"
    cached_diff = {"sections": [{"title": "SUMMARY", "content": cached_text, "changed": True}]}
    cached_row = CVCustomizationRow(
        id=uuid4(),
        user_id=USER_ID,
        job_result_id=JOB_RESULT_ID,
        customized_text=cached_text,
        customized_diff=cached_diff,
        created_at="2024-01-14T10:00:00+00:00",  # type: ignore[arg-type]
        updated_at="2024-01-14T10:00:00+00:00",  # type: ignore[arg-type]
    )

    job_result_repo.find_by_id_and_user = AsyncMock(return_value=job)
    cv_repo.find_by_user = AsyncMock(return_value=cv)
    cv_customization_repo.find_by_user_and_job = AsyncMock(return_value=cached_row)
    cv_customization_repo.upsert = AsyncMock(return_value=MagicMock())

    # ...force_regenerate should still run the pipeline
    text, from_cache, warnings, sections = await service.customize_cv(
        user_id=USER_ID,
        job_result_id=JOB_RESULT_ID,
        humanize=True,
        force_regenerate=True,
    )

    assert from_cache is False
    assert len(text) > 0
    # All LLM providers should have been called
    assert len(optimize_provider.calls) >= 1
    assert len(humanize_provider.calls) >= 1
    assert len(audit_provider.calls) >= 1


# ---------------------------------------------------------------------------
# Test: humanize=False skips passes 2-5
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_humanize_false_skips_passes_2_through_5():
    """With humanize=False, only Pass 1 (optimize) runs; Passes 2-5 are skipped."""
    optimize_provider = SequentialProvider([OPTIMIZE_RESPONSE])
    humanize_provider = _make_provider("should not be called")
    audit_provider = _make_provider("should not be called")

    optimize_client = LLMClient(provider=optimize_provider, default_model="haiku-model", default_temperature=0)
    humanize_client = LLMClient(provider=humanize_provider, default_model="sonnet-model", default_temperature=0.3)
    audit_client = LLMClient(provider=audit_provider, default_model="haiku-model", default_temperature=0)

    multi = MultiModelLLMClient(clients={
        "optimize": optimize_client,
        "humanize": humanize_client,
        "keyword_audit": audit_client,
    })

    cv_repo = MagicMock()
    cv_customization_repo = MagicMock()
    job_result_repo = MagicMock()

    service = CVService(
        cv_repo=cv_repo,
        cv_customization_repo=cv_customization_repo,
        job_result_repo=job_result_repo,
        llm_client=multi,
    )

    job = _sample_job_result()
    cv = _sample_cv_row()

    job_result_repo.find_by_id_and_user = AsyncMock(return_value=job)
    cv_repo.find_by_user = AsyncMock(return_value=cv)
    cv_customization_repo.find_by_user_and_job = AsyncMock(return_value=None)
    cv_customization_repo.upsert = AsyncMock(return_value=MagicMock())

    text, from_cache, warnings, sections = await service.customize_cv(
        user_id=USER_ID,
        job_result_id=JOB_RESULT_ID,
        humanize=False,
    )

    assert from_cache is False
    assert isinstance(text, str)
    assert len(text) > 0

    # Only optimize was called; humanize and audit were not
    assert len(optimize_provider.calls) >= 1
    assert len(humanize_provider.calls) == 0
    assert len(audit_provider.calls) == 0
