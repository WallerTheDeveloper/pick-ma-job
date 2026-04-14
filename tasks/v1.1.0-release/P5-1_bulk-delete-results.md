# P5-1: Bulk Delete Job Results

- **Phase:** 5 — Results UX
- **Priority:** P2 — Enhancement
- **Status:** DONE
- **Depends on:** P4-1 (search field; bulk delete must respect active filters for "select all")

## Problem

Users can delete all filtered results or delete one row at a time. There is no way to select a subset of rows and delete only those. This makes cleaning up results tedious.

## Scope

### Backend

1. **`repositories/job_result.py`** — add `delete_many(user_id, ids: list[UUID]) -> int` using:
   ```sql
   DELETE FROM job_results
   WHERE user_id = $1 AND id = ANY($2::uuid[])
   RETURNING id
   ```
   Returns the count of deleted rows. Scoped by `user_id` to prevent cross-user deletion.
2. **`api/schemas.py`** — add `BulkDeleteRequest(ids: list[UUID])` with `max_length=500` to prevent oversized payloads.
3. **`api/routes/api_results.py`** — add `POST /api/results/bulk-delete`, CSRF-protected. Returns `{ "deleted": n }`. Returns 422 if `ids` is empty or exceeds 500.

### Frontend

4. **`frontend/src/api/results.ts`** — add `bulkDeleteResults(ids: string[])` calling `POST /api/results/bulk-delete`.
5. **`frontend/src/hooks/use-results.ts`** — add `useBulkDeleteResults` mutation with results query invalidation on success.
6. **`frontend/src/pages/results.tsx`** — add multi-select UI:
   - Checkbox on each job row bound to `selectedIds: Set<string>` state.
   - Header checkbox to select/deselect all currently visible (filtered) rows.
   - Sticky action bar visible when `selectedIds.size > 0`, showing "Delete N selected" button.
   - Confirm dialog before executing the bulk delete.
   - Clear `selectedIds` after successful deletion.

## Files

- `repositories/job_result.py`
- `api/schemas.py`
- `api/routes/api_results.py`
- `frontend/src/api/results.ts`
- `frontend/src/hooks/use-results.ts`
- `frontend/src/pages/results.tsx`

## Acceptance Criteria

- [ ] `POST /api/results/bulk-delete` deletes only rows owned by the current user
- [ ] Payload of more than 500 ids returns 422
- [ ] Each job row has a checkbox
- [ ] Header checkbox selects/deselects all visible rows
- [ ] Action bar appears when at least one row is selected
- [ ] Confirm dialog is shown before deletion executes
- [ ] After deletion the results list refreshes and selection is cleared
- [ ] "Select all" respects the active search and filter state (only selects visible rows)
