# T11 - Stop Pipeline Button

## Priority
High

## Status
.Done

## Description
Add a "Stop Pipeline" button on the Dashboard that appears when a pipeline run is in progress (status: pending or running). This allows users to gracefully cancel a running pipeline, preserving already-processed jobs.

## Context
- `frontend/src/pages/dashboard.tsx` — shows Run Status card and Run Pipeline button.
- `frontend/src/hooks/use-run.ts` — `useRun` hook manages run state with `activeRunId` and `isRunning`.
- `frontend/src/components/run-status.tsx` — renders the detailed run status card with status, stats, etc.
- `services/run_manager.py` — `RunManager` dispatches background tasks and tracks status.
- `services/pipeline.py` — `PipelineService.run_pipeline()` orchestrates the full pipeline.
- Pipeline run statuses: currently `pending`, `running`, `completed`, `failed`.
- `repositories/pipeline_run.py` — tracks run status in the `pipeline_runs` table.

## Acceptance Criteria
- [ ] "Stop Pipeline" button appears on Dashboard when `isRunning` is true
- [ ] Clicking the button shows a confirmation dialog: "Are you sure you want to stop this pipeline run? Jobs already processed will be preserved."
- [ ] On confirmation, `POST /api/run/{run_id}/cancel` is called
- [ ] Backend sets a cancellation flag, pipeline gracefully stops after current evaluation
- [ ] Run status transitions to "cancelled" in the DB
- [ ] `cancelled` is a valid terminal status alongside `completed` and `failed`
- [ ] Dashboard shows "Cancelled" status icon (amber/orange color, Ban or XCircle icon)
- [ ] Frontend polling stops on "cancelled" status
- [ ] Already-processed jobs are preserved — cancellation only prevents new evaluations from starting

## Implementation Notes

### Backend

1. **DB migration `db/migrations/018_cancelled_status.sql`**:
   ```sql
   ALTER TABLE pipeline_runs DROP CONSTRAINT IF EXISTS pipeline_runs_status_check;
   ALTER TABLE pipeline_runs ADD CONSTRAINT pipeline_runs_status_check 
     CHECK (status IN ('pending', 'running', 'completed', 'failed', 'cancelled'));
   ```

2. **Modify `services/run_manager.py`**:
   - Add a `asyncio.Event`-based cancellation mechanism or a set of cancelled run IDs:
     ```python
     def __init__(self, ...):
         ...
         self._cancelled_runs: set[UUID] = set()
     ```
   - Add `cancel_run(run_id: UUID, user_id: UUID)` method:
     ```python
     async def cancel_run(self, run_id: UUID, user_id: UUID) -> None:
         """Cancel a running or pending pipeline run."""
         repo = PipelineRunRepository(self._pool)
         run = await repo.find_by_id(run_id)
         if run is None or run.user_id != user_id:
             raise NotFoundError("Run not found.")
         if run.status not in ("pending", "running"):
             raise DomainError("Run is not active.", http_status=409)
         self._cancelled_runs.add(run_id)
         await self._persist_status(run_id, user_id, status="cancelled",
             completed_at=datetime.now(timezone.utc))
     ```
   - In `_execute()`, check for cancellation between job evaluations:
     ```python
     if run_id in self._cancelled_runs:
         self._cancelled_runs.discard(run_id)
         logger.info("Run %s cancelled by user", run_id)
         return
     ```
   - The cancellation check should happen INSIDE the pipeline loop, between individual job evaluations.

3. **Modify `services/pipeline.py`** — pass a cancellation check callback:
   - Add `is_cancelled: collections.abc Callable[[], bool] | None = None` parameter to `run_pipeline()`.
   - Between platform evaluations or between job evaluations, check `if is_cancelled and is_cancelled(): return stats_so_far`.
   - The `RunManager._execute()` method provides the callback:
     ```python
     is_cancelled = lambda: run_id in self._cancelled_runs
     result = await service.run_pipeline(user_id, platforms, run_id=run_id, is_cancelled=is_cancelled)
     ```

