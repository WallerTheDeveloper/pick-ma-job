# v1.4.1 Anti-Detection CV Humanization — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 5-pass CV humanization pipeline that transforms AI-generated CV text into human-sounding text resistant to AI detection, backed by a provider-agnostic LLM client that makes adding new AI providers trivial.

**Architecture:** The existing single-pass CV customizer (Pass 1) is extended with four additional passes: skeleton extraction (algorithmic), human-voice rewrite (Sonnet at temp 0.3), keyword audit (Haiku at temp 0), and statistical post-processing (algorithmic). The LLM client is refactored from a hard-coded Anthropic wrapper into a protocol-based multi-provider system with per-pass routing.

**Tech Stack:** Python 3.12, FastAPI, asyncpg, Anthropic SDK, Pydantic, Pytest

---

## Dependency Graph

```
T01 (Multi-Provider LLM Client) ──┬──→ T03 (Humanization Pipeline)
                                   ├──→ T05 (Per-Pass Config)
                                   └──→ T07 (Integration Tests)
T02 (Humanization Prompts) ────────→ T03 (Humanization Pipeline)
T03 (Humanization Pipeline) ───────→ T04 (AI-Tell Detection)
                                   └──→ T06 (Frontend UI)
T04 (AI-Tell Detection) ───────────→ T07 (Integration Tests)
```

Execution order: **T01 → T02 → T04 → T03 → T05 → T06 → T07**

