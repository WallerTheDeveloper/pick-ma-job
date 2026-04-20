# Task 5 — Wire blacklist filter into PipelineService

**Size:** M  
**Status:** done

## Goal

Integrate the company blacklist as a pre-evaluation filter in `services/pipeline.py`. The evaluator must NOT be called for blacklisted jobs (cost-saving guarantee).

## Changes

### `services/pipeline.py`

1. **Constructor** — add `company_blacklist_repo: CompanyBlacklistRepository` parameter; store as `self._company_blacklist_repo`.

2. **`PlatformResult` dataclass** — add `jobs_skipped_blacklist: int = 0`.

3. **`PipelineRunResult` dataclass** — add `jobs_skipped_blacklist: int = 0`.

4. **`_run_platform`** — load blacklist once per platform run (not per job):
   ```python
   blacklist = await self._company_blacklist_repo.find_names_by_user_id(user_id)
   ```
   Then in the per-job loop, after dedup check and before keyword filter:
   ```python
   if self._is_blacklisted(job, blacklist):
       jobs_skipped_blacklist += 1
       continue
   ```

5. **Add helper method:**
   ```python
   def _is_blacklisted(self, job: NormalizedJob, blacklist: tuple[str, ...]) -> bool:
       if not blacklist:
           return False
       company = job.company_name
       if not company:
           return False
       company_lower = company.lower()
       return any(entry in company_lower for entry in blacklist)
   ```

6. **Aggregation** — sum `jobs_skipped_blacklist` from all platform results into `PipelineRunResult`.

7. **Logging** — include `jobs_skipped_blacklist` in the final run summary log line.

### `api/deps.py`

Update `get_pipeline_service` to instantiate and pass `CompanyBlacklistRepository`.

## Success Criteria

- `_is_blacklisted` returns `True` for "Google DeepMind" when blacklist contains `"google"`.
- `_is_blacklisted` returns `False` when `job.company_name` is `None`.
- `_is_blacklisted` returns `False` when blacklist is empty (no DB call overhead on empty list).
- Evaluator mock is NOT called for a blacklisted job in unit tests.
- `PipelineRunResult.jobs_skipped_blacklist` is correctly aggregated.
- Existing keyword-filter and dedup behavior unchanged.
