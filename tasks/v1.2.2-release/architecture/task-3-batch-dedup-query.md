# Task 3 — Batch Dedup Query (Eliminate N+1)

**Size:** S  
**Status:** done  
**Priority:** HIGH

## Goal

Replace the per-job `exists(user_id, platform, job_id)` dedup check with a single batch query. Currently 100 scraped jobs trigger 100 round trips before any evaluation begins.

## Problem

In `services/pipeline.py`:
```python
for job in scraped_jobs:
    if await self._job_result_repo.exists(user_id, platform, job.id):
        ...  # skip
```

## Changes

**`repositories/job_result_repo.py`**
- Add method:
  ```python
  async def find_existing_ids(
      self, user_id: UUID, platform: str, job_ids: list[str]
  ) -> set[str]:
      # SELECT external_id FROM job_results
      # WHERE user_id=$1 AND platform=$2 AND external_id = ANY($3)
  ```

**`services/pipeline.py → _run_platform`**
- Replace the per-job `exists` call:
  ```python
  existing_ids = await self._job_result_repo.find_existing_ids(
      user_id, platform, [j.id for j in scraped_jobs]
  )
  new_jobs = [j for j in scraped_jobs if j.id not in existing_ids]
  ```
- Remove the old `exists` call from `job_result_repo.py` only if unused elsewhere

## Success Criteria

- A pipeline run with 100 scraped jobs issues exactly 1 dedup query (verifiable via DB query log or test mock)
- `jobs_skipped_duplicate` count is unchanged vs the old per-job approach
- No regression in dedup correctness