T01 and T02 can be done in parallel. T04 can start once its interfaces are defined (no dependency on T03's implementation, only on its spec). T05 depends on T01 being done. T06 depends on T03. T07 depends on everything.

---

## File Structure

### New Files

| File | Purpose |
|------|---------|
| `core/llm_provider.py` | LLMProvider protocol, LLMResponse dataclass, create_provider() factory |
| `core/providers/__init__.py` | Package init |
| `core/providers/anthropic_provider.py` | Anthropic adapter with retry logic (migrated from llm_client.py) |
| `core/humanizer.py` | Algorithmic post-processing: AI tell removal, sentence variety, contractions |
| `configs/prompts/cv_humanize.json` | Pass 3 prompt — human-voice rewrite (Sonnet, temp 0.3) |
| `configs/prompts/cv_keyword_audit.json` | Pass 4 prompt — keyword alignment audit (Haiku, temp 0) |
| `tests/test_llm_provider.py` | Tests for provider protocol and AnthropicProvider |
| `tests/test_humanizer.py` | Tests for core/humanizer.py |
| `tests/test_humanization_pipeline.py` | Integration tests for full pipeline |
| `tests/test_multi_model_client.py` | Tests for MultiModelLLMClient |

### Modified Files

| File | Change |
|------|--------|
| `core/llm_client.py` | Accept LLMProvider instead of AsyncAnthropic; add temperature param; add MultiModelLLMClient |
| `core/settings.py` | Add CVModelConfig dataclass; parse cv_models from settings.json |
| `services/cv_service.py` | Add humanization pipeline methods; load new prompt files; add humanize param |
| `api/deps.py` | Build MultiModelLLMClient from config instead of single LLMClient |
| `api/schemas.py` | Add humanize field to CVCustomizeRequest |
| `api/routes/api_cv.py` | Pass humanize param to cv_service.customize_cv() |
| `main.py` | Remove app.state.anthropic_client; create MultiModelLLMClient in lifespan |
| `configs/settings.json` | Add providers and cv_models sections |
| `frontend/src/api/cv.ts` | Add humanize param to customizeCV() |
| `frontend/src/hooks/use-cv.ts` | Pass humanize through |
| `frontend/src/components/customize-cv-dialog.tsx` | Add toggle, badge, tooltip |

---

## Task 1: Multi-Provider LLM Client Refactor

**Depends on:** Nothing

### Step 1.1: Create the LLMProvider protocol

- [ ] **Create `core/llm_provider.py`**

```python
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
```

- [ ] **Commit:** `feat: add LLMProvider protocol and factory`

### Step 1.2: Create AnthropicProvider

- [ ] **Create `core/providers/__init__.py`** (empty)

- [ ] **Create `core/providers/anthropic_provider.py`**

Move all Anthropic-specific retry logic from `core/llm_client.py` into the new `AnthropicProvider`. This includes the retry loop, rate-limit handling, and Retry-After parsing.

```python
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
                    duration_ms=duration_ms,
                )
            except anthropic.APIStatusError as exc:
                is_last_attempt = attempt >= self._max_retries - 1
                if exc.status_code == 429 and not is_last_attempt:
                    retry_after = self._parse_retry_after(exc, attempt)
                    wait = max(retry_after, 60) if attempt >= 2 else retry_after
                    jitter = random.uniform(0, 2)
                    logger.warning(
                        "Rate limit hit (429), attempt %d/%d, waiting %.1fs",
                        attempt + 1, self._max_retries, wait + jitter,
                    )
                    await asyncio.sleep(wait + jitter)
                elif exc.status_code in {503, 529} and not is_last_attempt:
                    wait = 2 ** attempt + random.uniform(0, 1)
                    logger.warning(
                        "Anthropic API server error %d (attempt %d/%d), retrying in %.1fs",
                        exc.status_code, attempt + 1, self._max_retries, wait,
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
```

- [ ] **Commit:** `feat: add AnthropicProvider with retry logic`

### Step 1.3: Refactor LLMClient to use provider

- [ ] **Update `core/llm_client.py`**

Key changes:
1. Accept `LLMProvider` instead of `anthropic.AsyncAnthropic` as `client` field
2. Add `temperature` parameter to all public methods (default 0)
3. Remove internal `_call_api` retry logic (moved to provider)
4. Add `MultiModelLLMClient` class
5. Keep `LLMError` and `_parse_json_text` / `_strip_json_fences` as-is

The `LLMClient` becomes thin — it delegates to the provider and handles JSON parsing:

```python
@dataclass(frozen=True)
class LLMClient:
    """Provider-agnostic LLM client. Delegates to the configured provider."""
    provider: LLMProvider  # Changed from: anthropic.AsyncAnthropic
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
        resp = await self._call_api(system=system, user=user, model=model, max_tokens=max_tokens, temperature=temperature)
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
        resp = await self._call_api(system=system, user=user, model=model, max_tokens=max_tokens, temperature=temperature)
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
        resp = await self._call_api(system=system, user=user, model=model, max_tokens=max_tokens, temperature=temperature)
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
        resp = await self._call_api(system=system, user=user, model=model, max_tokens=max_tokens, temperature=temperature)
        return resp.text, resp
```

Add `MultiModelLLMClient`:

```python
class MultiModelLLMClient:
    """Routes calls to different LLMClient instances based on pass name."""

    def __init__(self, clients: dict[str, LLMClient]) -> None:
        self._clients = clients

    def for_pass(self, pass_name: str) -> LLMClient:
        if pass_name not in self._clients:
            raise ValueError(f"No LLM client configured for pass: {pass_name}")
        return self._clients[pass_name]
```

- [ ] **Commit:** `refactor: LLMClient accepts LLMProvider, adds temperature and MultiModelLLMClient`

### Step 1.4: Write tests for provider and client

- [ ] **Create `tests/test_llm_provider.py`**

Test that AnthropicProvider can be constructed, that create_provider routes correctly, that temperature passes through.

- [ ] **Create `tests/test_multi_model_client.py`**

Test that MultiModelLLMClient.for_pass() routes to correct client, raises ValueError for unknown pass.

- [ ] **Update existing tests** — wherever `LLMClient(client=mock_anthropic, ...)` appears, change to `LLMClient(provider=mock_provider, ...)`. The mock should implement the `LLMProvider` protocol.

- [ ] **Run all tests:** `pytest` — ensure everything passes with the refactored client.

- [ ] **Commit:** `test: add provider and multi-model tests, update existing mocks`

### Step 1.5: Update dependency injection

- [ ] **Update `api/deps.py`**

Replace `get_llm_client()` with a function that builds a `MultiModelLLMClient` from settings. Each pass gets its own `LLMClient` with the right provider, model, and temperature.

- [ ] **Update `main.py` lifespan**

Remove `app.state.anthropic_client`. Create `AnthropicProvider` from `ANTHROPIC_API_KEY` env var, then build `LLMClient` instances for each pass, then build `MultiModelLLMClient`.

- [ ] **Update `services/cv_service.py`**

The `CVService.__init__` should accept `MultiModelLLMClient` instead of `LLMClient`. All existing calls to `self._llm.generate_json(...)` should use `self._llm.for_pass("optimize").generate_json(...)`. For backward compat, `for_pass("optimize")` returns the default client (Haiku).

- [ ] **Update `core/evaluator.py`**

The `Evaluator` can continue using a plain `LLMClient` since it doesn't need multi-model routing. Update its constructor to accept `LLMClient` created from an `AnthropicProvider`.

- [ ] **Update `core/settings.py`**

Add `CVModelConfig` dataclass and `cv_models` field.

- [ ] **Update `configs/settings.json`**

Add the `cv_models` section with optimize, humanize, and keyword_audit entries.

- [ ] **Run all tests:** `pytest`

- [ ] **Commit:** `feat: wire up MultiModelLLMClient in deps, main, and settings`

---

## Task 2: Humanization Prompts

**Depends on:** Nothing (can be done in parallel with T01)

### Step 2.1: Create cv_humanize.json

- [ ] **Create `configs/prompts/cv_humanize.json`** with the exact prompt content from T02 spec (the system prompt with anti-AI patterns, human-voice instructions, hard boundaries, and JSON output format; model "claude-sonnet-4-6-20250514"; temperature 0.3).

- [ ] **Commit:** `feat: add cv_humanize.json prompt for Pass 3`

### Step 2.2: Create cv_keyword_audit.json

- [ ] **Create `configs/prompts/cv_keyword_audit.json`** with the exact prompt content from T02 spec (the audit prompt with present/missing/forced/patches JSON output format; model "claude-haiku-4-5-20251001"; temperature 0).

- [ ] **Commit:** `feat: add cv_keyword_audit.json prompt for Pass 4`

---

## Task 3: AI-Tell Detection & Post-Processing

**Depends on:** Nothing (can start once interfaces are clear)

### Step 3.1: Create core/humanizer.py with AI tell replacements

- [ ] **Create `core/humanizer.py`**

Implement the `AI_TELL_REPLACEMENTS` dict (50+ entries as specified in T03/T04), the `_CONTRACTION_MAP`, and all five functions:
- `remove_ai_tells(text: str) -> str`
- `ensure_sentence_opener_variety(text: str) -> str`
- `ensure_sentence_length_variance(text: str, min_variance: float = 0.3) -> str`
- `enforce_contractions(text: str, probability: float = 0.3, seed: int | None = None) -> str`
- `postprocess_humanization(text: str) -> str` (chains all four)

- [ ] **Commit:** `feat: add core/humanizer.py with AI-tell removal and sentence variety`

### Step 3.2: Write tests for humanizer

- [ ] **Create `tests/test_humanizer.py`** with all test cases from T04 spec. Run `pytest tests/test_humanizer.py -v` and ensure all pass.

- [ ] **Commit:** `test: add comprehensive humanizer tests`

---

## Task 4: Humanization Pipeline Service

**Depends on:** T01, T02, T03 (code is available)

### Step 4.1: Add prompt loading to cv_service.py

- [ ] **Update `services/cv_service.py`**

Add loading of `_HUMANIZE_PROMPT` and `_KEYWORD_AUDIT_PROMPT` at module level (same pattern as existing `_STRUCTURE_PROMPT` and `_CUSTOMIZE_PROMPT`).

- [ ] **Commit:** `feat: load humanization prompt configs in cv_service`

### Step 4.2: Implement _extract_skeleton (Pass 2)

- [ ] **Add `_extract_skeleton()` to `services/cv_service.py`**

Algorithmic method that takes the Pass 1 optimize result, the structured CV, and the job description, and returns a skeleton dict with target_keywords, must_include_facts, positioning, verified_skills/languages/certifications, and sections_json.

- [ ] **Commit:** `feat: implement _extract_skeleton for Pass 2`

### Step 4.3: Implement _call_humanize (Pass 3)

- [ ] **Add `_call_humanize()` to `services/cv_service.py`**

Uses `_llm.for_pass("humanize")` with the `cv_humanize.json` prompt at temperature 0.3. Returns diff-style JSON.

- [ ] **Commit:** `feat: implement _call_humanize for Pass 3`

### Step 4.4: Implement _call_keyword_audit and _apply_keyword_patches (Pass 4)

- [ ] **Add `_call_keyword_audit()` and `_apply_keyword_patches()` to `services/cv_service.py`**

Audit call uses `_llm.for_pass("keyword_audit")` with `cv_keyword_audit.json`. Patch application is algorithmic.

- [ ] **Commit:** `feat: implement keyword audit and patch application for Pass 4`

### Step 4.5: Implement _humanize_cv (orchestrator) and update customize_cv

- [ ] **Add `_humanize_cv()` method** that chains Passes 2-5:
  1. `_extract_skeleton()`
  2. `_call_humanize()`
  3. `_call_keyword_audit()` + `_apply_keyword_patches()`
  4. `postprocess_humanization()` from `core/humanizer`
  5. `_verify_customization()` (existing)

- [ ] **Update `customize_cv()`** to accept `humanize: bool = True` parameter. When `True`, after Pass 1, call `_humanize_cv()`. When `False`, return Pass 1 output directly (current behavior).

- [ ] **Commit:** `feat: implement full humanization pipeline in customize_cv`

---

## Task 5: Per-Pass Model Configuration

**Depends on:** T01 (MultiModelLLMClient must exist)

This task is largely already done in Step 1.5. The remaining work:

### Step 5.1: Ensure settings.json has cv_models config

- [ ] **Verify `configs/settings.json`** has the `cv_models` section with optimize, humanize, and keyword_audit entries (should already be there from Step 1.5).

- [ ] **Verify `core/settings.py`** has `CVModelConfig` dataclass and `cv_models` field with default values (should already be there from Step 1.5).

- [ ] **Test:** Run `python -c "from core.settings import load_settings; s = load_settings(); print(s.cv_models)"` and confirm it prints the correct config.

- [ ] **Commit:** `feat: verify per-pass model configuration in settings`

---

## Task 6: Frontend Humanization UI

**Depends on:** T03 (backend pipeline must be complete)

### Step 6.1: Add humanize parameter to backend API

- [ ] **Update `api/schemas.py`** — add `humanize: bool = True` to `CVCustomizeRequest`

- [ ] **Update `api/routes/api_cv.py`** — pass `humanize` to `cv_service.customize_cv()`

- [ ] **Commit:** `feat: add humanize parameter to CV customization API`

### Step 6.2: Update frontend API client and hook

- [ ] **Update `frontend/src/api/cv.ts`** — add `humanize` param to `customizeCV()`

- [ ] **Update `frontend/src/hooks/use-cv.ts`** — pass `humanize` through

- [ ] **Commit:** `feat: add humanize param to frontend API client`

### Step 6.3: Add toggle and badge to customize-cv-dialog

- [ ] **Update `frontend/src/components/customize-cv-dialog.tsx`**
  - Add `humanize` state (default `true`)
  - Add Switch component labeled "AI-tell protection" with InfoCircledIcon tooltip
  - Add "Humanized" Badge when humanization was applied
  - Add warning count Badge when `warnings.length > 0`
  - Pass `humanize` to `customizeCV()` API call

- [ ] **Commit:** `feat: add humanization toggle and badges to CV dialog`

---

## Task 7: Integration Tests

**Depends on:** T01, T03, T04 (all backend code complete)

### Step 7.1: Write pipeline integration tests

- [ ] **Create `tests/test_humanization_pipeline.py`**

Test the full `customize_cv()` flow with mocked LLM providers:
- `test_customize_cv_with_humanization` — mock all LLM calls, verify golden path
- `test_customize_cv_without_humanization` — `humanize=False` returns Pass 1 only
- `test_humanize_false_skips_passes_2_through_5`
- `test_verification_catches_fabrication_after_humanization`
- `test_cached_result_bypasses_pipeline`
- `test_force_regenerate_reruns_pipeline`

- [ ] **Run:** `pytest tests/test_humanization_pipeline.py -v`

- [ ] **Commit:** `test: add humanization pipeline integration tests`

### Step 7.2: Run full test suite and verify

- [ ] **Run:** `pytest --tb=short`

- [ ] **Fix any failures**

- [ ] **Commit:** `test: all tests passing for v1.4.1`

---

## Final Verification

- [ ] `pytest` — all tests pass
- [ ] `python db/migrate.py` — migrations up to date
- [ ] `python main.py` — server starts without errors
- [ ] Manual test: upload CV, customize for a job, verify humanization toggle works
- [ ] Update `VERSION` file to `1.4.1`
- [ ] **Final commit:** `chore: bump version to 1.4.1`
