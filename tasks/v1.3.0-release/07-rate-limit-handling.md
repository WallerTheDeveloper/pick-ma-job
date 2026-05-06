# Task 07: Rate Limit Handling

## Goal

Fix 429 rate limit errors from the Anthropic API. The current retry logic with exponential backoff (2^attempt, max 3 retries) is insufficient when running 8+ concurrent evaluations. Both the 50,000 input tokens per minute and 50 requests per minute limits are being exceeded.

## Current Behavior

### Error Logs (from user report)
```
Evaluation failed for 'Talent Manager Intership': LLMError: Anthropic API error 429: Error code: 429 -
{'type': 'rate_limit_error', 'message': "This request would exceed your organization's rate limit of
50,000 input tokens per minute (org: 9e054454-4731-4d41-bbdb-b5d18ed44f84, model: claude-haiku-4-5-20251001)."}
```

Multiple jobs failed with the same 429 error, both for token limits and request limits.

### Current Retry Logic

**File**: `core/llm_client.py` `_call_api()` (lines 69–123):
- `default_max_retries=3` — tries 3 times total
- Exponential backoff: `wait = 2 ** attempt` → 1s, 2s, 4s
- Retries on status codes: `{429, 503, 529}`
- Does NOT read `Retry-After` headers from the response
- Does NOT distinguish between rate limit types (tokens/min vs requests/min)

### Current Concurrency

**File**: `services/pipeline.py`:
- `asyncio.Semaphore(8)` for evaluation concurrency (from `settings.json` `evaluation_concurrency: 8`)
- Each evaluation makes 2 API calls (Pass 1 + Pass 2 for high-score jobs)
- With 50 jobs and concurrency of 8: up to 8 simultaneous API calls, each making 1-2 requests

### Rate Limit Math
- Anthropic limit: 50 requests/min, 50,000 input tokens/min
- Pass 1 (score): ~500–1000 input tokens per call
- Pass 2 (full eval): ~2000–4000 input tokens per call
- With concurrency=8 and 50 jobs: ~100 API calls total, burst of 8 at a time
- 8 concurrent calls * ~2000 avg tokens = ~16,000 tokens in one burst
- At 1s backoff, after a 429 we retry after 1-4s — the rate limit window is 60s, so we immediately hit it again

## Required Changes

### 1. Reduce Concurrency

**File**: `configs/settings.json`

Change `evaluation_concurrency` from 8 to 3:

```json
{
  "evaluation_concurrency": 3
}
```

With concurrency of 3:
- Max 3 simultaneous API calls
- Max ~12,000 tokens in a burst (well under 50,000/min)
- Max 3 requests at a time (well under 50/min)
- This alone may fix most rate limit issues

### 2. Enhance Retry Logic with Rate-Limit-Aware Backoff

**File**: `core/llm_client.py`

Update `_call_api()` to handle 429s properly:

```python
async def _call_api(
    self,
    *,
    system: str,
    user: str,
    model: str | None = None,
    max_tokens: int = 1024,
) -> LLMResponse:
    model_name = model or self.default_model
    max_retries = self.default_max_retries
    
    for attempt in range(max_retries):
        try:
            t0 = time.monotonic()
            response = await self.client.messages.create(
                model=model_name,
                max_tokens=max_tokens,
                temperature=0,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
            duration_ms = int((time.monotonic() - t0) * 1000)
            return LLMResponse(...)
        except anthropic.APIStatusError as exc:
            if exc.status_code == 429 and attempt < max_retries - 1:
                # Parse Retry-After header or default to 60s for rate limits
                retry_after = self._parse_retry_after(exc)
                wait = max(retry_after, 60) if attempt >= 2 else retry_after
                logger.warning(
                    "Rate limit hit (429), attempt %d/%d, waiting %ds",
                    attempt + 1, max_retries, wait,
                )
                await asyncio.sleep(wait)
            elif exc.status_code in RETRYABLE_STATUS_CODES and attempt < max_retries - 1:
                wait = 2 ** attempt
                logger.warning(...)
                await asyncio.sleep(wait)
            else:
                raise LLMError(...)

def _parse_retry_after(self, exc: anthropic.APIStatusError) -> float:
    """Extract Retry-After seconds from response headers, with fallback."""
    try:
        headers = exc.response.headers
        retry_after = headers.get("retry-after") or headers.get("Retry-After")
        if retry_after:
            return float(retry_after)
    except Exception:
        pass
    # Default backoff: exponential with jitter, capped at 60s
    return min(2 ** self._current_attempt + 0.5, 60)
```

