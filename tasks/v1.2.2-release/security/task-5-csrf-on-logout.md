# Task 5 — Add CSRF Protection to Logout Route

**Size:** XS  
**Status:** done  
**Severity:** MEDIUM

## Goal

`POST /auth/logout` modifies session state but does not require a CSRF token. A cross-origin form POST can force-logout any logged-in user.

## Changes

**`api/routes/auth.py`** — add `require_csrf` dependency to the logout handler:
```python
@router.post("/logout")
async def logout(
    request: Request,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
    _csrf: Annotated[None, Depends(require_csrf)],
) -> JSONResponse:
    ...
```

## Success Criteria

- `POST /auth/logout` without a valid `X-CSRF-Token` header returns `403`.
- Logout from the frontend (which includes the CSRF token) continues to work.
