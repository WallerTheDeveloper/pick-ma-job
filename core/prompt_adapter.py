"""Adapters that bridge DB rows to the dict shapes expected by the Evaluator.

Two public functions:

- ``profile_row_to_prompt_dict`` — converts a ``ProfileRow`` (from DB) into the
  same dict structure that ``Evaluator._assemble_system_prompt`` expects (i.e.
  the shape of ``configs/prompts/base_profile.json``).

- ``load_platform_context`` — loads and caches the static per-platform context
  JSON files from ``configs/prompts/<platform>_context.json``.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from repositories.profile import ProfileRow

logger = logging.getLogger(__name__)

_CONFIGS_DIR = Path(__file__).parent.parent / "configs" / "prompts"

_DEFAULT_SYSTEM_INSTRUCTIONS = (
    "You are a job-fit evaluator. Assess the provided job posting against the "
    "developer profile above. Return ONLY a raw JSON object — no markdown, no "
    "backticks, no explanation outside the JSON. The JSON must include exactly "
    "these fields: scratchpad, evaluation, relevancy_score, recommendation, "
    "flags, summary. All fields except relevancy_score must be plain strings — "
    "no nested objects or arrays."
)


def profile_row_to_prompt_dict(profile: ProfileRow) -> dict[str, Any]:
    """Convert a ``ProfileRow`` to the base_profile dict shape the Evaluator expects.

    The Evaluator's ``_assemble_system_prompt`` reads these top-level keys:
    ``system_instructions``, ``developer``, ``background``, ``skills``,
    ``not_a_good_fit``, ``notable_projects``, ``languages``,
    ``scoring_rubric``, ``evaluation_factors``.

    Args:
        profile: A ``ProfileRow`` loaded from the ``profiles`` table.

    Returns:
        A dict with the same structure as ``configs/prompts/base_profile.json``.
    """
    rubric = profile.rubric or {}
    system_instructions: str = rubric.get("system_instructions") or _DEFAULT_SYSTEM_INSTRUCTIONS

    return {
        "system_instructions": system_instructions,
        "developer": {
            "role": profile.role or "",
            "experience": profile.experience or "",
            "rate": profile.rate or "",
        },
        "background": list(profile.background),
        "skills": {
            "primary": list(profile.primary_skills),
            "secondary": list(profile.secondary_skills),
            "tertiary": list(profile.tertiary_skills),
        },
        "not_a_good_fit": list(profile.not_a_good_fit),
        "notable_projects": list(profile.notable_projects),
        "languages": list(profile.languages),
        "scoring_rubric": dict(rubric.get("scoring", {})),
        "evaluation_factors": list(rubric.get("evaluation_factors", [])),
    }


@lru_cache(maxsize=16)
def load_platform_context(platform: str) -> dict[str, Any]:
    """Load and cache a platform context JSON file.

    Reads ``configs/prompts/<platform>_context.json`` relative to the project
    root. Results are cached for the lifetime of the process — these files are
    static and never change at runtime.

    Args:
        platform: Platform slug, e.g. ``"upwork"`` or ``"linkedin"``.

    Returns:
        The parsed platform context dict.

    Raises:
        FileNotFoundError: If no context file exists for the given platform.
        ValueError: If the file exists but contains invalid JSON.
    """
    path = _CONFIGS_DIR / f"{platform}_context.json"
    if not path.exists():
        raise FileNotFoundError(
            f"No platform context file found for '{platform}': {path}"
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Invalid JSON in platform context file '{path}': {exc}"
        ) from exc
