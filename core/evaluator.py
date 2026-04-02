"""Job evaluator — assembles prompts and calls the Claude API.

Prompt assembly merges:
- ``configs/prompts/base_profile.json`` (shared developer profile + rubric)
- ``configs/prompts/<platform>_context.json`` (platform-specific fields + template)
- The NormalizedJob fields

Claude is expected to return a raw JSON object (no markdown fences). If it
doesn't, a single retry is attempted after stripping backtick fences.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

import anthropic

from scrapers.base import NormalizedJob

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class EvaluationResult:
    """Structured result from a Claude evaluation.

    Attributes:
        scratchpad: Internal step-by-step reasoning (not displayed).
        evaluation: Detailed explanation of job relevance.
        relevancy_score: Integer 1–10.
        recommendation: Apply / Consider / Do not apply + justification.
        flags: Comma-separated red/green flags.
        summary: One-sentence job-fit summary.
        raw: The original parsed dict from Claude (defensive copy).
    """

    scratchpad: str
    evaluation: str
    relevancy_score: int
    recommendation: str
    flags: str
    summary: str
    raw: dict

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "EvaluationResult":
        """Build an EvaluationResult from Claude's parsed JSON response."""
        return cls(
            scratchpad=raw.get("scratchpad", ""),
            evaluation=raw.get("evaluation", ""),
            relevancy_score=int(raw.get("relevancy_score", 0)),
            recommendation=raw.get("recommendation", ""),
            flags=raw.get("flags", ""),
            summary=raw.get("summary", ""),
            raw=dict(raw),
        )


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
        self._base_profile = base_profile
        self._model: str = settings["model"]
        self._temperature: float = settings.get("temperature", 0)
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

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
        system_prompt = self._assemble_system_prompt(platform_context)
        user_message = self._assemble_user_message(job, platform_context)

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            temperature=self._temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )

        content = response.content[0].text
        raw = self._parse_response(content)
        return EvaluationResult.from_dict(raw)

    def _assemble_system_prompt(self, platform_context: dict) -> str:
        """Merge base_profile and platform_context into a system prompt string."""
        notes = "\n".join(f"- {n}" for n in platform_context.get("evaluation_notes", []))
        fields = ", ".join(platform_context.get("available_fields", []))
        return (
            f"{self._base_profile['system_instructions']}\n\n"
            f"## Developer Profile\n{json.dumps(self._base_profile, indent=2)}\n\n"
            f"## Platform: {platform_context['platform']}\n"
            f"### Evaluation Notes\n{notes}\n\n"
            f"### Available Fields\n{fields}"
        )

    def _assemble_user_message(
        self,
        job: NormalizedJob,
        platform_context: dict,
    ) -> str:
        """Interpolate job fields into the platform's user_message_template."""
        template: str = platform_context["user_message_template"]
        values: dict[str, Any] = {
            "title": job.title,
            "description": job.description,
            "budget": job.budget or "N/A",
            "job_type": job.job_type or "N/A",
            "experience_level": job.experience_level or "N/A",
            "skills": ", ".join(job.skills) if job.skills else "N/A",
            "url": job.url,
            **{k: v if v is not None else "N/A" for k, v in job.extras.items()},
        }

        class _DefaultNA(dict):
            def __missing__(self, key: str) -> str:
                return "N/A"

        return template.format_map(_DefaultNA(values))

    def _parse_response(self, content: str) -> dict[str, Any]:
        """Parse Claude's JSON response, stripping markdown fences if needed.

        Retries once if the initial parse fails.
        """
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Strip markdown fences and retry once
        stripped = content.strip()
        if stripped.startswith("```"):
            stripped = stripped.split("\n", 1)[-1]
        if stripped.endswith("```"):
            stripped = stripped.rsplit("```", 1)[0]
        stripped = stripped.strip()

        try:
            return json.loads(stripped)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Claude response after retry: %s", content)
            raise ValueError(f"Claude returned invalid JSON: {exc}") from exc
