# Task 3 — Bug: Filters Broken in Custom List View

**Size:** M  
**Status:** done

## Problem

Filters (status, platform, min score, sort) do nothing when viewing a custom list. Only keyword search works. All filters work correctly on the "All Results" page.

## Root Cause

`frontend/src/pages/results.tsx:97` — when `selectedListId !== null` the component switches to `useListJobs(listId)`, which calls `GET /api/lists/{id}/jobs` with no filter query params. The hook returns all jobs in the list unfiltered. Only `searchTerm` (client-side) is applied afterward, which is why keyword lookup works but nothing else does.

## Files to Change

### Backend
- `api/routes/api_lists.py`
  - Add `status`, `min_score`, `platform`, `sort` query params to `GET /api/lists/{id}/jobs`.
  - Validate `status` against `VALID_STATUSES`; validate `sort` against allowed sort values.
  - Pass params through to the repository.
- `repositories/job_list.py`
  - Extend `find_jobs_in_list` to accept filter kwargs (`status`, `min_score`, `platform`, `sort`).
  - Build WHERE clause mirroring the filter logic in `JobResultRepository.find_by_user`.

### Frontend
- `frontend/src/api/lists.ts`
  - Extend `fetchJobsInList(listId)` to accept an optional filter params object; serialize as query string.
- `frontend/src/hooks/use-lists.ts`
  - `useListJobs` accepts a filter object and includes it in the TanStack Query key (so filter changes trigger a refetch).
- `frontend/src/pages/results.tsx`
  - When `selectedListId !== null`, pass the current filters (status, minScore, platform, sort) into `useListJobs`.
  - Keep `searchTerm` and `dateRange` as client-side filters on both code paths (already working).

## Design Decisions

- **Sort default in list view:** `score_desc` (same as all-results for consistency).
- **Pagination in list view:** skip for v1.2.0 — lists rarely exceed 50 items.

## Success Criteria

- Selecting status, platform, min-score, or sort filter in a custom list view correctly filters the visible rows.
- Keyword search continues to work.
- Behaviour in list view is identical to all-results for all filter types.
