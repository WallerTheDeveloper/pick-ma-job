# FE-7: useRun useEffect Re-fires invalidateQueries on Every Render After Completion

- **Phase:** fixes
- **Priority:** P2 (High)
- **Status:** DONE
- **Depends on:** None

## Problem

In `src/hooks/use-run.ts:35-40`, the `useEffect` fires `invalidateQueries` not just once when the run transitions to a terminal state, but on every re-render while status remains `"completed"` or `"failed"`. This causes unnecessary network requests and potential UI flickering.

## Approach

Track the previous status with a `useRef` and only invalidate on the actual transition:

```ts
const prevStatusRef = useRef<string | undefined>(undefined);

useEffect(() => {
  const status = statusQuery.data?.status;
  if (
    (status === "completed" || status === "failed") &&
    prevStatusRef.current !== status
  ) {
    queryClient.invalidateQueries({ queryKey: ["dashboard"] });
  }
  prevStatusRef.current = status;
}, [statusQuery.data?.status, queryClient]);
```

## Files

- `frontend/src/hooks/use-run.ts:35–40` — add useRef guard for status transition

## Implementation Notes

- Verify that the dashboard data does refresh exactly once when a run completes, not zero times or multiple times.
