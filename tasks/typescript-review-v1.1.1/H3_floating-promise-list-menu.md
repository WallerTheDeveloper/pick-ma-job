# H3: Fix Floating Promise in `AddToListMenu` Handler

- **Phase:** High
- **Priority:** P1 — Unhandled Rejection / Missing Feedback
- **Status:** DONE
- **Depends on:** None

## Problem

`frontend/src/components/add-to-list-menu.tsx:118–121` creates a promise but neither awaits it nor returns it from the handler:

```ts
onClick={() => {
  const promise = inList ? onRemove(list.id) : onAdd(list.id);
  promise.catch((err: unknown) => {
    toast.error(err instanceof Error ? err.message : "Failed to update list");
  });
}}
```

Issues:
1. The promise is floating — only `.catch()` is chained, so in React concurrent mode and in some environments this does not properly suppress an unhandled rejection.
2. There is no loading state during the operation — the dropdown stays open with no visual feedback while the mutation is in flight.
3. The dropdown does not close on success.

## Solution

Make the handler `async`, await the operation, handle errors explicitly, and close the dropdown on success:

```ts
onClick={async () => {
  try {
    if (inList) {
      await onRemove(list.id);
    } else {
      await onAdd(list.id);
    }
    setOpen(false);
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Failed to update list");
  }
}}
```

If a loading indicator is needed, track a local `isPending` state or use TanStack Mutation's `isPending` flag passed from the parent.

## Files

- `frontend/src/components/add-to-list-menu.tsx`

## Acceptance Criteria

- [ ] The `onClick` handler is `async` and `await`s the `onAdd`/`onRemove` promise
- [ ] Errors are caught in a `try/catch` block and shown via `toast.error`
- [ ] The dropdown closes on a successful operation
- [ ] No floating/unhandled promise rejections in the browser console during list toggle operations
