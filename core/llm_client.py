"""Unified LLM client — wraps AsyncAnthropic with retry, fence-stripping, and a clean error surface.

Used by ``Evaluator`` and ``CVService`` (and any future LLM-backed service)
to eliminate duplicated retry / JSON-parsing logic.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass

import anthropic

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMResponse:
    """Response from an LLM call with content and usage metadata."""

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    duration_ms: int

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


def _parse_json_text(text: str) -> dict:
    """Parse JSON from LLM response text, handling fences and trailing content.

    Tries in order:
    1. Direct json.loads
    2. Strip fences then json.loads
    3. raw_decode to extract first JSON object when there's trailing content
    """
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Strip fences and retry
    stripped = _strip_json_fences(text)
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        # Handle "Extra data" — LLM sometimes appends text after JSON
        if "Extra data" in str(exc) or "extra data" in str(exc).lower():
            decoder = json.JSONDecoder()
            try:
                obj, _ = decoder.raw_decode(stripped)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass
        raise


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
    ) -> LLMResponse:
        """Send a messages.create call with retry on transient errors.

        Returns an ``LLMResponse`` with content and usage metadata.
        Raises ``LLMError`` on failure.
        """
        model_name = model or self.default_model

        for attempt in range(self.default_max_retries):
            try:
                t0 = time.monotonic()
                response = await self.client.messages.create(
                    model=model_name,
                    max_tokens=max_tokens,
                    temperature=0,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                duration_ms = int((time.monotonic() - t0) * 1000)
                return LLMResponse(
                    text=response.content[0].text,
                    model=model_name,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    duration_ms=duration_ms,
                )
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

        Automatically strips markdown code fences and trailing text.
        Raises ``LLMError`` on API failure or if the response is not valid JSON.
        """
        resp = await self._call_api(
            system=system,
            user=user,
            model=model,
            max_tokens=max_tokens,
        )

        try:
            return _parse_json_text(resp.text)
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM returned invalid JSON: {exc}") from exc

    async def generate_json_with_metadata(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> tuple[dict, LLMResponse]:
        """Call the LLM, parse JSON, and return both the parsed dict and metadata."""
        resp = await self._call_api(
            system=system,
            user=user,
            model=model,
            max_tokens=max_tokens,
        )

        try:
            parsed = _parse_json_text(resp.text)
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM returned invalid JSON: {exc}") from exc

        return parsed, resp

    async def generate_text(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> str:
        """Call the LLM and return the raw text response."""
        resp = await self._call_api(
            system=system,
            user=user,
            model=model,
            max_tokens=max_tokens,
        )
        return resp.text

    async def generate_text_with_metadata(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> tuple[str, LLMResponse]:
        """Call the LLM and return both the raw text and metadata."""
        resp = await self._call_api(
            system=system,
            user=user,
            model=model,
            max_tokens=max_tokens,
        )
        return resp.text, resp
