# Task 9 — Extract Auto-List Creation to AutoListService

**Size:** S  
**Status:** done  
**Priority:** MEDIUM

## Goal

Move the post-pipeline job-list creation out of `_run_platform` into a dedicated `services/auto_list_service.py`. Currently it's a cross-cutting concern mixed into scraping/eval logic, and duplicate runs on the same day can produce name collisions.

## Problem

In `services/pipeline.py → _run_platform`:
- Creates a job list named `<platform>-<date>` mid-platform-loop
- If a user runs the pipeline twice in a day: duplicate name → DB constraint failure logged as generic warning
- Post-processing logic is coupled to scraping/eval orchestration

## Changes

**`services/auto_list_service.py`** — new file
```python
class AutoListService:
    def __init__(self, job_list_repo: JobListRepo): ...

    async def create_for_run(
        self,
        user_id: UUID,
        run_id: UUID,
        job_result_ids: list[UUID],
        platform: str,
    ) -> UUID | None:
        # Idempotent: upsert list by (user_id, run_id, platform)
        # Name: f"{platform}-{date}-{run_id[:8]}" to guarantee uniqueness
```

**`services/pipeline.py`**
- Remove auto-list creation from `_run_platform`
- After all platforms complete in `run_pipeline`, call `auto_list_service.create_for_run(...)` per platform with the collected job result IDs

**`api/deps.py`**
- Provide `AutoListService` via `Depends()`

## Success Criteria

- Running the pipeline twice in one day creates two distinct lists with no DB errors
- `_run_platform` contains no job-list creation logic
- `AutoListService` is independently testable (mock `JobListRepo`)
