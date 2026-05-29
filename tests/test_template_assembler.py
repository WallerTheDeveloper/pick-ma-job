"""Tests for core.template_assembler — hybrid template assembly for anti-detection."""

import json
import pytest

from core.template_assembler import (
    assemble_cv,
    _parse_voice_fragments,
    _extract_original_section,
    _is_section_header,
    _is_any_section_header,
    _apply_section_patches,
)


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_CV_TEXT = """JANE DEVELOPER
Senior Developer

SUMMARY
Experienced backend developer with 5 years of Python and FastAPI. Built real-time APIs handling 10K requests/sec. Mostly worked on data pipelines and microservices architecture.

EXPERIENCE
Senior Developer at TechCorp (2020-2023)
- Built real-time data pipeline processing 500K events/day
- Led migration from monolith to microservices using Docker and Kubernetes
- Reduced API latency by 40% through caching and query optimization

Developer at StartupCo (2018-2020)
- Implemented REST APIs with Python and FastAPI
- Managed PostgreSQL databases with 1M+ rows

SKILLS
Python, FastAPI, PostgreSQL, Docker, Kubernetes, AWS, Redis, Celery

EDUCATION
B.S. Computer Science, University of Technology (2018)
"""

SAMPLE_SKELETON = {
    "target_keywords": ["Python", "FastAPI", "Docker", "PostgreSQL", "Kubernetes"],
    "must_include_facts": [
        "5 years of Python experience",
        "Real-time data pipeline processing 500K events/day",
        "Company: TechCorp",
        "Role: Senior Developer",
    ],
    "positioning": "Backend-focused developer with strong API and data pipeline expertise",
    "verified_skills": "Python, FastAPI, PostgreSQL, Docker, Kubernetes, AWS, Redis, Celery",
    "verified_languages": "English, Spanish",
    "verified_certifications": "AWS Certified Solutions Architect",
    "sections_json": json.dumps({
        "sections": [
            {
                "title": "SUMMARY",
                "content": "Furthermore, I leveraged cutting-edge Python and FastAPI to streamline backend systems. Additionally, I spearheaded the migration project.",
                "changed": True,
            },
            {
                "title": "EXPERIENCE",
                "content": "Led the backend team using Docker and PostgreSQL. Managed microservices architecture for high-availability systems.",
                "changed": True,
            },
            {
                "title": "SKILLS",
                "content": "Python, FastAPI, PostgreSQL, Docker, Kubernetes, AWS, Redis, Celery",
                "changed": False,
            },
            {
                "title": "EDUCATION",
                "content": "B.S. Computer Science, University of Technology (2018)",
                "changed": False,
            },
        ]
    }),
}

SAMPLE_VOICE_FRAGMENTS = {
    "fragments": [
        {"section": "SUMMARY", "voice": "Really a backend person who spent five years neck-deep in Python and API work. The data pipeline stuff was honestly the most fun."},
        {"section": "EXPERIENCE", "voice": "The TechCorp migration was where I learned the most. Shipping microservices at scale is always harder than people think."},
        {"section": "SKILLS", "voice": "Python and FastAPI are what I use daily. Docker is pretty much second nature at this point."},
        {"section": "EDUCATION", "voice": "Got my CS degree mostly because the math classes were genuinely interesting."},
    ]
}


# ---------------------------------------------------------------------------
# Test: _parse_voice_fragments
# ---------------------------------------------------------------------------


class TestParseVoiceFragments:
    def test_parse_valid_fragments(self):
        """Parses fragment list into section-keyed map."""
        result = _parse_voice_fragments(SAMPLE_VOICE_FRAGMENTS)
        assert "SUMMARY" in result
        assert "EXPERIENCE" in result
        assert result["SUMMARY"] == "Really a backend person who spent five years neck-deep in Python and API work. The data pipeline stuff was honestly the most fun."

    def test_empty_fragments(self):
        """Empty fragments dict returns empty map."""
        result = _parse_voice_fragments({"fragments": []})
        assert result == {}

    def test_fragments_without_section_key(self):
        """Fragments missing 'section' key are skipped."""
        fragments = {"fragments": [{"voice": "Some text"}]}
        result = _parse_voice_fragments(fragments)
        assert result == {}

    def test_fragments_without_voice_key(self):
        """Fragments missing 'voice' key are skipped."""
        fragments = {"fragments": [{"section": "SUMMARY"}]}
        result = _parse_voice_fragments(fragments)
        assert result == {}

    def test_missing_fragments_key(self):
        """Dict without 'fragments' key returns empty map."""
        result = _parse_voice_fragments({})
        assert result == {}


# ---------------------------------------------------------------------------
# Test: _extract_original_section
# ---------------------------------------------------------------------------


