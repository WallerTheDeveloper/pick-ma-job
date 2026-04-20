# H3: Fix Unreachable Guard in get_by_platform — list vs None Check

- **Phase:** High
- **Priority:** P1 — Logic Bug
- **Status:** DONE
- **Depends on:** None

## Problem

`services/search_config.py:36–38` — `get_by_platform` returns `list[SearchConfigRow]`.

`api/routes/api_pipeline.py:59–64` — the route checks `if config is None:` after calling this method.

A `list` is **never** `None`, so the guard condition is always `False`. A user with no search config for a platform passes the guard silently, and the pipeline run launches — then fails with a confusing `PipelineError` deeper in the stack instead of a clear HTTP 400.

## Solution

**Option A (minimal fix):** Change the guard to use truthiness:
```python
config = await search_config_svc.get_by_platform(user.id, platform)
if not config:
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"No search config found for platform '{platform}'. Please configure it first.",
    )
```

**Option B (cleaner, preferred):** Change `SearchConfigService.get_by_platform` to return `SearchConfigRow | None` (single config, `LIMIT 1`):
```python
async def get_by_platform(self, user_id: UUID, platform: str) -> SearchConfigRow | None:
    results = await self._repo.get_by_platform(user_id, platform)
    return results[0] if results else None
```
Then the `is None` check in the route becomes correct and the type annotation is honest.

## Files

- `api/routes/api_pipeline.py`
- `services/search_config.py` (if Option B)
- `repositories/search_config.py` (if Option B — verify LIMIT 1 semantics)

## Acceptance Criteria

- [ ] A `POST /api/run` request for a platform with no configured search config returns HTTP 400 with a clear error message
- [ ] The guard condition is reachable and tested
- [ ] Type annotations for `get_by_platform` accurately reflect the return type
