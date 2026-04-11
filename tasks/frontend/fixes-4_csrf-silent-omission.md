# FE-4: CSRF Token Silently Omitted on State-Changing Requests

- **Phase:** fixes
- **Priority:** P2 (High)
- **Status:** DONE
- **Depends on:** None

## Problem

In `src/api/client.ts:45-49`, when `getCsrfToken()` returns `undefined` (cookie not yet set or expired), the CSRF header is silently omitted. The backend returns 403, and the user sees an opaque error with no indication that the CSRF token is missing.

## Approach

Add a development-mode warning when a state-changing request (POST/PUT/PATCH/DELETE) has no CSRF token:

```ts
if (["POST", "PUT", "PATCH", "DELETE"].includes(method)) {
  const csrf = getCsrfToken();
  if (csrf) {
    headers["X-CSRF-Token"] = csrf;
  } else if (import.meta.env.DEV) {
    console.warn(`[API] CSRF token missing for ${method} ${path}. Request will likely fail with 403.`);
  }
}
```

Optionally, in production, throw a specific error type so the UI can show "Session expired, please refresh" instead of a generic 403.

## Files

- `frontend/src/api/client.ts:45–49` — add CSRF-missing warning/error

## Implementation Notes

- Do NOT block the request in all cases — the `/auth/magic-link` POST legitimately runs before the CSRF cookie exists.
- Consider adding a whitelist of paths that are exempt from CSRF (e.g., magic link request).
