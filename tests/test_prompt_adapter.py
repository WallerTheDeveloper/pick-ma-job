"""Unit tests for core.prompt_adapter.

All tests are pure (no DB, no filesystem IO) except for the
load_platform_context tests which hit the real config files on disk.
"""

import pytest

from core.prompt_adapter import (
    _DEFAULT_SYSTEM_INSTRUCTIONS,
    load_platform_context,
    profile_row_to_prompt_dict,
)
from repositories.profile import ProfileRow

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_RUBRIC = {
    "scoring": {
        "9-10": "Excellent match",
        "7-8": "Good match",
        "5-6": "Moderate match",
        "3-4": "Poor match",
        "1-2": "Very poor match",
    },
    "evaluation_factors": ["Skills Match", "Budget/Rate"],
    "system_instructions": "Custom instructions.",
}


def _make_profile(**overrides) -> ProfileRow:
    """Return a fully-populated ProfileRow with sensible defaults."""
    from datetime import datetime
    from uuid import uuid4

    defaults = dict(
        id=uuid4(),
        user_id=uuid4(),
        role="Unity Developer",
        experience="mid-level — 4 years",
        rate="€10-30/hr · €50,000/yr",
        primary_skills=["Unity (C#)", "AR Foundation"],
        secondary_skills=["Rust", "C++"],
        tertiary_skills=["Vue.js"],
        not_a_good_fit=["Pure frontend"],
        background=["2 years at ZAUBAR"],
        notable_projects=[{"name": "Paper.io clone", "description": "Rust multiplayer"}],
        languages=["English", "Ukrainian"],
        rubric=_BASE_RUBRIC,
        updated_at=datetime(2026, 1, 1),
    )
    defaults.update(overrides)
    return ProfileRow(**defaults)


# ---------------------------------------------------------------------------
# profile_row_to_prompt_dict — output shape
# ---------------------------------------------------------------------------

EXPECTED_TOP_LEVEL_KEYS = {
    "system_instructions",
    "developer",
    "background",
    "skills",
    "not_a_good_fit",
    "notable_projects",
    "languages",
    "scoring_rubric",
    "evaluation_factors",
}


def test_output_has_all_expected_top_level_keys():
    result = profile_row_to_prompt_dict(_make_profile())
    assert EXPECTED_TOP_LEVEL_KEYS == set(result.keys())


def test_skills_dict_has_primary_secondary_tertiary():
    result = profile_row_to_prompt_dict(_make_profile())
    assert set(result["skills"].keys()) == {"primary", "secondary", "tertiary"}


def test_developer_dict_has_role_experience_rate():
    result = profile_row_to_prompt_dict(_make_profile())
    assert set(result["developer"].keys()) == {"role", "experience", "rate"}


# ---------------------------------------------------------------------------
# profile_row_to_prompt_dict — field mapping
# ---------------------------------------------------------------------------

def test_role_mapped_correctly():
    result = profile_row_to_prompt_dict(_make_profile(role="Senior Unity Dev"))
    assert result["developer"]["role"] == "Senior Unity Dev"


def test_primary_skills_mapped():
    result = profile_row_to_prompt_dict(_make_profile())
    assert result["skills"]["primary"] == ["Unity (C#)", "AR Foundation"]


def test_secondary_skills_mapped():
    result = profile_row_to_prompt_dict(_make_profile())
    assert result["skills"]["secondary"] == ["Rust", "C++"]


def test_tertiary_skills_mapped():
    result = profile_row_to_prompt_dict(_make_profile())
    assert result["skills"]["tertiary"] == ["Vue.js"]


def test_not_a_good_fit_mapped():
    result = profile_row_to_prompt_dict(_make_profile())
    assert result["not_a_good_fit"] == ["Pure frontend"]


def test_background_mapped():
    result = profile_row_to_prompt_dict(_make_profile())
    assert result["background"] == ["2 years at ZAUBAR"]


def test_notable_projects_mapped():
    result = profile_row_to_prompt_dict(_make_profile())
    assert result["notable_projects"] == [{"name": "Paper.io clone", "description": "Rust multiplayer"}]


