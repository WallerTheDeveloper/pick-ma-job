# FE-6: Non-null Assertion `listId!` Inside queryFn

- **Phase:** fixes
- **Priority:** P2 (High)
- **Status:** DONE
- **Depends on:** None

## Problem

In `src/hooks/use-lists.ts:75`, the query function uses `listId!` with a non-null assertion, relying on the `enabled: listId !== null` guard to prevent the function from running when `listId` is null. If the `enabled` condition is changed or removed, this silently passes `null` to the API call.

## Approach

Replace the non-null assertion with an explicit runtime guard inside the queryFn:

```ts
queryFn: () => {
  if (listId === null || listId === undefined) {
    throw new Error("listId is required to fetch jobs in a list");
  }
  return fetchJobsInList(listId);
},
```

## Files

- `frontend/src/hooks/use-lists.ts:75` — replace `listId!` with runtime guard

## Implementation Notes

- This pattern should be applied to any other queryFn that uses non-null assertions on dependent parameters.
