# Task 4 — UX Feature: Bulk Status Marking

**Size:** M  
**Status:** done

## Problem

Users must change result row statuses one by one. There is no way to select multiple rows and update them all at once.

## Desired Behaviour

User selects multiple rows → clicks "Mark as…" → picks a status → all selected rows update in one action.

## UX Design

Add a "Mark as…" dropdown to the **existing floating selection bar** (already appears when rows are selected in `results.tsx:427-471`).

Bar layout:
```
[ N selected ]  [ Mark as…  ▼ ]  [ Delete N selected ]  [ Clear selection ]
```

- Dropdown options: **New**, **Applied**, **Dismissed**.
- On select: fire bulk-update request → show toast `"Marked N jobs as Applied"` → clear `selectedIds` on success.
- **No confirmation dialog** — status changes are reversible.
- Works in both all-results and custom list views (uses the shared `selectedIds` Set).
- No "Mark all filtered as…" variant in this release.

## Files to Change

### Backend
- `api/routes/api_results.py`
  - Add `POST /api/results/bulk-status` accepting `{ids: UUID[], status: "new"|"applied"|"dismissed"}`.
  - Validate status against `VALID_STATUSES`; validate ids are non-empty.
  - Rate-limit consistent with existing bulk endpoints.
- `api/schemas.py`
  - Add `BulkStatusUpdateRequest`, `BulkStatusUpdateResponse` Pydantic models.
- `repositories/job_result.py`
  - Add `update_status_many(user_id: UUID, ids: list[UUID], new_status: str) -> int`.
  - Use a single `UPDATE ... WHERE id = ANY($1) AND user_id = $2` for atomicity (scoped to user for safety).

### Frontend
- `frontend/src/api/results.ts`
  - Add `bulkUpdateStatus(ids: string[], status: string): Promise<...>` wrapper.
- `frontend/src/hooks/use-results.ts`
  - Add `bulkUpdateStatusByIds` mutation; on success invalidate `RESULTS_KEY` and `"lists"` query keys.
- `frontend/src/pages/results.tsx:427-471`
  - Add "Mark as…" `DropdownMenu` to the floating selection bar.
  - Wire to the new mutation.
  - Clear `selectedIds` on success.
  - Show toast with count.

## Success Criteria

- Select 3 rows → Mark as Applied → all 3 badges flip to "Applied".
- Works inside a custom list and on all-results.
- Toast confirms how many rows were updated.
- Selection clears on success.
- Rows owned by other users are never affected (server enforces `user_id` scope).
