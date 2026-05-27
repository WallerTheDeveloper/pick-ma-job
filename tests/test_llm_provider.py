"""Tests for core.llm_provider — provider protocol and AnthropicProvider."""

import pytest

from core.llm_provider import LLMProvider, LLMResponse, create_provider


# ---------------------------------------------------------------------------
# LLMResponse
# ---------------------------------------------------------------------------


def test_llm_response_is_frozen():
    """LLMResponse is a frozen dataclass — attribute assignment raises."""
    resp = LLMResponse(text="hi", model="m", input_tokens=1, output_tokens=2, duration_ms=100)
    with pytest.raises(AttributeError):
        resp.text = "bye"  # type: ignore[misc]


def test_llm_response_fields():
    resp = LLMResponse(text="hello", model="gpt-5", input_tokens=10, output_tokens=20, duration_ms=300)
    assert resp.text == "hello"
    assert resp.model == "gpt-5"
    assert resp.input_tokens == 10
    assert resp.output_tokens == 20
    assert resp.duration_ms == 300


# ---------------------------------------------------------------------------
# create_provider factory
# ---------------------------------------------------------------------------


def test_create_provider_anthropic():
    """create_provider('anthropic', ...) returns an AnthropicProvider instance."""
    from core.providers.anthropic_provider import AnthropicProvider
    provider = create_provider("anthropic", api_key="test-key")
    assert isinstance(provider, AnthropicProvider)


def test_create_provider_anthropic_with_kwargs():
    """create_provider passes kwargs through to AnthropicProvider."""
    provider = create_provider("anthropic", api_key="test-key", default_max_retries=3)
    assert provider._max_retries == 3


def test_create_provider_unknown_raises():
    """create_provider raises ValueError for unknown provider names."""
    with pytest.raises(ValueError, match="Unknown provider: openai"):
        create_provider("openai", api_key="test-key")


# ---------------------------------------------------------------------------
# LLMProvider protocol (structural typing)
# ---------------------------------------------------------------------------


class DummyProvider:
    """A minimal provider that satisfies the LLMProvider protocol."""

    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0,
    ) -> LLMResponse:
        return LLMResponse(
            text=f"{system}|{user}|{model}|{max_tokens}|{temperature}",
            model=model,
            input_tokens=0,
            output_tokens=0,
            duration_ms=0,
        )


def test_llm_provider_protocol_is_runtime_checkable():
    """DummyProvider satisfies the LLMProvider protocol at runtime."""
    assert isinstance(DummyProvider(), LLMProvider)


def test_non_provider_is_not_instance():
    """A class without complete() does not satisfy LLMProvider."""

    class NotAProvider:
        pass

    assert not isinstance(NotAProvider(), LLMProvider)