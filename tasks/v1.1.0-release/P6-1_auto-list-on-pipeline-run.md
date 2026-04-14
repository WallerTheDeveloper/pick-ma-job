# P6-1: Auto-Create Job List on Pipeline Completion

- **Phase:** 6 — Pipeline Enhancement
- **Priority:** P2 — Enhancement
- **Status:** DONE
- **Depends on:** None (job_lists infrastructure already exists)

## Problem

When a pipeline run finishes, newly scraped jobs are mixed into the full results list. With many existing results it is easy to lose track of what was just scraped. Users need a way to immediately see only the jobs from the latest run.

## Solution

At the end of each pipeline run, automatically create a `job_list` named `{platform}-{YYYY-MM-DD-HH:MM}` (using the run's start time) and add all newly inserted job results to it. The existing lists page surfaces this list immediately.

## Scope

### Backend

1. **`repositories/job_list.py`** — verify or add `add_items(list_id: UUID, job_result_ids: list[UUID]) -> None` using bulk insert:
   ```sql
   INSERT INTO job_list_items (list_id, job_result_id)
   SELECT $1, unnest($2::uuid[])
   ON CONFLICT DO NOTHING
   ```
2. **`services/pipeline.py`** — after the scrape + evaluate + insert loop for each platform:
   - Collect the list of newly inserted `job_result.id` values from the insert loop.
   - Skip list creation if zero new jobs were inserted (no dedup survivors).
   - Compute list name: `f"{platform}-{run_started_at.strftime('%Y-%m-%d-%H:%M')}"`.
   - Call `JobListRepository.create(user_id, name)` then `add_items(list_id, new_ids)`.
   - Wrap in `try/except Exception` — log the error but never let list-creation failure abort the pipeline run.
   - If a single run covers multiple platforms, create one list per platform.

### Frontend

No changes required. The existing lists page and `use-lists` hook will surface the new list automatically. Optionally, a toast on run-complete can link to the new list — track as a follow-up.

## Files

- `repositories/job_list.py`
- `services/pipeline.py`

## Acceptance Criteria

- [x] A completed run with N new jobs creates a list named `{platform}-{YYYY-MM-DD-HH:MM}`
- [x] The list contains exactly the newly inserted jobs from that run
- [x] A run that produces zero new jobs (all duplicates) does not create a list
- [x] A multi-platform run creates one list per platform
- [x] List-creation failure is logged but does not fail or abort the pipeline run
- [x] The new list appears on the lists page without any additional user action
