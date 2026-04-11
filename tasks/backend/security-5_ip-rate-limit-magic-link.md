# CR-6: No IP-Level Rate Limit on /auth/magic-link

- **Phase:** security
- **Priority:** P2 (High)
- **Status:** DONE
- **Depends on:** None

## Problem

The `/auth/magic-link` endpoint (in `api/routes/auth.py:52-70`) has a per-user DB rate limit (max N requests per user within a time window). However, there is no IP-level rate limit. An attacker with many email addresses can flood the email provider (Resend), causing cost overruns and potential account suspension.

## Approach

1. Add `slowapi` as a dependency (`pip install slowapi`).
2. Configure a global rate limiter in `main.py` using `Limiter(key_func=get_remote_address)`.
3. Apply a per-IP rate limit on the `/auth/magic-link` route, e.g., `@limiter.limit("5/minute")`.
4. Add appropriate error handling for `RateLimitExceeded` (return HTTP 429).

## Files

- `requirements.txt` — add `slowapi`
- `main.py` — initialize `Limiter` and add `SlowAPIMiddleware`
- `api/routes/auth.py:52-70` — apply `@limiter.limit("5/minute")` decorator to `api_request_magic_link`

## Implementation Notes

- `slowapi` is a FastAPI-compatible wrapper around `limits`. It supports in-memory and Redis backends.
- For MVP, in-memory storage is fine. For production with multiple workers, use Redis.
- Consider also rate-limiting `/auth/verify` to prevent token brute-force (lower priority).
- The per-user DB rate limit should remain as a defense-in-depth layer.
