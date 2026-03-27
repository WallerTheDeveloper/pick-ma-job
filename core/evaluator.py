"""Job evaluator — assembles prompts and calls the Claude API.

Prompt assembly merges:
- ``configs/prompts/base_profile.json`` (shared developer profile + rubric)
- ``configs/prompts/<platform>_context.json`` (platform-specific fields + template)
- The NormalizedJob fields

Claude is expected to return a raw JSON object (no markdown fences). If it
doesn't, a single retry is attempted after stripping backtick fences.
"""

import logging
from typing import Any

from scrapers.base import NormalizedJob

logger = logging.getLogger(__name__)


class EvaluationResult:
    """Structured result from a Claude evaluation.

    Attributes:
        scratchpad: Internal step-by-step reasoning (not displayed).
        evaluation: Detailed explanation of job relevance.
        relevancy_score: Integer 1–10.
        recommendation: Apply / Consider / Do not apply + justification.
        flags: Comma-separated red/green flags.
        summary: One-sentence job-fit summary.
        raw: The original parsed dict from Claude.
    """

    def __init__(self, raw: dict[str, Any]) -> None:
        self.scratchpad: str = raw.get("scratchpad", "")
        self.evaluation: str = raw.get("evaluation", "")
        self.relevancy_score: int = int(raw.get("relevancy_score", 0))
        self.recommendation: str = raw.get("recommendation", "")
        self.flags: str = raw.get("flags", "")
        self.summary: str = raw.get("summary", "")
        self.raw = raw


class Evaluator:
    """Assembles prompts from config and evaluates jobs via the Claude API.

    Args:
        base_profile: Loaded ``configs/prompts/base_profile.json``.
        settings: Loaded ``configs/settings.json``.
        api_key: Anthropic API key.
    """

    def __init__(
        self,
        base_profile: dict,
        settings: dict,
        api_key: str,
    ) -> None:
        ...

    async def evaluate(
        self,
        job: NormalizedJob,
        platform_context: dict,
    ) -> EvaluationResult:
        """Evaluate a single job and return a structured result.

        Assembles the system prompt from base_profile + platform_context,
        builds the user message using the platform's template, calls Claude
        Haiku at temperature 0, and parses the JSON response.

        Args:
            job: The normalized job to evaluate.
            platform_context: Loaded ``configs/prompts/<platform>_context.json``.

        Returns:
            An ``EvaluationResult`` with all Claude response fields populated.

        Raises:
            ValueError: If Claude returns invalid JSON after one retry.
        """
        ...

    def _assemble_system_prompt(self, platform_context: dict) -> str:
        """Merge base_profile and platform_context into a system prompt string."""
        ...

    def _assemble_user_message(
        self,
        job: NormalizedJob,
        platform_context: dict,
    ) -> str:
        """Interpolate job fields into the platform's user_message_template."""
        ...

    def _parse_response(self, content: str) -> dict[str, Any]:
        """Parse Claude's JSON response, stripping markdown fences if needed.

        Retries once if the initial parse fails.
        """
        ...
