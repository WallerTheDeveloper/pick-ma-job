# P2-5: Clear Irrelevant / Old Jobs

- **Phase:** 2 — UX Polish
- **Priority:** P1 — High
- **Status:** DONE
- **Depends on:** None

## Problem

No way to bulk-clear old or irrelevant job results. Users accumulate stale results over time.

## Changes Required

### Backend — `repositories/job_result.py`

- Add `bulk_update_status(user_id, filters, new_status)` method
- Accepts optional filters: `older_than` (datetime), `status` (current status to match), `platform`, `max_score`

### Backend — `api/routes/api_results.py`

- Add `POST /api/results/bulk-dismiss` endpoint
- Request body: `{ older_than_days?: number, status?: string, platform?: string, max_score?: number }`
- Sets matching results to status `dismissed`

### Frontend — `frontend/src/pages/results.tsx`

- Add "Dismiss All Filtered" button next to "Clear filters" button
- Only visible when there are results displayed
- Confirmation dialog before executing
- Invalidate results query on success

### Frontend — `frontend/src/hooks/use-results.ts`

- Add `bulkDismiss` mutation

## Open Question

Should "clear" permanently delete or just set status to `dismissed`? (Defaulting to dismiss — reversible and safer.)

## Acceptance Criteria

- [x] User can dismiss all currently-filtered results in one action
- [x] Confirmation dialog prevents accidental bulk dismissal
- [x] Results list refreshes after bulk dismiss
- [x] Dismissed results can be found by filtering for "Dismissed" status
