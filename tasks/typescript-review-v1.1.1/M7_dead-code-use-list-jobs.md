# M7: Remove Unreachable Dead Code in `useListJobs` Query Function

- **Phase:** Medium
- **Priority:** P2 — Code Clarity
- **Status:** DONE
- **Depends on:** None

## Problem

`frontend/src/hooks/use-lists.ts:74–83` has an unreachable `undefined` branch inside the `queryFn`:

```ts
queryFn: async () => {
  if (listId === undefined) {
    throw new Error("listId is required");
  }
  if (listId === null) {
    return [];
  }
  return fetchListJobs(listId);
},
```

The TypeScript type of `listId` is `string | null` — it can never be `undefined`. The `enabled: listId !== null` guard already prevents the `queryFn` from executing when `listId` is `null`, making both the `undefined` check and the `null` check inside `queryFn` redundant dead code.

This confuses future readers into thinking `undefined` is a valid state, and the presence of the `null` guard inside `queryFn` suggests the `enabled` guard may not be trusted.

## Solution

Remove both dead branches from the `queryFn`:

```ts
queryFn: async () => {
  return fetchListJobs(listId!);
},
```

The non-null assertion `listId!` is safe here because `enabled: listId !== null` guarantees `queryFn` only runs when `listId` is a `string`. Alternatively, use a type assertion comment:

```ts
queryFn: () => fetchListJobs(listId as string),
```

## Files

- `frontend/src/hooks/use-lists.ts`

## Acceptance Criteria

- [ ] The `listId === undefined` branch is removed from `queryFn`
- [ ] The redundant `listId === null` branch is removed from `queryFn`
- [ ] The `enabled: listId !== null` guard remains as the sole gate
- [ ] TypeScript compiles without errors and the non-null assertion is type-safe given the `enabled` guard
