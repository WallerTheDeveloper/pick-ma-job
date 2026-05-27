"""Tests for core.llm_client — provider is mocked throughout."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.llm_client import LLMClient, LLMError, MultiModelLLMClient, _strip_json_fences
from core.llm_provider import LLMResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_JSON = {"result": "ok", "score": 8}


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


class FailingProvider:
    """A mock provider that raises LLMError on all calls."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0,
    ) -> LLMResponse:
        raise self._error


class SequentialProvider:
    """A mock provider that returns texts in sequence, then repeats the last."""

    def __init__(self, texts: list[str]) -> None:
        self._texts = list(texts)
        self._index = 0

    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0,
    ) -> LLMResponse:
        idx = min(self._index, len(self._texts) - 1)
        text = self._texts[idx]
        self._index += 1
        return LLMResponse(
            text=text,
            model=model,
            input_tokens=10,
            output_tokens=20,
            duration_ms=100,
        )


def _make_llm(response_text: str) -> LLMClient:
    provider = MockProvider(response_text=response_text)
    return LLMClient(provider=provider, default_model="test-model")


# ---------------------------------------------------------------------------
# _strip_json_fences
# ---------------------------------------------------------------------------


def test_strip_clean_json():
    assert _strip_json_fences(json.dumps(VALID_JSON)) == json.dumps(VALID_JSON)


def test_strip_json_fences():
    fenced = f"```json\n{json.dumps(VALID_JSON)}\n```"
    assert _strip_json_fences(fenced) == json.dumps(VALID_JSON)


def test_strip_plain_fences():
    fenced = f"```\n{json.dumps(VALID_JSON)}\n```"
    assert _strip_json_fences(fenced) == json.dumps(VALID_JSON)


def test_strip_fences_with_whitespace():
    fenced = f"  ```json\n{json.dumps(VALID_JSON)}\n```  "
    assert _strip_json_fences(fenced) == json.dumps(VALID_JSON)


# ---------------------------------------------------------------------------
# generate_json
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_json_clean():
    llm = _make_llm(json.dumps(VALID_JSON))
    result = await llm.generate_json(system="sys", user="usr")
    assert result == VALID_JSON


@pytest.mark.asyncio
async def test_generate_json_with_fences():
    fenced = f"```json\n{json.dumps(VALID_JSON)}\n```"
    llm = _make_llm(fenced)
    result = await llm.generate_json(system="sys", user="usr")
    assert result == VALID_JSON


@pytest.mark.asyncio
async def test_generate_json_invalid_raises_llm_error():
    llm = _make_llm("not json at all")
    with pytest.raises(LLMError, match="invalid JSON"):
        await llm.generate_json(system="sys", user="usr")


@pytest.mark.asyncio
async def test_generate_json_passes_model_and_max_tokens():
    provider = MockProvider(response_text=json.dumps(VALID_JSON))
    llm = LLMClient(provider=provider, default_model="default-model")
    await llm.generate_json(system="sys", user="usr", model="override-model", max_tokens=2048)
    assert provider.calls[-1]["model"] == "override-model"
    assert provider.calls[-1]["max_tokens"] == 2048


@pytest.mark.asyncio
async def test_generate_json_uses_default_model():
    provider = MockProvider(response_text=json.dumps(VALID_JSON))
    llm = LLMClient(provider=provider, default_model="default-model")
    await llm.generate_json(system="sys", user="usr")
    assert provider.calls[-1]["model"] == "default-model"


# ---------------------------------------------------------------------------
# generate_text
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_text_returns_raw():
    llm = _make_llm("hello world")
    result = await llm.generate_text(system="sys", user="usr")
    assert result == "hello world"


@pytest.mark.asyncio
async def test_generate_text_passes_params():
    provider = MockProvider(response_text="response")
    llm = LLMClient(provider=provider, default_model="dm")
    await llm.generate_text(system="s", user="u", model="m", max_tokens=16)
    assert provider.calls[-1]["model"] == "m"
    assert provider.calls[-1]["max_tokens"] == 16


# ---------------------------------------------------------------------------
# Temperature parameter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_generate_json_passes_temperature():
    provider = MockProvider(response_text=json.dumps(VALID_JSON))
    llm = LLMClient(provider=provider, default_model="test-model")
    await llm.generate_json(system="sys", user="usr", temperature=0.3)
    assert provider.calls[-1]["temperature"] == 0.3


@pytest.mark.asyncio
async def test_generate_text_passes_temperature():
    provider = MockProvider(response_text="ok")
    llm = LLMClient(provider=provider, default_model="test-model")
    await llm.generate_text(system="sys", user="usr", temperature=0.7)
    assert provider.calls[-1]["temperature"] == 0.7


@pytest.mark.asyncio
async def test_default_temperature_is_zero():
    provider = MockProvider(response_text="ok")
    llm = LLMClient(provider=provider, default_model="test-model")
    await llm.generate_text(system="sys", user="usr")
    assert provider.calls[-1]["temperature"] == 0


# ---------------------------------------------------------------------------
# Error propagation from provider
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_error_propagates_as_llm_error():
    err = LLMError("Anthropic API error 400: bad request", retryable=False)
    provider = FailingProvider(error=err)
    llm = LLMClient(provider=provider, default_model="test")
    with pytest.raises(LLMError, match="400") as exc_info:
        await llm.generate_text(system="sys", user="usr")
    assert exc_info.value.retryable is False


@pytest.mark.asyncio
async def test_provider_retryable_error_propagates():
    err = LLMError("Anthropic API error 429: rate limited", retryable=True)
    provider = FailingProvider(error=err)
    llm = LLMClient(provider=provider, default_model="test")
    with pytest.raises(LLMError, match="429") as exc_info:
        await llm.generate_text(system="sys", user="usr")
    assert exc_info.value.retryable is True


# ---------------------------------------------------------------------------
# LLMClient is frozen
# ---------------------------------------------------------------------------


def test_llm_client_is_immutable():
    llm = _make_llm("")
    with pytest.raises(Exception):
        llm.default_model = "other"  # type: ignore[misc]