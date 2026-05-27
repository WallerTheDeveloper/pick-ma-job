"""Tests for core.providers.anthropic_provider — retry logic and response normalization."""

import time
from unittest.mock import AsyncMock, MagicMock, patch

import anthropic
import pytest

from core.llm_provider import LLMResponse
from core.providers.anthropic_provider import AnthropicProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
# Successful completion
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_returns_llm_response():
    mock_response = _make_message_response("hello world", input_tokens=5, output_tokens=10)
    provider = AnthropicProvider(api_key="test-key", default_max_retries=2)
    provider._client = MagicMock()
    provider._client.messages.create = AsyncMock(return_value=mock_response)

    result = await provider.complete(
        system="system prompt", user="user prompt", model="test-model",
    )

    assert isinstance(result, LLMResponse)
    assert result.text == "hello world"
    assert result.model == "test-model"
    assert result.input_tokens == 5
    assert result.output_tokens == 10
    assert result.duration_ms >= 0


@pytest.mark.asyncio
async def test_complete_passes_all_parameters():
    mock_response = _make_message_response("ok")
    provider = AnthropicProvider(api_key="test-key", default_max_retries=2)
    provider._client = MagicMock()
    provider._client.messages.create = AsyncMock(return_value=mock_response)

    await provider.complete(
        system="sys", user="usr", model="mymodel",
        max_tokens=2048, temperature=0.5,
    )

    call_kwargs = provider._client.messages.create.call_args.kwargs
    assert call_kwargs["model"] == "mymodel"
    assert call_kwargs["max_tokens"] == 2048
    assert call_kwargs["temperature"] == 0.5
    assert call_kwargs["system"] == "sys"
    assert call_kwargs["messages"] == [{"role": "user", "content": "usr"}]


# ---------------------------------------------------------------------------
# Retry logic: 529 server error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_retries_on_529_then_succeeds():
    provider = AnthropicProvider(api_key="test-key", default_max_retries=6)
    provider._client = MagicMock()
    error_529 = _make_api_status_error(529, "overloaded")
    success_msg = _make_message_response("ok")
    provider._client.messages.create = AsyncMock(side_effect=[error_529, success_msg])

    with patch("core.providers.anthropic_provider.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await provider.complete(system="sys", user="usr", model="test")
    assert result.text == "ok"
    assert provider._client.messages.create.call_count == 2
    mock_sleep.assert_called_once()


# ---------------------------------------------------------------------------
# Retry logic: 429 rate limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_retries_on_429_then_succeeds():
    provider = AnthropicProvider(api_key="test-key", default_max_retries=6)
    provider._client = MagicMock()
    error_429 = _make_api_status_error(429, "rate limited")
    success_msg = _make_message_response("ok")
    provider._client.messages.create = AsyncMock(side_effect=[error_429, success_msg])

    with patch("core.providers.anthropic_provider.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await provider.complete(system="sys", user="usr", model="test")
    assert result.text == "ok"
    assert provider._client.messages.create.call_count == 2
    mock_sleep.assert_called_once()


# ---------------------------------------------------------------------------
# Retry logic: Retry-After header
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_429_uses_retry_after_header():
    mock_response = MagicMock(status_code=429)
    mock_response.headers = {"retry-after": "5"}
    provider = AnthropicProvider(api_key="test-key", default_max_retries=6)
    provider._client = MagicMock()
    error_429 = anthropic.APIStatusError(message="rate limited", response=mock_response, body=None)
    success_msg = _make_message_response("ok")
    provider._client.messages.create = AsyncMock(side_effect=[error_429, success_msg])

    with patch("core.providers.anthropic_provider.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await provider.complete(system="sys", user="usr", model="test")
    assert result.text == "ok"
    call_args = mock_sleep.call_args[0][0]
    assert 5.0 <= call_args <= 7.0  # 5s + 0-2s jitter


# ---------------------------------------------------------------------------
# Retry logic: Exhausting retries raises LLMError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_exhausts_retries_raises_llm_error():
    provider = AnthropicProvider(api_key="test-key", default_max_retries=3)
    provider._client = MagicMock()
    error_529 = _make_api_status_error(529, "overloaded")
    provider._client.messages.create = AsyncMock(side_effect=[error_529, error_529, error_529])

    with patch("core.providers.anthropic_provider.asyncio.sleep", new_callable=AsyncMock):
        from core.llm_client import LLMError
        with pytest.raises(LLMError, match="529") as exc_info:
            await provider.complete(system="sys", user="usr", model="test")
    assert exc_info.value.retryable is True
    assert provider._client.messages.create.call_count == 3


# ---------------------------------------------------------------------------
# Retry logic: Non-retryable error raises immediately
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_non_retryable_error_raises_immediately():
    provider = AnthropicProvider(api_key="test-key", default_max_retries=3)
    provider._client = MagicMock()
    error_400 = _make_api_status_error(400, "bad request")
    provider._client.messages.create = AsyncMock(side_effect=error_400)

    from core.llm_client import LLMError
    with pytest.raises(LLMError, match="400") as exc_info:
        await provider.complete(system="sys", user="usr", model="test")
    assert exc_info.value.retryable is False
    assert provider._client.messages.create.call_count == 1


# ---------------------------------------------------------------------------
# 429 on later attempts uses 60s minimum
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_429_on_later_attempts_uses_60s_minimum():
    mock_response = MagicMock(status_code=429)
    mock_response.headers = {}
    provider = AnthropicProvider(api_key="test-key", default_max_retries=6)
    provider._client = MagicMock()
    error_429 = anthropic.APIStatusError(message="rate limited", response=mock_response, body=None)
    success_msg = _make_message_response("ok")
    provider._client.messages.create = AsyncMock(
        side_effect=[error_429, error_429, error_429, success_msg]
    )

    with patch("core.providers.anthropic_provider.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        result = await provider.complete(system="sys", user="usr", model="test")
    assert result.text == "ok"
    assert provider._client.messages.create.call_count == 4
    assert mock_sleep.call_count == 3


# ---------------------------------------------------------------------------
# _parse_retry_after
# ---------------------------------------------------------------------------


def test_parse_retry_after_from_header():
    mock_response = MagicMock()
    mock_response.headers = {"retry-after": "10"}
    exc = anthropic.APIStatusError(message="rate limited", response=mock_response, body=None)
    result = AnthropicProvider._parse_retry_after(exc, 0)
    assert result == 10.0


def test_parse_retry_after_fallback():
    mock_response = MagicMock()
    mock_response.headers = {}
    exc = anthropic.APIStatusError(message="rate limited", response=mock_response, body=None)
    result = AnthropicProvider._parse_retry_after(exc, 2)
    assert result == 4.5  # 2**2 + 0.5
