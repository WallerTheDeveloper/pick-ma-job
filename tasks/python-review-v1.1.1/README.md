# Python Review Tasks — v1.1.1

Tasks derived from a full manual Python code review of the pick-ma-job backend (April 2026).

**Verdict:** BLOCK — 3 Critical, 8 High, 3 Medium issues found.

---

## Critical (fix before any deploy)

| Task | File | Issue |
|------|------|-------|
| [C1](C1_task-gc-fire-and-forget.md) | `services/run_manager.py:113` | Fire-and-forget asyncio tasks — can be GC'd before completion |
| [C2](C2_magic-link-token-in-logs.md) | `services/auth.py:74` | Magic link auth token logged in plaintext at INFO level |
| [C3](C3_dynamic-sql-interpolation.md) | `repositories/job_result.py:228+` | Dynamic SQL column interpolation — structurally unsafe pattern |

## High (fix soon)

| Task | File | Issue |
|------|------|-------|
| [H1](H1_retry-backoff-claude-api.md) | `core/evaluator.py:138` | No retry/backoff on Claude API calls |
| [H2](H2_retry-backoff-apify.md) | `scrapers/upwork.py:55`, `scrapers/linkedin.py:140` | No retry/backoff on Apify actor calls |
| [H3](H3_search-config-list-none-check.md) | `services/search_config.py:36` + `api/routes/api_pipeline.py:59` | `get_by_platform` returns list; `is None` guard is unreachable |
| [H4](H4_blocking-resend-email.md) | `services/auth.py:116` | Synchronous `resend.Emails.send` blocks the event loop |
| [H5](H5_rate-limit-pipeline-endpoint.md) | `api/routes/api_pipeline.py` | No rate limiting on `POST /api/run` |
| [H6](H6_empty-profile-mutable-singleton.md) | `services/profile.py:33` | `_EMPTY_PROFILE` singleton with mutable list fields |
| [H7](H7_pipeline-exception-logging.md) | `services/pipeline.py:222` | `except Exception` without `exc_info=True` — stack traces lost |
| [H8](H8_auth-error-wrong-http-status.md) | `api/routes/auth.py:69` | Invalid email returns HTTP 429 instead of 422 |

## Medium (clean up when time allows)

| Task | File | Issue |
|------|------|-------|
| [M1](M1_settings-json-cached-read.md) | `services/pipeline.py:84` | `settings.json` re-read from disk on every pipeline run |
| [M2](M2_hardcoded-version-fastapi.md) | `main.py:128` | Hardcoded `version="0.3.0"` diverges from VERSION file |
| [M3](M3_misc-code-quality.md) | Various | Batched small quality fixes (imports, type hints, shared helpers) |
