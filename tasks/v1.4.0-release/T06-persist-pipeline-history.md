# T06 - Persist Pipeline Run History on Dashboard

## Priority
Medium

## Status
.Done

## Description
When the user navigates away from the Dashboard and returns, or refreshes the page, the pipeline run status card disappears. The "Recent Runs" section also disappears when a run is active. This task ensures run history is always visible and run details can be re-inspected by clicking on past runs.

## Context
- `frontend/src/pages/dashboard.tsx` — the main Dashboard component.
- `frontend/src/hooks/use-run.ts` — the `useRun` hook that manages run state. `activeRunId` is stored in React state and lost on navigation/refresh.
- `frontend/src/components/run-status.tsx` — renders the detailed run status card.
- The `seedRunId` logic (line 51-54) rehydrates from `latestRun` only when status is "running" or "pending".
- Line 183 hides Recent Runs when `displayedRun` exists: `{data.recent_runs.length > 0 && !displayedRun && (`
- The `useRun(initialRunId)` hook seeds from `initialRunId` but doesn't persist across navigation.

## Acceptance Criteria
- [ ] "Recent Runs" section is always visible regardless of whether a run is active
- [ ] Clicking on a past run card in "Recent Runs" shows its `RunStatus` details
- [ ] Active run status card is automatically rehydrated from sessionStorage on page reload
- [ ] On run completion/failure, the `run_id` is cleared from sessionStorage
- [ ] User can select any run in the history to view its details (not just the latest active one)
- [ ] Run cards in history have cursor-pointer and hover state indicating clickability

## Implementation Notes

### Frontend changes

1. **Modify `frontend/src/pages/dashboard.tsx`**:

   a. Add state for tracking the selected run:
   ```tsx
   const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
   ```

   b. Replace the `seedRunId` logic with sessionStorage-based persistence:
   ```tsx
   // On mount, check sessionStorage for a recent active run
   useEffect(() => {
     const storedRunId = sessionStorage.getItem("activeRunId");
     if (storedRunId && activeRunId === null) {
       setActiveRunId(storedRunId);
     }
   }, []);

   // When startRun succeeds, store the run_id in sessionStorage
   const startMutation = useMutation({
     mutationFn: (args?: StartRunArgs | void) => startRun(args ?? undefined),
     onSuccess: (data) => {
       setActiveRunId(data.run_id);
       sessionStorage.setItem("activeRunId", data.run_id);
     },
   });
   ```

   c. Add logic to clear sessionStorage on terminal states:
   ```tsx
   useEffect(() => {
     if (runStatus?.status === "completed" || runStatus?.status === "failed") {
       sessionStorage.removeItem("activeRunId");
     }
   }, [runStatus?.status]);
   ```

   d. Make Recent Runs list always visible (remove `!displayedRun` condition):
   Change line 183 from:
   ```tsx
   {data.recent_runs.length > 0 && !displayedRun && (
   ```
   to:
   ```tsx
   {data.recent_runs.length > 0 && (
   ```

   e. Add click handler to run cards:
   ```tsx
   {data.recent_runs.map((run) => (
     <Card
       key={run.id}
       className="p-3 shadow-sm cursor-pointer hover:shadow-md transition-shadow"
       onClick={() => setSelectedRunId(run.id)}
     >
       ...
     </Card>
   ))}
   ```

   f. Use `selectedRunId` (falling back to the auto-seeded `activeRunId`) for displaying `RunStatus`:
   ```tsx
   const displayedRunId = selectedRunId ?? (activeRunId ?? seedRunId ?? undefined);
   ```
   Then pass `displayedRunId` to `useRunStatus` or `useRun`.

2. **Modify `frontend/src/hooks/use-run.ts`**:

   a. Update `useRun` to accept `initialRunId` properly and expose `setActiveRunId` if needed (it already does via `clearRun` pattern).
   
   b. In `useRunStatus`, also include "cancelled" status in terminal state check (for T11):
   ```tsx
   if (status === "completed" || status === "failed" || status === "cancelled") return false;
   ```

3. **Ensure `RunStatus` component** accepts any `RunStatusResponse` and renders it, not just active runs. This should already work since it just displays the data.

## Dependencies
- T11 (Stop Pipeline Button) adds the "cancelled" status, which should be included in terminal state checks

## Files to Modify/Create
- `frontend/src/pages/dashboard.tsx` (modify — add selectedRunId state, sessionStorage persistence, always-show history, clickable run cards)
- `frontend/src/hooks/use-run.ts` (modify — sessionStorage integration)

## Tests
- Start a pipeline run, navigate to Results, navigate back to Dashboard → run status card should reappear
- Refresh the page during an active run → run status card should reappear via sessionStorage
- After run completes, refresh → no stale run_id in sessionStorage
- Click a past "completed" run card → RunStatus shows that run's details
- Recent Runs section is visible even when an active run is in progress