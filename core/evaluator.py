"""Job evaluator — assembles prompts and calls the Claude API.

Prompt assembly merges:
- ``configs/prompts/base_profile.json`` (shared developer profile + rubric)
- ``configs/prompts/<platform>_context.json`` (platform-specific fields + template)
- The NormalizedJob fields

Claude is expected to return a raw JSON object (no markdown fences). If it
doesn't, a single retry is attempted after stripping backtick fences.

Two-pass evaluation:
- Pass 1 (score only): lightweight prompt → single integer 1–10
- Pass 2 (full eval): only if Pass 1 score ≥ SCORE_THRESHOLD
Jobs below the threshold are stored with their score and null evaluation fields.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any

from core.llm_client import LLMClient, LLMError, LLMResponse
from core.settings import Settings
from scrapers.base import NormalizedJob

logger = logging.getLogger(__name__)

SCORE_THRESHOLD = 5  # Jobs scoring below this skip the full evaluation pass


@dataclass(frozen=True)
class EvaluationResult:
    """Structured result from a Claude evaluation.

    For jobs that score below ``SCORE_THRESHOLD`` in Pass 1, only
    ``relevancy_score`` and ``raw`` are populated; all other fields are None.

    Attributes:
        relevancy_score: Integer 1–10.
        scratchpad: Internal step-by-step reasoning (not displayed). None for low-score jobs.
        evaluation: Detailed explanation of job relevance. None for low-score jobs.
        recommendation: Apply / Consider / Do not apply + justification. None for low-score jobs.
        flags: Comma-separated red/green flags. None for low-score jobs.
        summary: One-sentence job-fit summary. None for low-score jobs.
        raw: The original parsed dict from Claude (defensive copy).
    """

    relevancy_score: int
    scratchpad: str | None = None
    evaluation: str | None = None
    recommendation: str | None = None
    flags: str | None = None
    summary: str | None = None
    raw: dict = field(default_factory=dict)
    pass1_parse_failed: bool = False

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "EvaluationResult":
        """Build a full EvaluationResult from Claude's parsed JSON response."""
        return cls(
            relevancy_score=int(raw.get("relevancy_score", 0)),
            scratchpad=raw.get("scratchpad"),
            evaluation=raw.get("evaluation"),
            recommendation=raw.get("recommendation"),
            flags=raw.get("flags"),
            summary=raw.get("summary"),
            raw=dict(raw),
        )

    @classmethod
    def from_score(cls, score: int, pass1_parse_failed: bool = False) -> "EvaluationResult":
        """Build a score-only result for jobs that failed the Pass 1 threshold."""
        return cls(
            relevancy_score=score,
            raw={"relevancy_score": score},
            pass1_parse_failed=pass1_parse_failed,
        )


