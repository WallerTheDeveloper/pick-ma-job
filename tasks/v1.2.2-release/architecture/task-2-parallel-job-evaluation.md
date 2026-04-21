# Task 2 — Parallel Job Evaluation with Semaphore

**Size:** M  
**Status:** todo  
**Priority:** HIGH

## Goal

Evaluate jobs concurrently instead of serially. Currently `services/pipeline.py` awaits Pass 1 + Pass 2 + DB insert per job sequentially. For 100 jobs at ~1-2s each this is 2-4 minutes of wall time; the Claude API and Apify both support concurrent requests.

## Problem

In `services/pipeline.py → _run_platform`:
```python
for job in jobs_to_evaluate:
    result = await self._evaluator.evaluate(...)   # serial
    await self._job_result_repo.insert(...)         # serial
```

## Changes

**`services/pipeline.py`**
- Add `_concurrency: int` to `PipelineService.__init__`, read from settings (default `8`)
- Extract inner loop body to `async def _evaluate_and_store(job, semaphore) -> JobResult`
- Replace serial loop with:
  ```python
  semaphore = asyncio.Semaphore(self._concurrency)
  tasks = [self._evaluate_and_store(job, semaphore) for job in jobs_to_evaluate]
  results = await asyncio.gather(*tasks, return_exceptions=True)
  ```
- Handle exceptions per-job in results (log and count as `jobs_failed`, don't abort the whole platform)

**`configs/settings.json`**
- Add `"evaluation_concurrency": 8`

**`services/pipeline.py`** — dedup and blacklist checks stay serial (they are now a single batch query after Task 3)

## Success Criteria

- A pipeline run with 50 jobs completes in under 30s (not 50-100s)
- A single job evaluation failure does not abort the rest of the platform batch
- `evaluation_concurrency` in settings controls the semaphore size
- `jobs_failed` counter in the run result captures per-job errors
