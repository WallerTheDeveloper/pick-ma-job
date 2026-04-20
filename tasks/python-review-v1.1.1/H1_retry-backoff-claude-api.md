# H1: Add Retry with Exponential Backoff to Claude API Calls

- **Phase:** High
- **Priority:** P1 — Reliability
- **Status:** DONE
- **Depends on:** None

## Problem

`core/evaluator.py:138–148, 163–170` calls `self._client.messages.create(...)` with no retry logic. The Anthropic API returns transient 529 (overloaded) and 503 errors. A single API failure propagates as an uncaught exception up to `_run_platform`, which logs the error and moves on — the job is **silently lost** for that run.

This violates the CLAUDE.md design convention: *"retry with exponential backoff for external API calls"*.

## Solution

1. **`core/evaluator.py`** — wrap both `_call_score` and the primary `evaluate` API call with retry logic:
   ```python
   import asyncio

   RETRYABLE_STATUS_CODES = {429, 503, 529}

   async def _with_retry(coro_fn, max_attempts: int = 3):
       for attempt in range(max_attempts):
           try:
               return await coro_fn()
           except anthropic.APIStatusError as exc:
               if exc.status_code in RETRYABLE_STATUS_CODES and attempt < max_attempts - 1:
                   await asyncio.sleep(2 ** attempt)
               else:
                   raise
   ```

2. Alternatively, install `tenacity` (already common in async FastAPI stacks) and use:
   ```python
   from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

   @retry(
       stop=stop_after_attempt(3),
       wait=wait_exponential(multiplier=1, min=1, max=8),
       retry=retry_if_exception(lambda e: isinstance(e, anthropic.APIStatusError) and e.status_code in {429, 503, 529}),
   )
   async def _call_api(...):
       ...
   ```

3. Log a warning on each retry attempt with the attempt number and status code.

## Files

- `core/evaluator.py`
- `requirements.txt` (if adding `tenacity`)

## Acceptance Criteria

- [ ] Transient 429/503/529 errors from the Anthropic API trigger up to 3 retry attempts
- [ ] Backoff delay doubles between attempts (1s → 2s → 4s)
- [ ] Each retry attempt is logged at WARNING level with attempt number and status code
- [ ] Non-retryable errors (400, 401, 403) are raised immediately without retry
- [ ] A job that fails after all retries is logged as an error (not silently dropped)
