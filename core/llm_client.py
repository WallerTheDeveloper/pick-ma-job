"""Unified LLM client — delegates to an LLMProvider with JSON parsing and error handling.

Used by ``Evaluator`` and ``CVService`` (and any future LLM-backed service)
to eliminate duplicated JSON-parsing logic.  The actual API call is delegated
to an ``LLMProvider`` (e.g. ``AnthropicProvider``) which handles retries and
provider-specific error handling.
"""

import json
import logging
from dataclasses import dataclass

from core.llm_provider import LLMProvider, LLMResponse

logger = logging.getLogger(__name__)


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
    """Provider-agnostic LLM client. Delegates to the configured provider.

    Args:
        provider: An ``LLMProvider`` implementation (e.g. ``AnthropicProvider``).
        default_model: Model name used when *model* is not overridden per-call.
        default_max_retries: Kept for backward compatibility but retry logic
            is now handled by the provider.
    """

    provider: LLMProvider
    default_model: str
    default_max_retries: int = 6  # Kept for compat but retry is now per-provider

    async def _call_api(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0,
    ) -> LLMResponse:
        """Send a completion call to the provider.

        Returns an ``LLMResponse`` with content and usage metadata.
        Raises ``LLMError`` on failure (from the provider).
        """
        model_name = model or self.default_model
        return await self.provider.complete(
            system=system,
            user=user,
            model=model_name,
            max_tokens=max_tokens,
            temperature=temperature,
        )

    async def generate_json(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0,
    ) -> dict:
        """Call the LLM and parse the response as JSON.

        Automatically strips markdown code fences and trailing text.
        Raises ``LLMError`` on API failure or if the response is not valid JSON.
        """
        resp = await self._call_api(
            system=system, user=user, model=model,
            max_tokens=max_tokens, temperature=temperature,
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
        temperature: float = 0,
    ) -> tuple[dict, LLMResponse]:
        """Call the LLM, parse JSON, and return both the parsed dict and metadata."""
        resp = await self._call_api(
            system=system, user=user, model=model,
            max_tokens=max_tokens, temperature=temperature,
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
        temperature: float = 0,
    ) -> str:
        """Call the LLM and return the raw text response."""
        resp = await self._call_api(
            system=system, user=user, model=model,
            max_tokens=max_tokens, temperature=temperature,
        )
        return resp.text

    async def generate_text_with_metadata(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0,
    ) -> tuple[str, LLMResponse]:
        """Call the LLM and return both the raw text and metadata."""
        resp = await self._call_api(
            system=system, user=user, model=model,
            max_tokens=max_tokens, temperature=temperature,
        )
        return resp.text, resp


class MultiModelLLMClient:
    """Routes calls to different LLMClient instances based on pass name."""

    def __init__(self, clients: dict[str, LLMClient]) -> None:
        self._clients = clients

    def for_pass(self, pass_name: str) -> LLMClient:
        """Return the LLMClient configured for a specific pipeline pass."""
        if pass_name not in self._clients:
            raise ValueError(f"No LLM client configured for pass: {pass_name}")
        return self._clients[pass_name]