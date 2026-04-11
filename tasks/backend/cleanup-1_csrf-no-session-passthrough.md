# CR-13: require_csrf Silently Passes When No Session Cookie

- **Phase:** cleanup
- **Priority:** P4 (Low)
- **Status:** DONE
- **Depends on:** None

## Problem

In `api/csrf.py:42-46`, when no session cookie is present, `require_csrf` returns early without raising an error. The comment explains the intent: "let `get_current_user` raise 401." This is currently safe because all mutating routes also depend on `get_current_user`. However, if a future route uses `require_csrf` without `get_current_user`, CSRF protection silently does nothing.

## Approach

Two options (choose one):

1. **Document the assumption** (minimal change): Add a prominent docstring/comment explaining that `require_csrf` MUST always be paired with `get_current_user` on mutating routes.

2. **Raise HTTP 403 for mutating methods** (defensive): When no session cookie is present AND the HTTP method is POST/PUT/PATCH/DELETE, raise HTTP 403 instead of silently passing. This makes the dependency on `get_current_user` unnecessary for CSRF safety.

## Files

- `api/csrf.py:42-46` — either document the assumption or add defensive 403

## Implementation Notes

- Option 2 changes behavior: unauthenticated POST requests would get 403 (CSRF) instead of 401 (unauthenticated). This may affect error message clarity for API consumers.
- Option 1 is zero-risk and still valuable — preventing future developers from misusing the dependency.
