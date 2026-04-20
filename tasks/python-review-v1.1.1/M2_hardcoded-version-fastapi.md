# M2: Remove Hardcoded version="0.3.0" from FastAPI Constructor

- **Phase:** Medium
- **Priority:** P2 — Consistency
- **Status:** DONE
- **Depends on:** None

## Problem

`main.py:128` hardcodes `FastAPI(version="0.3.0", ...)`. The actual version served by `/api/version` is read from a `VERSION` file via `_read_version()` and stored in `app.state.version`.

When the `VERSION` file is bumped, the FastAPI OpenAPI schema (shown in `/docs`) still reports `0.3.0`. The two version sources diverge silently.

## Solution

**`main.py`** — read the version before constructing the `FastAPI` instance and pass it in:

```python
def create_app() -> FastAPI:
    version = _read_version()
    app = FastAPI(title="pick-ma-job", version=version, lifespan=lifespan)
    app.state.version = version  # keep for /api/version route
    ...
```

Remove the redundant `_read_version()` call from inside `lifespan` if it is now called in `create_app`.

## Files

- `main.py`

## Acceptance Criteria

- [x] `FastAPI(version=...)` uses the value read from the `VERSION` file
- [x] `/docs` OpenAPI schema version matches `/api/version` response
- [x] Bumping the `VERSION` file updates both without any code change
