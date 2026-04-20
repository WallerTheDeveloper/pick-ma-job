# H5: Add Rate Limiting to POST /api/run and Bulk Mutation Endpoints

- **Phase:** High
- **Priority:** P1 — Abuse Prevention
- **Status:** DONE
- **Depends on:** None

## Problem

`@limiter.limit(...)` is only applied to `/auth/magic-link`. All other mutating endpoints — including `POST /api/run`, which triggers expensive Apify scraping + Claude API calls — are unprotected.

While `RunActiveError` prevents two *concurrent* runs, completed runs evict after 1 hour, meaning an authenticated user can trigger ~60 runs/hour without restriction. Bulk-delete and bulk-update endpoints also have no per-user limits.

## Solution

1. **`api/routes/api_pipeline.py`** — add rate limit to the run endpoint:
   ```python
   @router.post("/run")
   @limiter.limit("5/hour")
   async def api_start_run(request: Request, ...):
   ```

2. **`api/routes/api_results.py`** — add rate limit to bulk mutation endpoints:
   ```python
   @router.patch("/results/bulk")
   @limiter.limit("60/minute")
   async def bulk_update(...):
   ```

3. Ensure `request: Request` is present as a parameter on each decorated route (slowapi requires it for IP extraction).

4. Review all other POST/PATCH/DELETE routes for appropriate limits.

## Files

- `api/routes/api_pipeline.py`
- `api/routes/api_results.py`
- `api/routes/api_lists.py` (review)
- `api/routes/api_search_config.py` (review)

## Acceptance Criteria

- [ ] `POST /api/run` is limited to a reasonable per-user/per-IP rate (e.g. 5/hour)
- [ ] Bulk mutation endpoints have rate limits applied
- [ ] Exceeding the limit returns HTTP 429 with a clear error message
- [ ] Normal usage is not impacted by the limits