Key improvements:
- For 429 errors: use `Retry-After` header if available, otherwise wait 60s (the rate limit window)
- For 503/529 errors: keep exponential backoff (1s, 2s, 4s)
- Increase default max retries from 3 to 6 (more patience for rate limits)
- Cap total wait time to prevent indefinite blocking

### 3. Update LLMClient Constructor

**File**: `core/llm_client.py`

Change `default_max_retries` from 3 to 6:

```python
@dataclass(frozen=True)
class LLMClient:
    client: anthropic.AsyncAnthropic
    default_model: str
    default_max_retries: int = 6  # Changed from 3
```

### 4. Add Rate Limit Tracking

**File**: `services/pipeline.py`

Track rate limit events per pipeline run:

```python
@dataclass(frozen=True)
class PipelineStats:
    # ... existing fields ...
    rate_limit_hits: int = 0  # NEW
    rate_limit_wait_seconds: float = 0.0  # NEW
```

Update `_evaluate_and_store()` to catch and track rate limit errors:
- Increment `rate_limit_hits` counter
- Add `rate_limit_wait_seconds` from the wait time
- Log rate limit events with job title for debugging

### 5. Add Token Usage Logging

**File**: `services/pipeline.py`

Track total tokens used per run:

```python
@dataclass(frozen=True)
class PipelineStats:
    # ... existing fields ...
    total_input_tokens: int = 0  # NEW
    total_output_tokens: int = 0  # NEW
```

Accumulate from `LLMResponse` metadata returned by evaluator calls.

### 6. Update Run Manager Stats

**File**: `services/run_manager.py`

Include rate limit stats in the run result:

```python
result = {
    # ... existing stats ...
    "rate_limit_hits": stats.rate_limit_hits,
    "rate_limit_wait_seconds": stats.rate_limit_wait_seconds,
    "total_input_tokens": stats.total_input_tokens,
    "total_output_tokens": stats.total_output_tokens,
}
```

### 7. Frontend — Display Rate Limit Stats

**File**: `frontend/src/components/run-status.tsx` or `frontend/src/pages/dashboard.tsx`

Show rate limit stats in the run completion summary:
- "Rate limit hits: X" (only shown if > 0)
- "Token usage: X input, Y output"
- This helps users understand if their run was affected by rate limits

## Anti-Pattern: Infinite Retry

**Do NOT add infinite retry.** After max retries (6), the evaluation should fail gracefully:
- The job is stored with `evaluation=NULL` and `score=NULL`
- The error is logged in `PipelineStats.errors`
- The user can manually re-evaluate the failed job using the on-demand evaluation (Task 01)
- This prevents burning credits on a stuck pipeline

## Files to Modify

| File | Change |
|------|--------|
| `configs/settings.json` | Reduce `evaluation_concurrency` from 8 to 3 |
| `core/llm_client.py` | Enhance retry logic: parse Retry-After, 60s backoff for 429, increase max retries to 6 |
| `services/pipeline.py` | Add rate limit tracking to `PipelineStats`; accumulate token usage |
| `services/run_manager.py` | Include rate limit stats in run result |
| `frontend/src/components/run-status.tsx` or dashboard | Display rate limit stats |
| `frontend/src/types/schemas.ts` | Add rate limit stats to run result type |

## Acceptance Criteria

- [ ] `evaluation_concurrency` reduced to 3 in `settings.json`
- [ ] `default_max_retries` increased to 6 in `LLMClient`
- [ ] 429 errors trigger a 60-second wait (or `Retry-After` header value) before retry
- [ ] 503/529 errors still use exponential backoff (1s, 2s, 4s)
- [ ] Rate limit events are logged with job title, attempt number, and wait duration
- [ ] `PipelineStats` includes `rate_limit_hits`, `rate_limit_wait_seconds`, token usage counts
- [ ] Run result in dashboard shows rate limit stats (when > 0)
- [ ] After max retries, jobs fail gracefully (stored without evaluation, not retried forever)
- [ ] Pipeline completes successfully with 50+ jobs without 429 errors

## Testing

- Run a pipeline with 50+ jobs and verify no 429 errors occur
- If possible, temporarily set `evaluation_concurrency` back to 8 to verify the retry logic handles rate limits
- Check logs for rate limit warnings and verify wait times are appropriate

## Dependencies

- **Depends on**: None (independent fix — should be prioritized since it's blocking real pipeline runs)
- **Blocks**: None
- **Related to**: Task 01 (On-Demand Evaluation) — same `LLMClient` is used, but the rate limit fix benefits both pipeline and on-demand evaluation
