# Task 4 — Extract Unified LLM Client

**Size:** M  
**Status:** todo  
**Priority:** HIGH

## Goal

Extract a shared `LLMClient` wrapper used by both `Evaluator` and `CVService`. Currently the two services duplicate JSON-fence stripping, have inconsistent retry logic (`CVService` has zero retry — a 529 hard-fails the user's CV request), and both hardcode `anthropic.AsyncAnthropic`.

## Problem

- `core/evaluator.py`: has `_with_retry`, `_parse_response` (strips fences)
- `services/cv_service.py`: has `_parse_json_response` (strips fences), **no retry**
- Adding a third LLM-backed service means duplicating the pattern again

## Changes

**`core/llm_client.py`** — new file
```python
@dataclass(frozen=True)
class LLMClient:
    client: AsyncAnthropic
    default_model: str
    default_max_retries: int = 3

    async def generate_json(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> dict: ...   # retries on 429/529, strips fences, raises LLMError on failure

    async def generate_text(
        self,
        *,
        system: str,
        user: str,
        model: str | None = None,
        max_tokens: int = 1024,
    ) -> str: ...    # same retry/error contract
```

- Shared retry logic (backoff on 429/529 only — same codes as current `_with_retry`)
- Shared JSON-fence stripping
- Raises a single `LLMError(message, retryable)` exception type

**`core/evaluator.py`**
- Accept `LLMClient` via constructor instead of raw `AsyncAnthropic` + model string
- Remove `_with_retry` and `_parse_response` — delegate to `LLMClient`

**`services/cv_service.py`**
- Accept `LLMClient` via constructor
- Remove `_parse_json_response` — delegate to `LLMClient.generate_json`
- Retry is now automatic

**`api/deps.py`**
- Create `LLMClient` once (injected from `app.state.anthropic_client`) and provide via `Depends()`

**`main.py` lifespan**
- Create `AsyncAnthropic` once → `app.state.anthropic_client`

## Success Criteria

- `CVService` retries on Anthropic 529 (test with mock that raises 529 once then succeeds)
- `Evaluator` behavior unchanged vs current
- No duplication of fence-stripping logic across the codebase (`grep "_parse.*response"` returns only `llm_client.py`)
- `LLMClient` can be replaced with a fake in tests without patching `anthropic` directly
