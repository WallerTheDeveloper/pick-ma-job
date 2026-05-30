# Task 01 — Multi-Provider LLM Client Refactor

**Size:** L  
**Status:** done  
**Priority:** HIGH  
**Depends on:** —

## Goal

Refactor `LLMClient` from a hard-coded Anthropic wrapper into a provider-agnostic abstraction. Adding a new LLM provider (OpenAI, Google Gemini, Mistral, etc.) should require only:
1. A new adapter class implementing `LLMProvider` interface
2. A config entry in `settings.json`
3. No changes to service code (`Evaluator`, `CVService`, `PipelineService`)

## Problem

Current `core/llm_client.py`:
- Is a `@dataclass(frozen=True)` that wraps `anthropic.AsyncAnthropic` directly
- Hardcodes `temperature=0` in `_call_api`
- Returns `LLMResponse` with Anthropic-specific assumptions (single text block)
- Has retry logic specific to Anthropic status codes (429, 503, 529)
- All callers go through `LLMClient` which only knows Anthropic

Adding a second provider (e.g., OpenAI for the humanization pass) would require:
- Duplicating retry/fence-stripping logic per provider
- Service code knowing which provider to call for which pass
- Two separate error surfaces

## Design

### Provider Protocol

```python
# core/llm_provider.py

from dataclasses import dataclass
from typing import Protocol, AsyncIterator

@dataclass(frozen=True)
class LLMResponse:
    """Normalized LLM response — provider-agnostic."""
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    duration_ms: int

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
```

### Anthropic Adapter

```python
# core/providers/anthropic_provider.py

class AnthropicProvider:
    """Anthropic-specific adapter implementing LLMProvider."""

    def __init__(self, api_key: str, default_max_retries: int = 6) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._max_retries = default_max_retries

    async def complete(self, *, system, user, model, max_tokens, temperature) -> LLMResponse:
        # Same retry logic currently in LLMClient._call_api
        # Same rate-limit handling (429, 503, 529)
        # Returns normalized LLMResponse
```

### OpenAI Adapter (stub for now)

```python
# core/providers/openai_provider.py

class OpenAIProvider:
    """OpenAI-specific adapter implementing LLMProvider."""

    def __init__(self, api_key: str, default_max_retries: int = 6) -> None:
        self._client = openai.AsyncOpenAI(api_key=api_key)
        self._max_retries = default_max_retries

    async def complete(self, *, system, user, model, max_tokens, temperature) -> LLMResponse:
        # Retry on 429, 500, 503
        # Normalize OpenAI response to LLMResponse
```

### Refactored LLMClient

```python
# core/llm_client.py (refactored)

@dataclass(frozen=True)
class LLMClient:
    """Provider-agnostic LLM client. Delegates to the configured provider."""
    provider: LLMProvider  # Was: anthropic.AsyncAnthropic
    default_model: str
    default_max_retries: int = 6  # Kept for backward compat but retry is now per-provider

    async def generate_json(self, *, system, user, model=None, max_tokens=1024, temperature=0) -> dict: ...
    async def generate_json_with_metadata(self, *, system, user, model=None, max_tokens=1024, temperature=0) -> tuple[dict, LLMResponse]: ...
    async def generate_text(self, *, system, user, model=None, max_tokens=1024, temperature=0) -> str: ...
    async def generate_text_with_metadata(self, *, system, user, model=None, max_tokens=1024, temperature=0) -> tuple[str, LLMResponse]: ...
```

Key change: **every public method now accepts `temperature`** (defaults to 0 for backward compatibility). The provider's `complete()` method receives it directly.

### Provider Selection

```python
# core/llm_provider.py (continued)

def create_provider(provider_name: str, api_key: str, **kwargs) -> LLMProvider:
    """Factory function. Add new providers here."""
    if provider_name == "anthropic":
        from core.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(api_key=api_key, **kwargs)
    elif provider_name == "openai":
        from core.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(api_key=api_key, **kwargs)
    else:
        raise ValueError(f"Unknown provider: {provider_name}")
```

### Multi-Provider LLMClient

