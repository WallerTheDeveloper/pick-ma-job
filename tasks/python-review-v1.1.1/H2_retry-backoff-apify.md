# H2: Add Retry with Exponential Backoff to Apify Actor Calls

- **Phase:** High
- **Priority:** P1 — Reliability
- **Status:** DONE
- **Depends on:** None

## Problem

`scrapers/upwork.py:55` and `scrapers/linkedin.py:140` call `client.actor(actor_id).call(...)` (synchronous Apify SDK, run in a thread executor) with no retry logic. Apify returns rate-limit and transient errors. A single Apify failure for a user results in zero jobs scraped for that run with no recovery attempt.

## Solution

1. **`scrapers/upwork.py`** and **`scrapers/linkedin.py`** — wrap the `client.actor(...).call(...)` call in a retry loop inside `_fetch_jobs_sync`:
   ```python
   import time

   MAX_ATTEMPTS = 3
   for attempt in range(MAX_ATTEMPTS):
       try:
           run = client.actor(ACTOR_ID).call(run_input=actor_input, timeout_secs=300)
           break
       except Exception as exc:
           if attempt < MAX_ATTEMPTS - 1:
               wait = 2 ** attempt
               logger.warning("Apify call failed (attempt %d/%d), retrying in %ds: %s", attempt + 1, MAX_ATTEMPTS, wait, exc)
               time.sleep(wait)
           else:
               raise
   ```

2. If `tenacity` is added as a dependency (see H1), use `@retry(...)` decorator on `_fetch_jobs_sync` for consistency.

3. Ensure the retry only applies to transient errors — if the Apify SDK raises a specific exception type for invalid inputs (e.g. bad actor config), those should not be retried.

## Files

- `scrapers/upwork.py`
- `scrapers/linkedin.py`

## Acceptance Criteria

- [ ] Transient Apify errors trigger up to 3 retry attempts with exponential backoff
- [ ] Each retry is logged at WARNING level with attempt number and error message
- [ ] A scraper that fails after all retries raises the exception (run is marked failed, not silently empty)
- [ ] Successful retries are logged at INFO level