class Evaluator:
    """Assembles prompts from config and evaluates jobs via the Claude API.

    Args:
        base_profile: Loaded ``configs/prompts/base_profile.json``.
        settings: Validated application settings.
        llm_client: A shared ``LLMClient`` instance.
    """

    def __init__(
        self,
        base_profile: dict,
        settings: Settings,
        llm_client: LLMClient,
    ) -> None:
        self._base_profile = base_profile
        self._temperature: float = settings.claude_temperature
        self._score_threshold: int = settings.score_threshold
        self._llm = llm_client

    async def evaluate(
        self,
        job: NormalizedJob,
        platform_context: dict,
    ) -> EvaluationResult:
        """Evaluate a single job using a two-pass approach.

        Pass 1 — lightweight score prompt: returns a single integer 1–10.
        Pass 2 — full evaluation: only runs if Pass 1 score ≥ SCORE_THRESHOLD.

        Jobs below the threshold return an ``EvaluationResult`` with only the
        score populated (all other fields are None).

        Args:
            job: The normalized job to evaluate.
            platform_context: Loaded ``configs/prompts/<platform>_context.json``.

        Returns:
            An ``EvaluationResult`` — fully populated for high-score jobs,
            score-only for low-score jobs.

        Raises:
            LLMError: If Claude returns invalid JSON after retries (Pass 2 only).
        """
        score, parse_failed, meta1 = await self._call_score(job)
        logger.info(
            "llm_call",
            extra={
                "pass": 1,
                "job_title": job.title,
                "model": meta1.model,
                "duration_ms": meta1.duration_ms,
                "input_tokens": meta1.input_tokens,
                "output_tokens": meta1.output_tokens,
            },
        )
        logger.debug("Pass 1 score=%d for job '%s'", score, job.title)

        if score < self._score_threshold:
            logger.info(
                "Low score (%d < %d) — skipping full evaluation for '%s'",
                score,
                self._score_threshold,
                job.title,
            )
            return EvaluationResult.from_score(score, pass1_parse_failed=parse_failed)

        system_prompt = self._assemble_system_prompt(platform_context)
        user_message = self._assemble_user_message(job, platform_context)

        raw, meta2 = await self._llm.generate_json_with_metadata(
            system=system_prompt,
            user=user_message,
            max_tokens=2048,
        )
        logger.info(
            "llm_call",
            extra={
                "pass": 2,
                "job_title": job.title,
                "model": meta2.model,
                "duration_ms": meta2.duration_ms,
                "input_tokens": meta2.input_tokens,
                "output_tokens": meta2.output_tokens,
            },
        )
        return EvaluationResult.from_dict(raw)

    async def evaluate_full(
        self,
        job: NormalizedJob,
        platform_context: dict,
        existing_score: int,
    ) -> EvaluationResult:
        """Run Pass 2 (full evaluation) for a job that already has a score from Pass 1.

        Only runs if existing_score >= self._score_threshold.
        Returns EvaluationResult.from_score(existing_score) if below threshold.

        Args:
            job: The normalized job to evaluate.
            platform_context: Loaded ``configs/prompts/<platform>_context.json``.
            existing_score: The score from Pass 1 (already stored in DB).

        Returns:
            An ``EvaluationResult`` — fully populated for high-score jobs,
            score-only for low-score jobs.

        Raises:
            LLMError: If Claude returns invalid JSON after retries.
        """
        if existing_score < self._score_threshold:
            logger.info(
                "Existing score (%d < %d) — skipping full evaluation for '%s'",
                existing_score,
                self._score_threshold,
                job.title,
            )
            return EvaluationResult.from_score(existing_score)

        system_prompt = self._assemble_system_prompt(platform_context)
        user_message = self._assemble_user_message(job, platform_context)

        raw, meta = await self._llm.generate_json_with_metadata(
            system=system_prompt,
            user=user_message,
            max_tokens=2048,
        )
        logger.info(
            "llm_call",
            extra={
                "pass": 2,
                "job_title": job.title,
                "model": meta.model,
                "duration_ms": meta.duration_ms,
                "input_tokens": meta.input_tokens,
                "output_tokens": meta.output_tokens,
            },
        )
        return EvaluationResult.from_dict(raw)

    async def _call_score(self, job: NormalizedJob) -> tuple[int, bool, LLMResponse]:
        """Pass 1: send a lightweight prompt and return a relevancy score 1–10.

        Args:
            job: The job to score.

        Returns:
            A tuple of (score, parse_failed, LLMResponse) where score is 1–10,
            parse_failed is True if the response was unparseable, and the
            LLMResponse contains timing and token usage metadata.
        """
        system_prompt = self._build_score_system_prompt()
        user_message = f"Job Title: {job.title}\n\nDescription:\n{job.description}"

        content, meta = await self._llm.generate_text_with_metadata(
            system=system_prompt,
            user=user_message,
            max_tokens=16,
        )
        score, parse_failed = self._parse_score(content)
        return score, parse_failed, meta

    def _build_score_system_prompt(self) -> str:
        """Build the concise system prompt used for Pass 1 scoring."""
        developer = self._base_profile.get("developer", {})
        role = developer.get("role", "")
        experience = developer.get("experience", "")
        primary_skills = ", ".join(self._base_profile.get("skills", {}).get("primary", []))
        not_a_good_fit = ", ".join(self._base_profile.get("not_a_good_fit", []))
        return (
            "You are a job-fit screener. Rate the relevance of the job posting "
            "to the developer profile below on a scale of 1 to 10. Respond with "
            "ONLY a single integer between 1 and 10 — no explanation, no other text.\n\n"
            f"Developer: {role} ({experience})\n"
            f"Primary skills: {primary_skills}\n"
            f"Not a good fit for: {not_a_good_fit}"
        )

    def _parse_score(self, content: str) -> tuple[int, bool]:
        """Parse a 1–10 integer from Claude's Pass 1 response.

        Tries a direct integer parse first, then falls back to regex extraction.
        Returns ``(self._score_threshold - 1, True)`` if parsing fails entirely,
        so the job falls below the gate and does not trigger Pass 2.

        Returns:
            A tuple of (score, parse_failed).
        """
        stripped = content.strip()
        try:
            return max(1, min(10, int(stripped))), False
        except ValueError:
            pass

        match = re.search(r"\b(10|[1-9])\b", stripped)
        if match:
            return int(match.group(1)), False

        logger.warning(
            "pass1_parse_failed",
            extra={"raw": content[:200]},
        )
        return self._score_threshold - 1, True

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