When different passes need different providers, the service receives a mapping:

```python
# core/llm_client.py addition

class MultiModelLLMClient:
    """Routes calls to different providers/models based on pass name."""

    def __init__(self, clients: dict[str, LLMClient]) -> None:
        self._clients = clients

    def for_pass(self, pass_name: str) -> LLMClient:
        """Return the LLMClient configured for a specific pipeline pass."""
        if pass_name not in self._clients:
            raise ValueError(f"No LLM client configured for pass: {pass_name}")
        return self._clients[pass_name]
```

### Config Changes

`configs/settings.json` — add provider configuration:

```json
{
  "providers": {
    "anthropic": {
      "api_key_env": "ANTHROPIC_API_KEY",
      "default_max_retries": 6
    }
  },
  "models": {
    "default": "claude-haiku-4-5-20251001",
    "cv_models": {
      "optimize": "claude-haiku-4-5-20251001",
      "humanize": "claude-sonnet-4-6-20250514",
      "keyword_audit": "claude-haiku-4-5-20251001"
    }
  }
}
```

To add OpenAI later:
```json
{
  "providers": {
    "anthropic": { "api_key_env": "ANTHROPIC_API_KEY" },
    "openai": { "api_key_env": "OPENAI_API_KEY" }
  },
  "models": {
    "cv_models": {
      "optimize": { "provider": "anthropic", "model": "claude-haiku-4-5-20251001" },
      "humanize": { "provider": "openai", "model": "gpt-5.4" }
    }
  }
}
```

### Dependency Injection Changes

`api/deps.py`:
- Replace `get_llm_client()` with `get_multi_model_client()` that reads config and creates per-pass `LLMClient` instances
- `LLMClient` construction goes from `LLMClient(client=anthropic_client, default_model=...)` to `LLMClient(provider=anthropic_provider, default_model=...)`

`main.py` lifespan:
- Remove `app.state.anthropic_client`
- Add `app.state.llm_client` = `MultiModelLLMClient` built from config

## Files to Create

| File | Purpose |
|------|--------|
| `core/llm_provider.py` | `LLMProvider` protocol, `LLMResponse` dataclass, `create_provider()` factory |
| `core/providers/__init__.py` | Package init |
| `core/providers/anthropic_provider.py` | Anthropic adapter with retry logic |

## Files to Modify

| File | Change |
|------|--------|
| `core/llm_client.py` | Accept `LLMProvider` instead of `AsyncAnthropic`; add `temperature` parameter to all public methods |
| `api/deps.py` | Build `MultiModelLLMClient` from config instead of single `LLMClient` |
| `main.py` | Remove `app.state.anthropic_client`, create `MultiModelLLMClient` in lifespan |
| `core/settings.py` | Parse `providers` and `models.cv_models` config |
| `configs/settings.json` | Add `providers` and `models` sections |
| `services/cv_service.py` | Accept `MultiModelLLMClient` instead of single `LLMClient`; use `for_pass("humanize")` etc. |
| `core/evaluator.py` | Same — accept `MultiModelLLMClient` or `LLMClient` for the default model |
| `tests/test_llm_client.py` | Update all tests — use mock provider instead of mock `AsyncAnthropic` |
| `requirements.txt` | No change — `anthropic` is already a dependency |

## Success Criteria

- [x] `LLMClient` accepts any `LLMProvider`, not just `AsyncAnthropic`
- [x] All public `LLMClient` methods accept `temperature` parameter (default 0)
- [x] Adding a new provider requires only: new adapter class + config entry + factory registration
- [x] `AnthropicProvider` preserves all existing retry logic (429/503/529 handling, Retry-After parsing)
- [x] `MultiModelLLMClient.for_pass("humanize")` returns a `LLMClient` configured with Sonnet 4.6
- [x] `MultiModelLLMClient.for_pass("optimize")` returns a `LLMClient` configured with Haiku 4.5
- [x] All existing tests pass without changes to service code assertions
- [x] `Evaluator` and `CVService` continue to work identically with the Anthropic provider
- [x] `temperature=0.3` can be passed through `LLMClient.generate_json()` to the provider