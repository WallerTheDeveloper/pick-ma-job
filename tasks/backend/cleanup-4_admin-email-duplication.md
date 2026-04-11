# CR-16: ADMIN_EMAIL Lookup Duplicated Across 3 Files

- **Phase:** cleanup
- **Priority:** P4 (Low)
- **Status:** DONE
- **Depends on:** security-6_admin-email-timing-attack

## Problem

`os.environ.get("ADMIN_EMAIL")` is duplicated in three files:
- `api/routes/api_dashboard.py:29`
- `api/routes/auth.py:35`
- `api/deps.py:97`

The `get_admin_user` dependency in `api/deps.py:93-100` already centralizes the admin check, but the other two files perform their own inline checks instead of reusing it. This means the admin email comparison logic (including the `hmac.compare_digest` fix from security-6) must be maintained in three places.

## Approach

1. Add an `is_admin_email` helper in `api/deps.py`:
   ```python
   def is_admin_email(email: str) -> bool:
       admin_email = os.environ.get("ADMIN_EMAIL", "").strip()
       return bool(admin_email and hmac.compare_digest(email, admin_email))
   ```
2. Replace inline checks in `api_dashboard.py:29-30` and `auth.py:35-36` with calls to `is_admin_email(user.email)`.
3. Update `get_admin_user` in `deps.py` to use the same helper internally.

## Files

- `api/deps.py:93-100` — add `is_admin_email` helper, refactor `get_admin_user` to use it
- `api/routes/api_dashboard.py:29-30` — replace inline check with `is_admin_email`
- `api/routes/auth.py:35-36` — replace inline check with `is_admin_email`

## Implementation Notes

- This task depends on security-6 being done first, so the `hmac.compare_digest` fix is already in place and only needs to live in one location.
- After consolidation, any future admin email check only needs to call `is_admin_email()`.
