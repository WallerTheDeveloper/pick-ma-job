# Task 1 — Stateless RunManager (DB as Source of Truth)

**Size:** L  
**Status:** todo  
**Priority:** HIGH

## Goal

Replace the in-memory `RunManager` dict with the existing `pipeline_runs` DB table as the authoritative state store. Currently any restart/deploy silently orphans in-flight runs (row stays `running` forever), and horizontal scaling is impossible because `asyncio.Task` handles and the `_runs` dict exist only in one process.

## Problem

`services/run_manager.py` stores `self._runs: dict[UUID, PipelineRunSnapshot]` in memory:
- Restart kills in-flight runs; DB row stays stuck at `running`
- `_has_active_run` check fails behind a load balancer (each replica has its own dict)
- Cannot run more than one backend replica

## Changes

**`services/run_manager.py`**
- Remove `self._runs` dict and `self._tasks` dict
- On startup (lifespan): reconcile any `running` rows older than N minutes → `failed` (configurable, default 30 min)
- `start_run`: insert `PENDING` row, dispatch `asyncio.create_task`, update row to `RUNNING`
- `_has_active_run`: query DB for `status IN ('pending', 'running')` for this `user_id` instead of checking dict
- `get_run_status`: query DB row directly
- `_update_run`: call existing `_persist_status` (already writes to DB) — remove in-memory snapshot updates

**`db/migrations/`** — new migration:
- Add `started_at TIMESTAMPTZ` and `finished_at TIMESTAMPTZ` columns to `pipeline_runs` if not already present
- Add index on `(user_id, status)` for the active-run check query

**`main.py` lifespan**
- Call `run_manager.reconcile_stale_runs()` on startup after pool is ready

## Success Criteria

- Restarting the backend while a run is in progress marks the run `failed` on next startup (not stuck at `running`)
- `GET /api/run/{run_id}` returns correct status after backend restart
- Two simultaneous `POST /api/run` requests for the same user return 409 (only one active run allowed), checked via DB not memory
- No `self._runs` or `self._tasks` attributes on `RunManager`
