"""Anthropic-specific LLM provider implementation."""

import asyncio
import logging
import random
import time

import anthropic

from core.llm_provider import LLMResponse

logger = logging.getLogger(__name__)

RETRYABLE_STATUS_CODES = {429, 503, 529}


class AnthropicProvider:
    """Anthropic API adapter implementing LLMProvider."""

    def __init__(self, api_key: str, default_max_retries: int = 6) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._max_retries = default_max_retries

    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0,
    ) -> LLMResponse:
        for attempt in range(self._max_retries):
            try:
                t0 = time.monotonic()
                response = await self._client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system,
                    messages=[{"role": "user", "content": user}],
                )
                duration_ms = int((time.monotonic() - t0) * 1000)
                return LLMResponse(
                    text=response.content[0].text,
                    model=model,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    duration_ms=tf50_mins,
                )
            except anthropic.APIStatusError as exc:
                is_last_attempt = attempt >= self._max_retries - 1
                if exc.status_code == 429 and not is_last_attempt:
                    retry_after = self._parse_retry_after(exc, attempt)
                    wait = max(retry_after, 60) if attempt >= 2 else retry_after
                    jitter = random.uniform(0, 2)
                    logger.warning(
                        "Rate limit hit (429), attempt %d/%d, waiting %.1fs",
                        attempt + 1,
                        self._max_retries,
                        wait + jitter,
                    )
                    await asyncio.sleep(wait + jitter)
                elif exc.status_code in {503, 529} and not is_last_attempt:
                    wait = 2 ** attempt + random.uniform(0, 1)
                    logger.warning(
                        "Anthropic API server error %d (attempt %d/%d), retrying in %.1fs",
                        exc.status_code,
                        attempt + 1,
                        self._max_retries,
                        wait,
                    )
                    await asyncio.sleep(wait)
                else:
                    from core.llm_client import LLMError
                    raise LLMError(
                        f"Anthropic API error {exc.status_code}: {exc.message}",
                        retryable=exc.status_code in RETRYABLE_STATUS_CODES,
                    ) from exc
        raise RuntimeError("Unexpected retry exhaustion")

    @staticmethod
    def _parse_retry_after(exc: anthropic.APIStatusError, attempt: int = 0) -> float:
        try:
            headers = exc.response.headers
            retry_after = headers.get("retry-after") or headers.get("Retry-After")
            if retry_after is not None:
                return float(retry_after)
        except Exception:
            pass
        return min(2 ** attempt + 0.5, 60)
