# FE-14: ProtectedRoute Redirects to / Instead of /login on Auth Error

- **Phase:** improvements
- **Priority:** P3 (Medium)
- **Status:** TODO
- **Depends on:** None

## Problem

In `src/components/protected-route.tsx:17`, when `!isAuthenticated || error`, the user is redirected to `/` (the landing page). This means a network error on `GET /auth/me` (timeout, 500) redirects an authenticated user to the landing page, losing their context. It also conflates "not logged in" with "auth check failed."

## Approach

1. Change the redirect target to `/login`.
2. Optionally distinguish between network errors and auth failures:
   - If the error is a network error or 5xx, show a retry UI instead of redirecting.
   - If the error is a 401/403, redirect to `/login`.

## Files

- `frontend/src/components/protected-route.tsx:17` — change redirect from `/` to `/login`

## Implementation Notes

- Verify that `/login` route exists and handles the unauthenticated state correctly.
- Consider passing the current URL as a `?next=` query param so the user can be redirected back after login.
