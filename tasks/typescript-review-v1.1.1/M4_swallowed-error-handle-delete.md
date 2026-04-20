# M4: Handle Errors in `ListManager.handleDelete`

- **Phase:** Medium
- **Priority:** P2 — Silent Failure
- **Status:** DONE
- **Depends on:** None

## Problem

`frontend/src/components/list-manager.tsx:67–73` has no error handling in `handleDelete`:

```ts
async function handleDelete(list: JobList) {
  if (selectedListId === list.id) {
    onSelectList(null);
  }
  await deleteList(list.id);
  setDeleteTarget(null);
}
```

If `deleteList` throws (network error, 403, 404, etc.), the error is swallowed silently — no toast, no UI feedback. Additionally, `onSelectList(null)` fires unconditionally *before* the delete completes, so the selection clears even if the delete fails.

Compare with `handleCreate` just above it, which correctly uses try/catch.

## Solution

Add a try/catch and move the `onSelectList` call to after a successful delete:

```ts
async function handleDelete(list: JobList) {
  try {
    await deleteList(list.id);
    if (selectedListId === list.id) {
      onSelectList(null);
    }
    setDeleteTarget(null);
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Failed to delete list");
  }
}
```

## Files

- `frontend/src/components/list-manager.tsx`

## Acceptance Criteria

- [ ] `handleDelete` wraps the `deleteList` call in a try/catch
- [ ] A failed delete shows a `toast.error` with a meaningful message
- [ ] `onSelectList(null)` only fires after a successful delete
- [ ] `setDeleteTarget(null)` (close dialog) only fires after a successful delete
- [ ] TypeScript compiles without errors
