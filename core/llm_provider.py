"""Provider-agnostic LLM interface.

Any LLM provider (Anthropic, OpenAI, Google, etc.) must implement
the LLMProvider protocol to work with LLMClient.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class LLMResponse:
    """Normalized LLM response — provider-agnostic."""

    text: str
    model: str
    input_tokens: int
    output_tokens: int
    duration_ms: int


@runtime_checkable
class LLMProvider(Protocol):
    """Interface that any LLM provider must implement."""

    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int = 1024,
        temperature: float = 0,
    ) -> LLMResponse: ...


def create_provider(provider_name: str, api_key: str, **kwargs: object) -> LLMProvider:
    """Factory function. Add new providers here."""
    if provider_name == "anthropic":
        from core.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(api_key=api_key, **kwargs)
    raise ValueError(f"Unknown provider: {provider_name}")
