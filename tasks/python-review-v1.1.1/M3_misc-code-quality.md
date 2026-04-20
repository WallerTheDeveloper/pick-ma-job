# M3: Miscellaneous Code Quality Fixes

- **Phase:** Medium
- **Priority:** P2 — Code Quality
- **Status:** DONE
- **Depends on:** None

## Problem

Several smaller code quality issues identified during the review that are worth batching into a single cleanup pass:

### 1. `__import__("json")` in db/pool.py codec lambdas
**`db/pool.py:17–25`** — `__import__("json")` is called inside codec lambdas that run on every JSONB query. `json` is stdlib and has no circular import risk here.

**Fix:** Replace with a top-level import:
```python
import json
# ...
encoder=json.dumps,
decoder=json.loads,
```

### 2. Split `dataclasses` import in run_manager.py
**`services/run_manager.py:19, 26`** — `dataclasses` is imported twice on separate lines:
```python
from dataclasses import dataclass, replace
...
from dataclasses import asdict
```

**Fix:** Consolidate to one line:
```python
from dataclasses import asdict, dataclass, replace
```

### 3. LinkedIn scraper constants defined inside method body
**`scrapers/linkedin.py:75, 94`** — `_EXPERIENCE_LEVEL_MAP` and `_VALID_JOB_TYPES` are defined inside `_fetch_jobs_sync`, re-allocated on every scrape call.

**Fix:** Move to module-level constants.

### 4. Cursor decoder bare `except Exception`
**`api/routes/api_results.py:53–61`** — `_decode_cursor` uses `except Exception` to validate the cursor.

**Fix:** Catch only expected exceptions:
```python
except (ValueError, KeyError, binascii.Error, json.JSONDecodeError):
```

### 5. `pool: object` annotation in admin/dashboard routes
**`api/routes/api_admin.py:21`**, **`api/routes/api_dashboard.py:25`** — pool is annotated as `object`, losing type safety.

**Fix:**
```python
import asyncpg
pool: Annotated[asyncpg.Pool, Depends(get_db_pool)]
```

### 6. Duplicate `_get` / `_str_or_none` helpers in scrapers
**`scrapers/upwork.py:130–132`**, **`scrapers/linkedin.py:237–239`** — identical helper functions defined in both files.

**Fix:** Move to `scrapers/base.py` or a new `scrapers/_utils.py` and import from there.

## Files

- `db/pool.py`
- `services/run_manager.py`
- `scrapers/linkedin.py`
- `api/routes/api_results.py`
- `api/routes/api_admin.py`
- `api/routes/api_dashboard.py`
- `scrapers/upwork.py`
- `scrapers/base.py` (or new `scrapers/_utils.py`)

## Acceptance Criteria

- [x] `json` imported at module level in `db/pool.py`
- [x] Single `from dataclasses import asdict, dataclass, replace` line in `run_manager.py`
- [x] LinkedIn scraper constants at module level
- [x] `_decode_cursor` catches specific exception types
- [x] `pool` parameter typed as `asyncpg.Pool` in admin and dashboard routes
- [x] Duplicated scraper helpers extracted to a shared location
