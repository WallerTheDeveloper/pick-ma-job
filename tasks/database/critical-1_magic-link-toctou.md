# DB-1: Magic Link Verification Is Not Atomic — TOCTOU Race Condition

- **Phase:** critical
- **Priority:** P1 (Critical)
- **Status:** DONE
- **Depends on:** None

## Problem

`verify_magic_link` in `services/auth.py:86–109` performs three separate database calls: `find_by_token` (read), check `link.used` in Python, then `mark_used` (write). Two concurrent requests with the same token can both pass the `used` check before either marks it used, creating two valid sessions from a single magic link. This is a classic TOCTOU race condition.

## Approach

1. Add a new `MagicLinkRepository.claim(token: str) -> MagicLinkRow | None` method that performs a single atomic UPDATE:
   ```sql
   UPDATE magic_links
   SET used = TRUE
   WHERE token = $1 AND used = FALSE AND expires_at > now()
   RETURNING id, user_id, token, used, expires_at, created_at
   ```
   If no row is returned, the token was invalid, expired, or already used — all three cases collapse into one non-raceable operation.
2. Refactor `AuthService.verify_magic_link` to call `claim(token)` instead of the three-step sequence.
3. Remove `find_by_token` from the auth hot path (keep if needed elsewhere, otherwise remove).

## Files

- `repositories/magic_link.py:85–91` — add new `claim(token)` method
- `services/auth.py:86–109` — replace three-step sequence with single `claim()` call
- `repositories/magic_link.py:44–68` — evaluate whether `find_by_token` is still needed

## Implementation Notes

- The atomic UPDATE eliminates the race window — PostgreSQL row-level locking ensures only one transaction can claim a given token.
- Error messages should remain generic ("Invalid or expired login link") to avoid leaking whether a token existed, was already used, or expired.
- Add a test simulating concurrent verification of the same token using `asyncio.gather` to confirm only one succeeds.
