# CR-8: Raw Exception Messages Returned to Client from Pipeline Runs

- **Phase:** hardening
- **Priority:** P3 (Medium)
- **Status:** DONE
- **Depends on:** None

## Problem

In `services/run_manager.py:167-174`, `str(exc)` from any uncaught exception (asyncpg, Apify SDK, Anthropic SDK) is stored in the run status and returned to the frontend. This may leak connection strings, table names, internal file paths, or API error details to end users.

## Approach

1. Log the full exception with traceback server-side (already done on line 163 with `exc_info=True`).
2. Replace `str(exc)` in the `error=` field (lines 168, 174) with a generic message: `"An internal error occurred. Please try again."`.
3. Optionally, classify known exception types to provide slightly more helpful messages (e.g., "Scraping service unavailable" for Apify errors, "Evaluation service error" for Anthropic errors) without leaking internals.

## Files

- `services/run_manager.py:162-174` — replace `str(exc)` with sanitized message in both update calls

## Implementation Notes

- The full exception is already logged at ERROR level on line 163. No information is lost.
- For debugging, consider storing the full error in a separate field not exposed to the API, or include a correlation ID that maps to the server log entry.
