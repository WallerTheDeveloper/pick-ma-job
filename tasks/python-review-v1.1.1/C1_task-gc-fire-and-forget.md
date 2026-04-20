# C1: Fix Fire-and-Forget asyncio Tasks in RunManager

- **Phase:** Critical
- **Priority:** P0 — Data Loss Risk
- **Status:** DONE
- **Depends on:** None

## Problem

`services/run_manager.py:113–114` uses `asyncio.create_task(...)` without storing the returned `Task` objects. Python's garbage collector can destroy tasks that have no strong references before they finish. This means the entire pipeline run (`_execute`) or the DB persist (`_persist_insert`) can silently vanish under memory pressure — no error, no log, just a missing run.

The CPython docs explicitly warn against this pattern.

## Solution

1. **`services/run_manager.py`** — add a `_active_tasks: set[asyncio.Task]` set to `__init__`:
   ```python
   self._active_tasks: set[asyncio.Task] = set()
   ```

2. For every `asyncio.create_task(...)` call, store the reference and register a done-callback that removes it:
   ```python
   task = asyncio.create_task(self._execute(run_id, user_id, pool, platforms))
   self._active_tasks.add(task)
   task.add_done_callback(self._active_tasks.discard)
   ```

3. Apply the same fix to `_persist_insert` task creation.

## Files

- `services/run_manager.py`

## Acceptance Criteria

- [ ] `RunManager.__init__` initialises `self._active_tasks: set[asyncio.Task]`
- [ ] Both `create_task` calls store the task reference in `_active_tasks`
- [ ] A done-callback removes completed tasks from the set (no memory leak)
- [ ] A pipeline run triggered via `POST /api/run` completes reliably under concurrent load
