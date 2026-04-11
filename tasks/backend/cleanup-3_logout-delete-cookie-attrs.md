# CR-15: delete_cookie in Logout Missing Matching Attributes

- **Phase:** cleanup
- **Priority:** P4 (Low)
- **Status:** DONE
- **Depends on:** None

## Problem

In `api/routes/auth.py:122-124`, `response.delete_cookie(key=_SESSION_COOKIE)` and `response.delete_cookie(key=CSRF_COOKIE)` are called without specifying `path`, `samesite`, `httponly`, or `secure` attributes. Per the Set-Cookie spec, browsers only evict a cookie if the delete (Max-Age=0) cookie matches the original's `path` and `domain`. If the original cookies were set with specific attributes, the delete may silently fail, leaving the user apparently logged in.

## Approach

1. Find where the session and CSRF cookies are originally set in auth routes.
2. Mirror those attributes in the `delete_cookie` calls:
   ```python
   response.delete_cookie(
       key=_SESSION_COOKIE,
       path="/",
       httponly=True,
       samesite="lax",
       secure=_is_secure(),
   )
   response.delete_cookie(
       key=CSRF_COOKIE,
       path="/",
       samesite="lax",
       secure=_is_secure(),
   )
   ```

## Files

- `api/routes/auth.py:122-124` — add matching cookie attributes to both `delete_cookie` calls
- `api/routes/auth.py` (where cookies are set) — reference to find correct attribute values

## Implementation Notes

- The `httponly` attribute should NOT be set on the CSRF cookie, because the frontend reads it via `document.cookie` in `getCsrfToken`.
- Use the same `_is_secure()` helper used when setting the cookies (if it exists), or derive `secure` from `ENVIRONMENT != "development"`.
