"""Unified LLM client — wraps AsyncAnthropic with retry, fence-stripping, and a clean error surface.

Used by ``Evaluator`` and ``CVService`` (and any future LLM-backed service)
to eliminate duplicated retry / JSON-parsing logic.
"""

import asyncio
import json
import logging
from dataclasses import dataclass

import anthropic

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {429, 503, 529}


class LLMError(Exception):
    """Raised when an LLM call fails after all retries.

    Attributes:
        message: Human-readable description.
        retryable: ``True`` if the error was from a transient API issue (429/503/529).
    """

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        self.message = message
        self.retryable = retryable
        super().__init__(message)


def _strip_json_fences(content: str) -> str:
    """Strip leading/trailing markdown code fences from *content*."""
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1]
    if stripped.endswith("```"):
        stripped = stripped.rsplit("```", 1)[0]
    return stripped.strip()


@dataclass(frozen=True)
class LLMClient:
    """Thin wrapper around ``AsyncAnthropic`` with shared retry and parsing.

    Args:
        client: An ``AsyncAnthropic`` instance.
        default_model: Model name used when *model* is not overridden per-call.
        default_max_retries: Total attempts before giving up (including the first).
    """

    client: anthropic.AsyncAnthropic
    default_model: str
    default_max_retries: int = 3

    async def _call_api(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> str:
        """Send a messages.create call with retry on transient errors.

        Returns the raw text content from the first content block.
        Raises ``LLMError`` on failure.
        """
        model_name = model or self.default_model

        for attempt in range(self.default_max_retries):
            try:
                response = await self.client.messages.create(
                    model=model_name,
                    max_tokens=max_tokens,
                    temperature=0,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                return response.content[0].text
            except anthropic.APIStatusError as exc:
                if (
                    exc.status_code in RETRYABLE_STATUS_CODES
                    and attempt < self.default_max_retries - 1
                ):
                    wait = 2 ** attempt
                    logger.warning(
                        "Anthropic API transient error %d (attempt %d/%d), retrying in %ds",
                        exc.status_code,
                        attempt + 1,
                        self.default_max_retries,
                        wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    raise LLMError(
                        f"Anthropic API error {exc.status_code}: {exc.message}",
                        retryable=exc.status_code in RETRYABLE_STATUS_CODES,
                    ) from exc

        # Unreachable, but satisfies the type checker.
        raise LLMError("Unexpected retry exhaustion")

    async def generate_json(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> dict:
        """Call the LLM and parse the response as JSON.

        Automatically strips markdown code fences before parsing.
        Raises ``LLMError`` on API failure or if the response is not valid JSON.
        """
        content = await self._call_api(
            system=system,
            user=user,
            model=model,
            max_tokens=max_tokens,
        )

        # Try direct parse first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Strip fences and retry once
        try:
            return json.loads(_strip_json_fences(content))
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM returned invalid JSON: {exc}") from exc

    async def generate_text(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> str:
        """Call the LLM and return the raw text response."""
        return await self._call_api(
            system=system,
            user=user,
            model=model,
            max_tokens=max_tokens,
        )