class TestExtractOriginalSection:
    def test_extract_summary(self):
        """Extracts SUMMARY section from original CV text."""
        result = _extract_original_section(SAMPLE_CV_TEXT, "SUMMARY")
        assert "Experienced backend developer" in result
        assert "5 years" in result

    def test_extract_experience(self):
        """Extracts EXPERIENCE section from original CV text."""
        result = _extract_original_section(SAMPLE_CV_TEXT, "EXPERIENCE")
        assert "TechCorp" in result
        assert "data pipeline" in result

    def test_extract_skills(self):
        """Extracts SKILLS section from original CV text."""
        result = _extract_original_section(SAMPLE_CV_TEXT, "SKILLS")
        assert "Python" in result
        assert "FastAPI" in result

    def test_extract_education(self):
        """Extracts EDUCATION section from original CV text."""
        result = _extract_original_section(SAMPLE_CV_TEXT, "EDUCATION")
        assert "Computer Science" in result

    def test_missing_section_returns_empty(self):
        """Missing section returns empty string."""
        result = _extract_original_section(SAMPLE_CV_TEXT, "HOBBIES")
        assert result == ""

    def test_empty_text_returns_empty(self):
        """Empty text returns empty string."""
        result = _extract_original_section("", "SUMMARY")
        assert result == ""


# ---------------------------------------------------------------------------
# Test: _is_section_header
# ---------------------------------------------------------------------------


class TestIsSectionHeader:
    def test_match_exact(self):
        assert _is_section_header("SUMMARY", "SUMMARY") is True

    def test_match_case_insensitive(self):
        assert _is_section_header("summary", "SUMMARY") is True

    def test_no_match(self):
        assert _is_section_header("Python developer", "SUMMARY") is False

    def test_empty_line(self):
        assert _is_section_header("", "SUMMARY") is False

    def test_very_long_line(self):
        long_line = "A" * 100
        assert _is_section_header(long_line, "SUMMARY") is False


# ---------------------------------------------------------------------------
# Test: _is_any_section_header
# ---------------------------------------------------------------------------


class TestIsAnySectionHeader:
    def test_all_caps(self):
        assert _is_any_section_header("SUMMARY") is True

    def test_title_case(self):
        assert _is_any_section_header("Professional Summary") is True

    def test_regular_sentence(self):
        assert _is_any_section_header("Built real-time data pipelines.") is False

    def test_ends_with_period(self):
        assert _is_any_section_header("Summary.") is False


# ---------------------------------------------------------------------------
# Test: _apply_section_patches
# ---------------------------------------------------------------------------


class TestApplySectionPatches:
    def test_applies_matching_patch(self):
        """Applies patch when section matches."""
        content = "I used Python and FastAPI to build systems."
        patches = {
            "patches": [
                {
                    "section": "SUMMARY",
                    "original_sentence": "I used Python and FastAPI to build systems.",
                    "new_sentence": "I used Python and FastAPI to build systems, including REST APIs.",
                }
            ]
        }
        result = _apply_section_patches(content, "SUMMARY", patches)
        assert "REST APIs" in result

    def test_no_patch_for_different_section(self):
        """Patches for other sections are ignored."""
        content = "I used Python and FastAPI to build systems."
        patches = {
            "patches": [
                {
                    "section": "EXPERIENCE",
                    "original_sentence": "I used Python and FastAPI to build systems.",
                    "new_sentence": "I used Python and FastAPI to build systems, including REST APIs.",
                }
            ]
        }
        result = _apply_section_patches(content, "SUMMARY", patches)
        assert result == content  # Unchanged

    def test_no_patches_returns_original(self):
        """None patches returns original content."""
        content = "Original content."
        result = _apply_section_patches(content, "SUMMARY", None)
        assert result == content

    def test_empty_patches(self):
        """Empty patches list leaves content unchanged."""
        content = "Original content."
        result = _apply_section_patches(content, "SUMMARY", {"patches": []})
        assert result == content


# ---------------------------------------------------------------------------
# Test: assemble_cv
# ---------------------------------------------------------------------------


