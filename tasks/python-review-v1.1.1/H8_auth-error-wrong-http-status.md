# H8: Fix AuthError Mapping — Invalid Email Returns 429 Instead of 422

- **Phase:** High
- **Priority:** P1 — Incorrect API Behaviour
- **Status:** DONE
- **Depends on:** None

## Problem

`services/auth.py:55` raises `AuthError("Invalid email address.")` for a malformed email. `api/routes/auth.py:69` catches all `AuthError` instances and returns HTTP 429 (Too Many Requests).

This means a user who simply types a bad email address receives a misleading 429 response — as if they are rate-limited — rather than a 422 Unprocessable Entity.

Additionally, the route manually parses `request.json()` at line 62–63 and ignores the existing `MagicLinkRequest` Pydantic model in `schemas.py`, bypassing automatic 422 validation for malformed request bodies.

## Solution

1. **`api/routes/auth.py`** — differentiate HTTP status codes for validation vs rate-limit errors:
   ```python
   except AuthError as exc:
       # Rate-limit errors from the service map to 429;
       # validation errors (bad email format) map to 422.
       status_code = 429 if "rate" in str(exc).lower() else 422
       return JSONResponse({"ok": False, "error": str(exc)}, status_code=status_code)
   ```
   Or use distinct exception subclasses (`AuthValidationError`, `AuthRateLimitError`) for a cleaner approach.

2. **`api/routes/auth.py:62–63`** — replace manual JSON parsing with Pydantic schema:
   ```python
   async def request_magic_link(
       request: Request,
       body: MagicLinkRequest,
       auth_service: Annotated[AuthService, Depends(get_auth_service)],
   ) -> JSONResponse:
       email = body.email.strip().lower()
   ```
   This gives automatic 422 for missing/malformed `email` fields.

## Files

- `api/routes/auth.py`
- `services/auth.py` (optionally, to add exception subclasses)

## Acceptance Criteria

- [ ] A request with a malformed email returns HTTP 422, not 429
- [ ] A request that exceeds the rate limit returns HTTP 429
- [ ] A missing `email` field in the request body returns HTTP 422 automatically via Pydantic
- [ ] Error response body format is consistent across all auth error cases
