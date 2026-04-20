# M5: Handle Rejection in Per-Row `deleteResult` Callback

- **Phase:** Medium
- **Priority:** P2 — Unhandled Rejection
- **Status:** DONE
- **Depends on:** None

## Problem

`frontend/src/pages/results.tsx:500` passes `deleteResult` as the `onDelete` callback for `ResultRow`:

```ts
onDelete={(id) => deleteResult(id)}
```

`deleteResult` is `deleteMutation.mutateAsync` — it returns a promise that rejects on failure. The `ResultRow` component's `onClick` handler awaits this promise, but there is no try/catch wrapping it. If the request fails (e.g., a concurrent bulk-delete already removed the row, returning 404), the rejection propagates as an unhandled promise rejection.

This is particularly likely when a user triggers a bulk delete and simultaneously clicks a per-row delete on one of the same items.

## Solution

Wrap the `onDelete` callback in a try/catch at the call site in `results.tsx`:

```ts
onDelete={async (id) => {
  try {
    await deleteResult(id);
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Failed to delete result");
  }
}}
```

Alternatively, ensure `ResultRow`'s own `onClick` handler catches the rejection — but since `onDelete` is a prop, the owning page is the right place to handle the error.

## Files

- `frontend/src/pages/results.tsx`

## Acceptance Criteria

- [ ] The `onDelete` callback in `results.tsx` wraps `deleteResult` in a try/catch
- [ ] A failed per-row delete (including 404 from concurrent bulk-delete) shows a toast error rather than an unhandled rejection
- [ ] No unhandled promise rejections appear in the browser console during normal use
- [ ] TypeScript compiles without errors