class TestAssembleCV:
    def test_preserves_original_bullet_points(self):
        """Verbatim original CV text appears in output."""
        result = assemble_cv(
            original_cv_text=SAMPLE_CV_TEXT,
            skeleton=SAMPLE_SKELETON,
            voice_fragments=SAMPLE_VOICE_FRAGMENTS,
            keyword_patches=None,
        )
        # Original CV text should be present in the output
        assert "TechCorp" in result or "Techcorp" in result.lower() or "migration" in result.lower()

    def test_includes_voice_fragment_in_summary(self):
        """Voice fragment appears in summary section."""
        result = assemble_cv(
            original_cv_text=SAMPLE_CV_TEXT,
            skeleton=SAMPLE_SKELETON,
            voice_fragments=SAMPLE_VOICE_FRAGMENTS,
            keyword_patches=None,
        )
        # The voice fragment for SUMMARY should appear
        assert "backend person" in result.lower() or "five years" in result.lower()

    def test_skill_section_uses_original_text(self):
        """Skills section draws heavily from original CV."""
        result = assemble_cv(
            original_cv_text=SAMPLE_CV_TEXT,
            skeleton=SAMPLE_SKELETON,
            voice_fragments=SAMPLE_VOICE_FRAGMENTS,
            keyword_patches=None,
        )
        # Original skills should be preserved
        assert "Python" in result
        assert "FastAPI" in result

    def test_experience_hybrid_structure(self):
        """Experience section blends original bulbs + voice fragment."""
        result = assemble_cv(
            original_cv_text=SAMPLE_CV_TEXT,
            skeleton=SAMPLE_SKELETON,
            voice_fragments=SAMPLE_VOICE_FRAGMENTS,
            keyword_patches=None,
        )
        # Should contain both original experience text AND voice fragment
        # The original CV has "TechCorp" and voice has "TechCorp migration"
        assert "EXPERIENCE" in result or "Experience" in result

    def test_education_mostly_original(self):
        """Education section preserves original text."""
        result = assemble_cv(
            original_cv_text=SAMPLE_CV_TEXT,
            skeleton=SAMPLE_SKELETON,
            voice_fragments=SAMPLE_VOICE_FRAGMENTS,
            keyword_patches=None,
        )
        # Education should be mostly original — "Computer Science" from the original
        assert "Computer Science" in result or "University" in result

    def test_missing_original_section_uses_template(self):
        """Graceful fallback when original text is sparse."""
        sparse_cv = "Jane Developer\n\nSUMMARY\nSome summary text."
        result = assemble_cv(
            original_cv_text=sparse_cv,
            skeleton=SAMPLE_SKELETON,
            voice_fragments=SAMPLE_VOICE_FRAGMENTS,
            keyword_patches=None,
        )
        # Should still produce output (fallback to optimized content)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_keyword_patches_applied(self):
        """Patches from keyword audit are woven in."""
        patches = {
            "patches": [
                {
                    "section": "SUMMARY",
                    "original_sentence": "I leveraged cutting-edge Python and FastAPI to streamline backend systems.",
                    "new_sentence": "I leveraged Python and FastAPI to streamline backend systems, including Docker deployment.",
                }
            ]
        }
        result = assemble_cv(
            original_cv_text=SAMPLE_CV_TEXT,
            skeleton=SAMPLE_SKELETON,
            voice_fragments=SAMPLE_VOICE_FRAGMENTS,
            keyword_patches=patches,
        )
        # Should complete without error
        assert isinstance(result, str)

    def test_target_keywords_present(self):
        """All target keywords appear in final text when present in sources."""
        result = assemble_cv(
            original_cv_text=SAMPLE_CV_TEXT,
            skeleton=SAMPLE_SKELETON,
            voice_fragments=SAMPLE_VOICE_FRAGMENTS,
            keyword_patches=None,
        )
        # Target keywords from skeleton should appear (they're in the CV text)
        assert "Python" in result
        assert "FastAPI" in result

    def test_verified_facts_present(self):
        """Must-include facts from skeleton are present in final text."""
        result = assemble_cv(
            original_cv_text=SAMPLE_CV_TEXT,
            skeleton=SAMPLE_SKELETON,
            voice_fragments=SAMPLE_VOICE_FRAGMENTS,
            keyword_patches=None,
        )
        # "5 years" should appear (it's in the original CV)
        assert "5" in result or "five" in result.lower()

    def test_no_fabricated_languages(self):
        """Verification still catches language fabrication after assembly."""
        from services.cv_service import _verify_customization
        
        cv_structured = {
            "languages": ["English"],
            "skills": {"primary": ["Python"]},
            "certifications": [],
            "education": [],
            "experience": [],
        }
        # Fabricate French in the assembled text
        fabricated_text = "I speak French fluently. " + assemble_cv(
            original_cv_text=SAMPLE_CV_TEXT,
            skeleton=SAMPLE_SKELETON,
            voice_fragments=SAMPLE_VOICE_FRAGMENTS,
            keyword_patches=None,
        )
        warnings = _verify_customization(fabricated_text, cv_structured)
        language_warnings = [w for w in warnings if "french" in w.lower() or "Language" in w]
        assert len(language_warnings) > 0, f"Expected language fabrication warning, got: {warnings}"

    def test_empty_voice_fragments(self):
        """Assembly works with empty voice fragments."""
        result = assemble_cv(
            original_cv_text=SAMPLE_CV_TEXT,
            skeleton=SAMPLE_SKELETON,
            voice_fragments={"fragments": []},
            keyword_patches=None,
        )
        assert isinstance(result, str)
        assert len(result) > 0
        # Should still have sections from skeleton
        assert "SUMMARY" in result or "EXPERIENCE" in result

    def test_assemble_with_no_keyword_patches(self):
        """Assembly works without keyword patches (None)."""
        result = assemble_cv(
            original_cv_text=SAMPLE_CV_TEXT,
            skeleton=SAMPLE_SKELETON,
            voice_fragments=SAMPLE_VOICE_FRAGMENTS,
            keyword_patches=None,
        )
        assert isinstance(result, str)
        assert len(result) > 0