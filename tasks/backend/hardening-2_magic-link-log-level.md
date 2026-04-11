# CR-9: Magic Link URL Logged in Plaintext at INFO Level

- **Phase:** hardening
- **Priority:** P3 (Medium)
- **Status:** DONE
- **Depends on:** None

## Problem

In `services/auth.py:77`, when `SKIP_EMAIL=true`, the full magic link URL (including the secret token) is logged at INFO level. In production-level logging configurations that capture INFO, this token is exposed in log files, log aggregators, or monitoring dashboards.

## Approach

1. Change the log level from `logger.info` to `logger.debug` on line 77.
2. Truncate the URL in the log message: `magic_url[:40] + "..."` to show enough for debugging without exposing the full token.
3. Best: use DEBUG level AND truncate, so even debug logs don't contain the full token.

## Files

- `services/auth.py:77` — change `logger.info` to `logger.debug` and truncate the URL

## Implementation Notes

- `SKIP_EMAIL=true` should only be used in development. However, log levels can be misconfigured, and defense-in-depth applies.
- The token is 32 bytes of `secrets.token_urlsafe`, so truncating at 40 characters removes the sensitive portion while keeping the base URL visible.
