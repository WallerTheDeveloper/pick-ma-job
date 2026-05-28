"""Integration tests for the multi-provider LLM client system.

Tests that the LLMProvider protocol, AnthropicProvider, and MultiModelLLMClient
work together correctly — routing calls, passing temperature, and handling retries.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest

from core.llm_client import LLMClient, LLMError, MultiModelLLMClient
from core.llm_provider import LLMResponse, create_provider
from core.providers.anthropic_provider import AnthropicProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class MockProvider:
    """A mock LLMProvider that records calls and returns fixed responses."""

    def __init__(self, response_text: str = "mock response") -> None:
        self._response_text = response_text
        self.calls: list[dict] = []

    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0,
    ) -> LLMResponse:
        self.calls.append({
            "system": system,
            "user": user,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
        })
        return LLMResponse(
            text=self._response_text,
            model=model,
            input_tokens=10,
            output_tokens=20,
            duration_ms=100,
        )


class SequentialProvider:
    """A mock provider that returns different responses for each call."""

    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)
        self._index = 0
        self.calls: list[dict] = []

    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0,
    ) -> LLMResponse:
        self.calls.append({
            "system": system,
            "user": user,
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
        })
        resp = self._responses[self._index]
        self._index += 1
        return resp


def _make_client(
    model: str = "test-model",
    response_text: str = "ok",
    default_temperature: float = 0,
) -> LLMClient:
    provider = MockProvider(response_text=response_text)
    return LLMClient(provider=provider, default_model=model, default_temperature=default_temperature)


def _make_message_response(text: str, input_tokens: int = 10, output_tokens: int = 20) -> MagicMock:
    """Create a mock Anthropic message response."""
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    msg.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)
    return msg


def _make_api_status_error(status_code: int, message: str = "error", headers: dict | None = None) -> anthropic.APIStatusError:
    """Create a mock Anthropic APIStatusError."""
    response = MagicMock(status_code=status_code)
    response.headers = headers or {}
    return anthropic.APIStatusError(message=message, response=response, body=None)


# ---------------------------------------------------------------------------
# test_anthropic_provider_complete
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_anthropic_provider_complete():
    """AnthropicProvider.complete() returns an LLMResponse with correct fields."""
    mock_response = _make_message_response("hello world", input_tokens=5, output_tokens=10)
    provider = AnthropicProvider(api_key="test-key", default_max_retries=2)
    provider._client = MagicMock()
    provider._client.messages.create = AsyncMock(return_value=mock_response)

    result = await provider.complete(
        system="system prompt",
        user="user prompt",
        model="claude-sonnet-4-6-20250514",
    )

    assert isinstance(result, LLMResponse)
    assert result.text == "hello world"
    assert result.model == "claude-sonnet-4-6-20250514"
    assert result.input_tokens == 5
    assert result.output_tokens == 10
    assert result.duration_ms >= 0


# ---------------------------------------------------------------------------
# test_anthropic_provider_retry_on_429
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_anthropic_provider_retry_on_429():
    """AnthropicProvider retries on 429 and returns success on next attempt."""
    provider = AnthropicProvider(api_key="test-key", default_max_retries=6)
    provider._client = MagicMock()
    error_429 = _make_api_status_error(429, "rate limited")
    success_msg = _make_message_response("retried ok")
    provider._client.messages.create = AsyncMock(side_effect=[error_429, success_msg])

    with patch("core.providers.anthropic_provider.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await provider.complete(system="sys", user="usr", model="test")

    assert result.text == "retried ok"
    assert provider._client.messages.create.call_count == 2
    mock_sleep.assert_called_once()


# ---------------------------------------------------------------------------
# test_multi_model_client_for_pass
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_model_client_for_pass():
    """MultiModelLLMClient.for_pass('humanize') returns the Sonnet-configured client."""
    optimize_client = _make_client(model="claude-haiku-4-5-20251001", default_temperature=0)
    humanize_client = _make_client(model="claude-sonnet-4-6-20250514", default_temperature=0.3)

    multi = MultiModelLLMClient(clients={
        "optimize": optimize_client,
        "humanize": humanize_client,
    })

    result = await multi.for_pass("humanize").generate_text(system="sys", user="usr")
    assert result == "ok"

    # Verify the humanize client's provider received the call
    hum_provider = humanize_client.provider  # type: ignore[attr-defined]
    assert hum_provider.calls[-1]["model"] == "claude-sonnet-4-6-20250514"
    assert hum_provider.calls[-1]["temperature"] == 0.3


# ---------------------------------------------------------------------------
# test_multi_model_client_unknown_pass
# ---------------------------------------------------------------------------


def test_multi_model_client_unknown_pass():
    """MultiModelLLMClient.for_pass('unknown') raises ValueError."""
    multi = MultiModelLLMClient(clients={"optimize": _make_client()})
    with pytest.raises(ValueError, match="No LLM client configured for pass: unknown"):
        multi.for_pass("unknown")


# ---------------------------------------------------------------------------
# test_llm_client_temperature_passthrough
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_client_temperature_passthrough():
    """Temperature parameter reaches the provider from LLMClient."""
    # Test with generate_text
    provider = MockProvider(response_text="temperature test")
    client = LLMClient(provider=provider, default_model="test-model")
    await client.generate_text(system="sys", user="usr", temperature=0.7)
    assert provider.calls[0]["temperature"] == 0.7

    # Test with generate_json (needs valid JSON response)
    json_provider = MockProvider(response_text=json.dumps({"result": "ok"}))
    json_client = LLMClient(provider=json_provider, default_model="test-model")
    await json_client.generate_json(system="sys", user="usr", temperature=0.3)
    assert json_provider.calls[0]["temperature"] == 0.3


# ---------------------------------------------------------------------------
# test_create_provider_factory
# ---------------------------------------------------------------------------


def test_create_provider_factory():
    """create_provider('anthropic', ...) returns an AnthropicProvider instance."""
    provider = create_provider("anthropic", api_key="test-key")
    assert isinstance(provider, AnthropicProvider)


def test_create_provider_factory_unknown():
    """create_provider raises ValueError for unknown providers."""
    with pytest.raises(ValueError, match="Unknown provider: openai"):
        create_provider("openai", api_key="test-key")


# ---------------------------------------------------------------------------
# test_multi_model_client_full_pipeline_routing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_model_client_full_pipeline_routing():
    """Full pipeline: for_pass routes optimize, humanize, keyword_audit to correct models."""
    opt_provider = MockProvider(response_text=json.dumps({"sections": [{"title": "SUMMARY", "content": "opt", "changed": True}]}))
    hum_provider = MockProvider(response_text=json.dumps({"sections": [{"title": "SUMMARY", "content": "hum", "changed": True}]}))
    audit_provider = MockProvider(response_text=json.dumps({"present": [], "missing": [], "forced": [], "patches": []}))

    opt_client = LLMClient(provider=opt_provider, default_model="haiku-model", default_temperature=0)
    hum_client = LLMClient(provider=hum_provider, default_model="sonnet-model", default_temperature=0.3)
    audit_client = LLMClient(provider=audit_provider, default_model="haiku-model", default_temperature=0)

    multi = MultiModelLLMClient(clients={
        "optimize": opt_client,
        "humanize": hum_client,
        "keyword_audit": audit_client,
    })

    # Simulate the three LLM calls in the CV pipeline
    await multi.for_pass("optimize").generate_json(system="sys", user="usr")
    await multi.for_pass("humanize").generate_json(system="sys", user="usr")
    await multi.for_pass("keyword_audit").generate_json(system="sys", user="usr")

    # Verify each provider was called with the correct model and temperature
    assert opt_provider.calls[0]["model"] == "haiku-model"
    assert opt_provider.calls[0]["temperature"] == 0

    assert hum_provider.calls[0]["model"] == "sonnet-model"
    assert hum_provider.calls[0]["temperature"] == 0.3

    assert audit_provider.calls[0]["model"] == "haiku-model"
    assert audit_provider.calls[0]["temperature"] == 0
