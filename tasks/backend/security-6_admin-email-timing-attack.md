# CR-7: Admin Email Compared with != Instead of hmac.compare_digest

- **Phase:** security
- **Priority:** P2 (High)
- **Status:** DONE
- **Depends on:** None

## Problem

In three locations, the admin email is compared using plain `==`/`!=` operators:
- `api/deps.py:98` — `user.email != admin_email`
- `api/routes/auth.py:36` — `user.email == admin_email`
- `api/routes/api_dashboard.py:30` — `user.email == admin_email`

The project convention in CLAUDE.md explicitly requires `hmac.compare_digest()` for all secret/token comparisons to prevent timing attacks. While email comparison is lower risk than token comparison, it still leaks information about which characters match.

## Approach

1. Replace all three plain comparisons with `hmac.compare_digest(user.email, admin_email)`.
2. Note: `hmac.compare_digest` requires both arguments to be the same type (both `str` or both `bytes`). Ensure `admin_email` is never `None` — use `os.environ.get("ADMIN_EMAIL", "").strip()`.

## Files

- `api/deps.py:98` — replace `user.email != admin_email` with `not hmac.compare_digest(user.email, admin_email)`
- `api/routes/auth.py:36` — replace `user.email == admin_email` with `hmac.compare_digest(user.email, admin_email)`
- `api/routes/api_dashboard.py:30` — replace `user.email == admin_email` with `hmac.compare_digest(user.email, admin_email)`

## Implementation Notes

- This task is a prerequisite for cleanup-4 (admin email duplication consolidation). Fix here first, then consolidate.
- Add `import hmac` to any file that doesn't already have it.
