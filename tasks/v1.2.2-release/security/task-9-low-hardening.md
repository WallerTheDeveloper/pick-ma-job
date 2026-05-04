# Task 9 — Low-Severity Hardening (CORS, Docs, Logging, Cookies)

**Size:** S  
**Status:** done  
**Severity:** LOW

## Goal

Bundle the remaining low-severity findings into one cleanup pass.

## Changes

### L-1 & L-2 — Restrict CORS methods and headers (`main.py`)
```python
CORSMiddleware,
allow_origins=...,
allow_credentials=True,
allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
allow_headers=["Content-Type", "X-CSRF-Token"],
```

### L-3 — Redact email PII in logs
**`repositories/user.py`** and **`services/auth.py`** — replace full email with domain-only in log statements:
```python
domain = email.split("@")[-1] if "@" in email else "?"
logger.info("Created user domain=%s id=%s", domain, row["id"])
```

### L-4 — Disable Swagger docs in production (`main.py`)
```python
is_local = os.environ.get("BASE_URL", "").startswith("http://localhost")
app = FastAPI(
    ...
    docs_url="/docs" if is_local else None,
    redoc_url="/redoc" if is_local else None,
    openapi_url="/openapi.json" if is_local else None,
)
```

### L-5 — Bind dev server to localhost only (`main.py`)
```python
if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
```

### L-6 — Upgrade CSRF cookie to `SameSite=Strict` (`api/routes/auth.py`)
The `session_token` cookie must remain `Lax` (magic link redirect arrives cross-site from email). The `csrf_token` cookie has no such constraint:
```python
# csrf_token cookie only
response.set_cookie(
    "csrf_token",
    ...,
    samesite="strict",
    ...
)
```

## Success Criteria

- CORS preflight rejects requests with unlisted methods or headers.
- `/docs` and `/redoc` return 404 when `BASE_URL` is not localhost.
- Log lines no longer contain full email addresses.
- `csrf_token` cookie carries `SameSite=Strict`.
- Dev server (`__main__`) binds to `127.0.0.1`.
