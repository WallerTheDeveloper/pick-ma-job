"""Tests for core.llm_client.MultiModelLLMClient."""

import pytest

from core.llm_client import LLMClient, MultiModelLLMClient
from core.llm_provider import LLMResponse


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class MockProvider:
    """A mock provider that records calls and returns fixed responses."""

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


def _make_client(model: str = "test-model", response_text: str = "ok") -> LLMClient:
    provider = MockProvider(response_text=response_text)
    return LLMClient(provider=provider, default_model=model)


# ---------------------------------------------------------------------------
# MultiModelLLMClient tests
# ---------------------------------------------------------------------------


def test_for_pass_returns_correct_client():
    """for_pass() routes to the correct LLMClient for each pass name."""
    optimize_client = _make_client(model="haiku-model")
    humanize_client = _make_client(model="sonnet-model")

    multi = MultiModelLLMClient(clients={
        "optimize": optimize_client,
        "humanize": humanize_client,
    })

    assert multi.for_pass("optimize") is optimize_client
    assert multi.for_pass("humanize") is humanize_client


def test_for_pass_raises_for_unknown_pass():
    """for_pass() raises ValueError for an unknown pass name."""
    multi = MultiModelLLMClient(clients={"optimize": _make_client()})
    with pytest.raises(ValueError, match="No LLM client configured for pass: unknown"):
        multi.for_pass("unknown")


def test_for_pass_empty_clients_raises():
    """for_pass() raises ValueError when no clients are configured."""
    multi = MultiModelLLMClient(clients={})
    with pytest.raises(ValueError, match="No LLM client configured for pass: optimize"):
        multi.for_pass("optimize")


@pytest.mark.asyncio
async def test_multi_model_routes_to_correct_model():
    """Calls through for_pass() use the correct model."""
    optimize_client = _make_client(model="haiku-model")
    humanize_client = _make_client(model="sonnet-model")

    multi = MultiModelLLMClient(clients={
        "optimize": optimize_client,
        "humanize": humanize_client,
    })

    result = await multi.for_pass("optimize").generate_text(system="sys", user="usr")
    assert result == "ok"

    result = await multi.for_pass("humanize").generate_text(system="sys", user="usr")
    assert result == "ok"

    # Verify the providers received the correct models
    opt_provider = optimize_client.provider  # type: ignore[attr-defined]
    hum_provider = humanize_client.provider  # type: ignore[attr-defined]
    assert opt_provider.calls[-1]["model"] == "haiku-model"
    assert hum_provider.calls[-1]["model"] == "sonnet-model"


@pytest.mark.asyncio
async def test_temperature_passes_through():
    """Temperature parameter passes through MultiModelLLMClient to the provider."""
    provider = MockProvider()
    client = LLMClient(provider=provider, default_model="test-model")
    multi = MultiModelLLMClient(clients={"humanize": client})

    await multi.for_pass("humanize").generate_text(
        system="sys", user="usr", temperature=0.3
    )
    assert provider.calls[0]["temperature"] == 0.3


@pytest.mark.asyncio
async def test_default_temperature_is_zero():
    """Temperature defaults to 0 when not specified."""
    provider = MockProvider()
    client = LLMClient(provider=provider, default_model="test-model")
    multi = MultiModelLLMClient(clients={"optimize": client})

    await multi.for_pass("optimize").generate_text(system="sys", user="usr")
    assert provider.calls[0]["temperature"] == 0
