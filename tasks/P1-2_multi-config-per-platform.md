# P1-2: Allow Multiple Search Configs Per Platform

- **Phase:** 1 — Critical Bugs
- **Priority:** P0 — Blocking
- **Status:** TODO
- **Depends on:** None

## Problem

Users cannot add two search configs for the same platform with different queries. The DB has a `UNIQUE (user_id, platform)` constraint and the repository uses `ON CONFLICT ... DO UPDATE`, so a second config silently overwrites the first.

## Changes Required

### Database Migration

- Drop `UNIQUE (user_id, platform)` constraint on `search_configs`
- Keep the `id` UUID primary key (already exists)

### Backend — `repositories/search_config.py`

- Replace `upsert()` with `create()` — plain `INSERT ... RETURNING`, no `ON CONFLICT`
- Remove `find_by_user_and_platform()` or keep as a convenience (returns list, not single row)

### Backend — `services/pipeline.py`

- `run_pipeline()` with `platform` filter: change from `find_by_user_and_platform` (returns 1) to a query that returns all configs for that platform
- Iterate over all matching configs in `_run_platform()`

### Backend — `api/routes/api_search_config.py`

- POST endpoint: call `create()` instead of `upsert()`
- No other route changes needed (GET list + DELETE by id already work)

### Frontend

- No changes needed — the add form already sends a create request

## Files

- DB migration SQL (new file)
- `repositories/search_config.py`
- `services/pipeline.py`
- `api/routes/api_search_config.py`

## Acceptance Criteria

- [ ] User can create multiple configs for the same platform
- [ ] Each config has a different query/filters
- [ ] Pipeline runs all configs for a platform, not just one
- [ ] Deleting one config does not affect others
