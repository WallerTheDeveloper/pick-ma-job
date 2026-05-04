# Task 13 — Unified DomainError Base + FastAPI Exception Handler

**Size:** S  
**Status:** done  
**Priority:** LOW

## Goal

Replace the per-service exception classes (`PipelineError`, `CVError`, `CompanyBlacklistError`) with a common `DomainError` base and a single FastAPI exception handler, eliminating the per-route try/except mapping boilerplate.

## Problem

Each service defines its own exception; each route must catch and map to HTTP status. Adding a new service means adding a new exception class and new catch blocks in routes.

## Changes

**`core/exceptions.py`** — new file
```python
class DomainError(Exception):
    def __init__(self, message: str, http_status: int = 400):
        super().__init__(message)
        self.http_status = http_status

class NotFoundError(DomainError):
    def __init__(self, message: str):
        super().__init__(message, http_status=404)

class ConflictError(DomainError):
    def __init__(self, message: str):
        super().__init__(message, http_status=409)
```

**`main.py`**
```python
@app.exception_handler(DomainError)
async def domain_error_handler(request, exc: DomainError):
    return JSONResponse(status_code=exc.http_status, content={"detail": str(exc)})
```

**Services** — replace existing exception classes:
- `PipelineError` → `DomainError` (or `ConflictError` for active-run-exists)
- `CVError` → `DomainError`
- `CompanyBlacklistError` → `DomainError` / `NotFoundError`

**Routes** — remove individual `except PipelineError`, `except CVError` blocks

## Success Criteria

- `grep -r "except.*Error" api/routes/` returns no domain-error catches (only unexpected-exception catches)
- All existing error HTTP status codes are preserved
- New services can raise `DomainError(message, http_status=422)` without touching any route file
