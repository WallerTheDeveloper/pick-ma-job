# Task 9 — Create TanStack Query hooks for blacklist

**Size:** S  
**Status:** done

## Goal

Implement TanStack Query v5 hooks in `frontend/src/hooks/use-company-blacklist.ts`.

## Hooks

```ts
// Read
export function useCompanyBlacklist(): UseQueryResult<CompanyBlacklistListResponse>

// Write
export function useAddBlacklistEntry(): UseMutationResult<CompanyBlacklistEntry, Error, string>
export function useRemoveBlacklistEntry(): UseMutationResult<void, Error, string>
```

## Query key

`["company-blacklist"]` — both mutations invalidate this key on success.

## Pattern reference

Follow `frontend/src/hooks/use-lists.ts` or `use-profile.ts` for TanStack Query v5 style (object syntax for `useQuery`, `useMutation` with `onSuccess` invalidation).

## Error handling

- Expose the error from `useQuery` and `useMutation` — let the component decide how to display it.
- Do not swallow errors silently.

## Success Criteria

- `useCompanyBlacklist` returns cached data on re-renders without re-fetching.
- After `useAddBlacklistEntry` succeeds, `useCompanyBlacklist` data refreshes.
- After `useRemoveBlacklistEntry` succeeds, `useCompanyBlacklist` data refreshes.
- TypeScript types flow through correctly (no `any`).
