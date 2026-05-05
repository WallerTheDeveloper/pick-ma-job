"""LanguageDetector — lightweight LLM-based language detection for job descriptions.

Uses the cheapest model (claude-haiku) with minimal tokens to detect the primary
language of a job description. This is used as a pre-filter step before the more
expensive evaluation pipeline, so that jobs in languages the user doesn't speak
can be skipped entirely, saving evaluation costs.
"""

import logging

from core.llm_client import LLMClient

logger = logging.getLogger(__name__)

# Default model for language detection — cheapest available
_DEFAULT_LANGUAGE_MODEL = "claude-haiku-4-5-20251001"


class LanguageDetector:
    """Detect the primary language of job descriptions using an LLM call.

    Args:
        llm_client: Shared ``LLMClient`` instance for making API calls.
        model: The model to use for detection. Defaults to claude-haiku for cost efficiency.
    """

    def __init__(self, llm_client: LLMClient, model: str = _DEFAULT_LANGUAGE_MODEL) -> None:
        self._llm = llm_client
        self._model = model

    async def detect(self, text: str) -> str:
        """Detect the primary language of the given text.

        Uses a minimal prompt to keep cost low (~100–500 input tokens + 1–5 output tokens).

        Args:
            text: The job description (or any text) to detect the language of.

        Returns:
            The detected language name in English (e.g., "English", "Dutch", "French").
            Defaults to "English" if detection fails or the text is empty.
        """
        if not text or not text.strip():
            logger.debug("Empty text provided to language detector, defaulting to English")
            return "English"

        system_prompt = (
            "What is the primary language of the following text? "
            "Reply with ONLY the language name in English (e.g., Dutch, French, English). "
            "No explanation."
        )

        # Truncate very long texts to save input tokens.
        # 2000 chars is enough to reliably detect the primary language.
        truncated = text[:2000]

        try:
            content = await self._llm.generate_text(
                system=system_prompt,
                user=truncated,
                model=self._model,
                max_tokens=16,
            )
            language = content.strip()

            if not language:
                logger.warning("Language detector returned empty response, defaulting to English")
                return "English"

            logger.debug("Detected language: %s", language)
            return language

        except Exception as exc:
            logger.warning("Language detection failed: %s, defaulting to English", exc)
            return "English"