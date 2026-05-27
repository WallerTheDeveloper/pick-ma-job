# T12 - Bulk Add to List

## Priority
Medium

## Status
.Done

## Description
Add an "Add to list" button in the floating bulk action bar on the Results page that adds all selected jobs to a chosen list. Currently the bulk actions are: Mark as…, Evaluate selected, Evaluate all, Delete selected, Clear selection.

## Context
- `frontend/src/pages/results.tsx` — the Results page with bulk selection and floating action bar.
- `frontend/src/components/add-to-list-menu.tsx` — per-row AddToListMenu component.
- `frontend/src/hooks/use-lists.ts` — hook for list operations.
- `frontend/src/api/lists.ts` — API calls for lists.
- `api/routes/api_lists.py` — backend list endpoints.
- The floating bulk action bar appears when `selectedIds.size > 0` (around line 370+ of results.tsx).
- `AddToListMenu` supports adding a single job to a list. The bulk version needs to add multiple jobs at once.

## Acceptance Criteria
- [ ] "Add to list" button appears in the floating bulk action bar when jobs are selected
- [ ] Clicking opens a dialog showing available lists
- [ ] Dialog has a "Create new list" option
- [ ] On selection, all selected jobs are added to the chosen list via API
- [ ] Success toast: "Added {count} jobs to '{list_name}'"
- [ ] After successful add, selection is cleared (`setSelectedIds(new Set())`)
- [ ] Button is disabled when `selectedIds.size === 0`
- [ ] Backend accepts an array of job IDs for adding to a list (check existing endpoint; modify if needed)

## Implementation Notes

### Backend

1. **Check `api/routes/api_lists.py`** — the existing `POST /api/lists/{list_id}/jobs` endpoint likely accepts a single `job_result_id`. Verify and update if needed.

2. **Add bulk endpoint** or modify existing:
   - Option A: Add `POST /api/lists/{list_id}/jobs/bulk` with `{ job_result_ids: UUID[] }`
   - Option B: Modify existing endpoint to accept either single or array
   - Recommended: Add a new bulk endpoint for clarity:
     ```python
     class BulkAddJobsRequest(BaseModel):
         job_result_ids: list[UUID] = Field(min_length=1, max_length=500)
     
     @router.post("/{list_id}/jobs/bulk")
     async def api_bulk_add_jobs_to_list(
         list_id: UUID,
         body: BulkAddJobsRequest,
         user: UserRow,
         list_repo: JobListRepository,
         _csrf: None = Depends(require_csrf),
     ) -> OkResponse:
         # Verify list ownership
         # Add all job_result_ids
         # Return { ok: true }
     ```

### Frontend

1. **Add bulk add API call to `frontend/src/api/lists.ts`**:
   ```typescript
   export async function bulkAddJobsToList(listId: string, jobResultIds: string[]): Promise<void> {
     await api(`/api/lists/${listId}/jobs/bulk`, {
       method: "POST",
       body: { job_result_ids: jobResultIds },
     });
   }
   ```

2. **Create `frontend/src/components/bulk-add-to-list-dialog.tsx`**:
   ```tsx
   interface BulkAddToListDialogProps {
     open: boolean;
     onOpenChange: (open: boolean) => void;
     selectedIds: Set<string>;
     onSuccess: () => void;  // Called after successful add (to clear selection)
   }
   ```
   - Use `useLists` hook to fetch available lists
   - Show a radio group or selectable list of existing lists
   - Show "Create new list" option at the bottom
   - "Add" button that calls the bulk API
   - On success: toast "Added {count} jobs to '{list_name}'", call `onSuccess()`
   - If "Create new list" is selected, show an inline input for the list name, create it, then add jobs

3. **Modify `frontend/src/pages/results.tsx`**:
   - Import `BulkAddToListDialog`
   - Add state: `const [bulkAddListOpen, setBulkAddListOpen] = useState(false)`
   - Add "Add to list" button in the floating action bar (next to existing buttons):
     ```tsx
     <Button
       variant="outline"
       size="sm"
       disabled={selectedIds.size === 0}
       onClick={() => setBulkAddListOpen(true)}
     >
       <ListPlus className="mr-1 h-4 w-4" />
       Add to list
     </Button>
     ```
   - Render the dialog:
     ```tsx
     <BulkAddToListDialog
       open={bulkAddListOpen}
       onOpenChange={setBulkAddListOpen}
       selectedIds={selectedIds}
       onSuccess={() => {
         setSelectedIds(new Set());
         queryClient.invalidateQueries({ queryKey: ["results"] });
       }}
     />
     ```

4. **Add Pydantic model in `api/schemas.py`** (if creating bulk endpoint):
   ```python
   class BulkAddJobsRequest(BaseModel):
       job_result_ids: list[UUID] = Field(min_length=1, max_length=500)
   ```

## Dependencies
- None

## Files to Modify/Create
- `api/routes/api_lists.py` (modify — add bulk endpoint)
- `api/schemas.py` (modify — add `BulkAddJobsRequest`)
- `frontend/src/api/lists.ts` (modify — add `bulkAddJobsToList`)
- `frontend/src/components/bulk-add-to-list-dialog.tsx` (new)
- `frontend/src/pages/results.tsx` (modify — add button and dialog)

## Tests
- API test: `POST /api/lists/{id}/jobs/bulk` adds multiple jobs
- API test: `POST /api/lists/{id}/jobs/bulk` returns error for non-existent list or wrong user
- Frontend: "Add to list" button disabled when no jobs selected
- Frontend: Dialog shows available lists, allows selection
- Frontend: Success toast shows correct count and list name
- Frontend: Selection cleared after successful add