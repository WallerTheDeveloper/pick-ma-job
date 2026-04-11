# P4-2: Delete Job Row

- **Phase:** 4 — Features
- **Priority:** P2 — Medium
- **Status:** DONE
- **Depends on:** None

## Problem

Users cannot delete individual job results from the results table. Once a job is evaluated and stored, it persists with no way to remove it — even if it was mis-scraped, duplicate, or simply unwanted.

## Scope

### Backend

Add a `DELETE /api/results/{id}` endpoint:
- Verify the job belongs to the authenticated user before deleting
- Hard delete the row from `job_results`
- Return 204 No Content on success, 404 if not found, 403 if not the owner

### Frontend

- Add a delete button/icon to each row in the results table
- Show a confirmation prompt before deleting (to prevent accidental removal)
- Remove the row from the UI immediately on success (optimistic update via TanStack Query)

## Files

- `api/routes/api_results.py` — add `DELETE /api/results/{id}` route
- `api/schemas.py` — no new schema needed (204 response)
- `repositories/job_result.py` — add `delete_by_id(user_id, job_result_id)` method
- `frontend/src/api/results.ts` — add `deleteResult(id)` API call
- `frontend/src/hooks/use-results.ts` — add `useDeleteResult` mutation hook
- `frontend/src/pages/results.tsx` — add delete button + confirmation to each row

## Acceptance Criteria

- [x] Each job row has a visible delete action (button or icon)
- [x] Clicking delete shows a confirmation prompt
- [x] Confirming removes the row from the UI and deletes it from the database
- [x] A user cannot delete another user's job results (403 check)
- [x] Deleting a job that belongs to a list also removes it from any `job_list_items` rows (cascade delete via FK)