def test_languages_mapped():
    result = profile_row_to_prompt_dict(_make_profile())
    assert result["languages"] == ["English", "Ukrainian"]


def test_scoring_rubric_from_rubric_scoring_key():
    result = profile_row_to_prompt_dict(_make_profile())
    assert result["scoring_rubric"] == _BASE_RUBRIC["scoring"]


def test_evaluation_factors_from_rubric():
    result = profile_row_to_prompt_dict(_make_profile())
    assert result["evaluation_factors"] == ["Skills Match", "Budget/Rate"]


def test_system_instructions_from_rubric():
    result = profile_row_to_prompt_dict(_make_profile())
    assert result["system_instructions"] == "Custom instructions."


# ---------------------------------------------------------------------------
# profile_row_to_prompt_dict — defaults for missing / empty fields
# ---------------------------------------------------------------------------

def test_none_role_becomes_empty_string():
    result = profile_row_to_prompt_dict(_make_profile(role=None))
    assert result["developer"]["role"] == ""


def test_none_experience_becomes_empty_string():
    result = profile_row_to_prompt_dict(_make_profile(experience=None))
    assert result["developer"]["experience"] == ""


def test_none_rate_becomes_empty_string():
    result = profile_row_to_prompt_dict(_make_profile(rate=None))
    assert result["developer"]["rate"] == ""


def test_empty_rubric_uses_default_system_instructions():
    result = profile_row_to_prompt_dict(_make_profile(rubric={}))
    assert result["system_instructions"] == _DEFAULT_SYSTEM_INSTRUCTIONS


def test_rubric_missing_system_instructions_uses_default():
    result = profile_row_to_prompt_dict(_make_profile(rubric={"scoring": {}}))
    assert result["system_instructions"] == _DEFAULT_SYSTEM_INSTRUCTIONS


def test_empty_skills_produce_empty_lists():
    result = profile_row_to_prompt_dict(
        _make_profile(primary_skills=[], secondary_skills=[], tertiary_skills=[])
    )
    assert result["skills"] == {"primary": [], "secondary": [], "tertiary": []}


def test_empty_rubric_produces_empty_scoring_and_factors():
    result = profile_row_to_prompt_dict(_make_profile(rubric={}))
    assert result["scoring_rubric"] == {}
    assert result["evaluation_factors"] == []


# ---------------------------------------------------------------------------
# profile_row_to_prompt_dict — immutability (no aliasing)
# ---------------------------------------------------------------------------

def test_mutating_returned_skills_does_not_affect_original_profile():
    profile = _make_profile()
    result = profile_row_to_prompt_dict(profile)
    result["skills"]["primary"].append("NEW SKILL")
    assert "NEW SKILL" not in profile.primary_skills


def test_mutating_returned_rubric_does_not_affect_original():
    profile = _make_profile()
    result = profile_row_to_prompt_dict(profile)
    result["scoring_rubric"]["99"] = "impossible"
    assert "99" not in profile.rubric.get("scoring", {})


# ---------------------------------------------------------------------------
# load_platform_context
# ---------------------------------------------------------------------------

def test_load_upwork_context_returns_dict():
    ctx = load_platform_context("upwork")
    assert isinstance(ctx, dict)


def test_upwork_context_has_required_keys():
    ctx = load_platform_context("upwork")
    assert "platform" in ctx
    assert "evaluation_notes" in ctx
    assert "available_fields" in ctx
    assert "user_message_template" in ctx


def test_linkedin_context_has_required_keys():
    ctx = load_platform_context("linkedin")
    assert "platform" in ctx
    assert "user_message_template" in ctx


def test_load_unknown_platform_raises_file_not_found():
    with pytest.raises(FileNotFoundError, match="no_such_platform"):
        load_platform_context("no_such_platform")


def test_load_platform_context_is_cached(tmp_path, monkeypatch):
    """Same object returned on repeated calls (lru_cache hit)."""
    ctx1 = load_platform_context("upwork")
    ctx2 = load_platform_context("upwork")
    assert ctx1 is ctx2
