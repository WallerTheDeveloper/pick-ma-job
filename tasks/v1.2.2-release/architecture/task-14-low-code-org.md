# Task 14 — Low-Impact Code Organisation Improvements

**Size:** S  
**Status:** done  
**Priority:** LOW

## Goal

Three small housekeeping changes: centralise router registration, cache platform config reads, and type the `extras` dict on `NormalizedJob`. Each is independent and can be done separately.

## Sub-tasks

### 14a — Centralise router registration (L1)

**`api/routes/__init__.py`**
```python
from .auth import router as auth_router
from .jobs import router as jobs_router
# ... all routers

all_routers = [auth_router, jobs_router, ...]
```

**`main.py`**
```python
from api.routes import all_routers
for router in all_routers:
    app.include_router(router)
```

### 14b — Cache platform config reads (L2)

In `services/pipeline.py` or wherever `configs/platforms/<platform>.json` is read per-run:
- Add `@functools.lru_cache(maxsize=None)` to the config loader (same pattern as `load_platform_context` already uses)
- Verify the file is only read once across multiple runs in the same process

### 14c — Type the NormalizedJob extras dict (L3)

**`scrapers/base.py`**

Option A (preferred): Promote common fields to first-class `NormalizedJob` attributes:
```python
@dataclass(frozen=True)
class NormalizedJob:
    ...
    company_name: str | None = None
    location: str | None = None
```

Option B: Define a `TypedDict` for each platform's extras and annotate `extras: UpworkJobExtras | LinkedInJobExtras | dict[str, Any]`

A misspelling in `extras["company_name"]` currently silently breaks blacklist filtering.

### 14d — Split api/schemas.py by domain (L4)

When `api/schemas.py` exceeds 400 lines, split into:
- `api/schemas/auth.py`
- `api/schemas/jobs.py`
- `api/schemas/profile.py`
- `api/schemas/runs.py`
- `api/schemas/__init__.py` — re-exports all for backward compat

## Success Criteria

- `main.py` contains no `include_router` calls (delegated to `api/routes/__init__.py`)
- Platform config JSON is read from disk exactly once per process lifetime (verifiable with a log statement or mock)
- `NormalizedJob.company_name` is a typed field; blacklist filter does not access `extras` dict for company name
