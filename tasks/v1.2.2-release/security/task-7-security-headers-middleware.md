# Task 7 — Add HTTP Security Headers Middleware

**Size:** XS  
**Status:** done  
**Severity:** MEDIUM

## Goal

The FastAPI app returns no security headers. Add a middleware that emits the baseline set on every response.

## Changes

**`main.py`** — register middleware after app creation:
```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: StarletteRequest, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"  # modern browsers ignore; disables legacy IE mode
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

app.add_middleware(SecurityHeadersMiddleware)
```

## Notes

- `X-XSS-Protection: 0` is intentional — the legacy header is disabled in favour of CSP; setting it to `1` can introduce vulnerabilities in old IE.
- A full `Content-Security-Policy` is out of scope here (requires frontend audit); that can be added in a follow-up task.

## Success Criteria

- All API responses include `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and `Permissions-Policy` headers.
