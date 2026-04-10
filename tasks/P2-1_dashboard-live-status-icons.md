# P2-1: Dashboard Live Run Status with Icons

- **Phase:** 2 — UX Polish
- **Priority:** P1 — High
- **Status:** TODO
- **Depends on:** P1-1 (pipeline must work)

## Problem

Dashboard shows text "pending"/"completed" status. User must reload the tab to see the status change after pipeline finishes.

## Changes Required

### `frontend/src/components/run-status.tsx`

- Replace `<Badge>` text labels with icons:
  - **pending/running:** `<Loader2 className="animate-spin" />` (lucide-react)
  - **completed:** `<CheckCircle2 />` with green color
  - **failed:** `<XCircle />` with red/destructive color
- Add a subtle pulse animation on the running state card

### `frontend/src/pages/dashboard.tsx`

- Replace the text `{run.status}` in the recent runs list with the same icon set
- When a run completes, invalidate the `dashboard` query to refresh stats and recent runs list without manual reload

### `frontend/src/hooks/use-run.ts`

- Add `onSettled` callback to `statusQuery` that invalidates `["dashboard"]` when status becomes `completed` or `failed`
- Verify polling interval (currently 2000ms) works correctly

## Acceptance Criteria

- [ ] Running pipeline shows animated spinner icon
- [ ] Completed pipeline shows green checkmark icon (no reload needed)
- [ ] Failed pipeline shows red X icon
- [ ] Recent runs list updates automatically when a run finishes
- [ ] Dashboard stats (config count, recent runs count) refresh after run completes
