# FE-16: Async Mutation Callers in ListManager Have No try/catch

- **Phase:** improvements
- **Priority:** P3 (Medium)
- **Status:** TODO
- **Depends on:** None

## Problem

In `src/components/list-manager.tsx:32-36,44-50`, `handleCreate` and `commitRename` call `await createList(...)` and `await renameList(...)` without try/catch. If the mutation fails, the error is silently swallowed with no user feedback.

## Approach

Wrap each async call in try/catch with `toast.error(...)`:

```ts
async function handleCreate() {
  try {
    await createList(newName);
    setNewName("");
  } catch (err: unknown) {
    toast.error(err instanceof Error ? err.message : "Failed to create list");
  }
}
```

Apply the same pattern to `commitRename`.

## Files

- `frontend/src/components/list-manager.tsx:32–36` — add try/catch to handleCreate
- `frontend/src/components/list-manager.tsx:44–50` — add try/catch to commitRename

## Implementation Notes

- Check other components in the codebase for the same pattern of unguarded async mutation calls.