4. **Add API endpoint in `api/routes/api_pipeline.py`**:
   ```python
   @router.post("/{run_id}/cancel")
   async def api_cancel_run(
       run_id: UUID,
       user: Annotated[UserRow, Depends(get_current_user)],
       run_manager: Annotated[RunManager, Depends(get_run_manager)],
       _csrf: Annotated[None, Depends(require_csrf)],
   ) -> OkResponse:
       await run_manager.cancel_run(run_id, user.id)
       return OkResponse()
   ```

5. **Update `api/schemas.py`** — no schema changes needed; the `RunStatusResponse.status` is already a `str` field.

### Frontend

1. **Add `POST /api/run/{run_id}/cancel` to `frontend/src/api/pipeline.ts`**:
   ```typescript
   export async function cancelRun(runId: string): Promise<OkResponse> {
     return api(`/api/run/${runId}/cancel`, { method: "POST" }, okResponseSchema);
   }
   ```

2. **Add `cancelRun` mutation to `frontend/src/hooks/use-run.ts`**:
   ```typescript
   const cancelMutation = useMutation({
     mutationFn: (runId: string) => cancelRun(runId),
     onSuccess: () => {
       queryClient.invalidateQueries({ queryKey: [RUN_STATUS_KEY] });
       queryClient.invalidateQueries({ queryKey: ["dashboard"] });
     },
   });
   ```
   Return `cancelRun: cancelMutation.mutate` from the hook.

3. **Modify `frontend/src/pages/dashboard.tsx`**:
   - Import `Ban` icon from `lucide-react`
   - Add a "Stop Pipeline" button next to the Run Pipeline area when `effectiveIsRunning`:
     ```tsx
     {effectiveIsRunning && (
       <Button
         variant="outline"
         onClick={() => setConfirmCancelOpen(true)}
         disabled={cancelMutation.isPending}
       >
         <Ban className="mr-2 h-4 w-4" />
         Cancel Run
       </Button>
     )}
     ```
   - Add `AlertDialog` for cancellation confirmation (similar pattern to the delete confirmation in result-row.tsx).

4. **Modify `frontend/src/components/run-status.tsx`** (or `dashboard.tsx`'s `RunStatusIcon`) — add "cancelled" case:
   ```tsx
   case "cancelled":
     return <Ban className="h-4 w-4 text-amber-500" />;
   ```

5. **Update `frontend/src/types/schemas.ts`** — the `runStatusResponseSchema.status` field is already `z.string()`, so no change needed. But update the `useRunStatus` polling stop condition:
   ```typescript
   if (status === "completed" || status === "failed" || status === "cancelled") return false;
   ```

6. **Update `useRun` hook** — the `isRunning` check should also exclude "cancelled":
   ```typescript
   const isRunning =
     activeRunId !== null &&
     runStatus?.status !== "completed" &&
     runStatus?.status !== "failed" &&
     runStatus?.status !== "cancelled";
   ```

## Dependencies
- None (but related to T06 — the sessionStorage persistence and run history should account for "cancelled" status)

## Files to Modify/Create
- `db/migrations/018_cancelled_status.sql` (new)
- `services/run_manager.py` (modify — add cancel_run, cancellation flag, check in _execute)
- `services/pipeline.py` (modify — add is_cancelled callback parameter)
- `api/routes/api_pipeline.py` (modify — add cancel endpoint)
- `api/schemas.py` (possibly no changes needed)
- `frontend/src/api/pipeline.ts` (modify — add cancelRun)
- `frontend/src/hooks/use-run.ts` (modify — add cancelRun mutation, update isRunning to exclude cancelled)
- `frontend/src/pages/dashboard.tsx` (modify — add Stop button, confirmation dialog, cancelled icon)
- `frontend/src/types/schemas.ts` (possibly no changes needed)

## Tests
- Unit test: `RunManager.cancel_run()` sets cancelled flag and updates DB status
- Unit test: `PipelineService.run_pipeline()` checks `is_cancelled` between evaluations and stops
- API test: `POST /api/run/{id}/cancel` returns 200 for running run
- API test: `POST /api/run/{id}/cancel` returns 409 for completed run
- API test: `POST /api/run/{id}/cancel` returns 404 for unknown run or other user's run
- Frontend: Stop button appears when run is active, disappears when run is terminal
- Frontend: Cancellation confirmation dialog works