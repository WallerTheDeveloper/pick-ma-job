# FE-17: void Operator Discards Mutation Promise in AddToListMenu

- **Phase:** improvements
- **Priority:** P3 (Medium)
- **Status:** DONE
- **Depends on:** None

## Problem

In `src/components/add-to-list-menu.tsx:76`, the `void` operator explicitly discards the promise from `onRemove(list.id)` or `onAdd(list.id)`. If the mutation rejects, the error is silently lost with no user feedback.

## Approach

Replace `void` with proper error handling:

```ts
onClick={() => {
  const promise = inList ? onRemove(list.id) : onAdd(list.id);
  promise.catch((err: unknown) => {
    toast.error(err instanceof Error ? err.message : "Failed to update list");
  });
}}
```

## Files

- `frontend/src/components/add-to-list-menu.tsx:76` — handle promise rejection

## Implementation Notes

- Ensure `toast` is imported. Check if the component already imports it or if `sonner` is available.
