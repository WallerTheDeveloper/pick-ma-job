# CR-5: resend.api_key Is a Module-Level Mutable Global

- **Phase:** security
- **Priority:** P2 (High)
- **Status:** DONE
- **Depends on:** None

## Problem

In `services/auth.py:46`, `resend.api_key = resend_api_key` overwrites a module-level global attribute on every `AuthService` instantiation. Since `AuthService` is created per-request via FastAPI `Depends()`, concurrent async requests cause a race condition on the shared `resend.api_key` global. If the value ever differs between requests (e.g., hot-reload or multi-tenant), this is a data leak vector.

## Approach

1. Check if the `resend` library supports a client instance pattern (e.g., `resend.Client(api_key=...)`). If so, instantiate one client per `AuthService` and use it for sending.
2. If the library only supports the global pattern, move the `resend.api_key = ...` assignment to app startup (in `main.py` lifespan) instead of per-request. Remove it from `AuthService.__init__`.
3. Either way, `AuthService.__init__` should not mutate the global.

## Files

- `services/auth.py:46` — remove `resend.api_key = resend_api_key` from `__init__`
- `main.py` (lifespan function) — set `resend.api_key` once at startup, OR
- `services/auth.py` — use `resend.Client(api_key=...)` instance if supported

## Implementation Notes

- Check `resend` library docs for client instantiation. As of resend-python 0.7+, the library supports `resend.Emails.send()` with the global key. Newer versions may support a `Resend(api_key=...)` client.
- The key principle: per-request mutation of module-level state violates the project's "no module-level mutable state" convention from CLAUDE.md.
