# FE-12: deleteSearchConfig Generic Is Misleading

- **Phase:** improvements
- **Priority:** P3 (Medium)
- **Status:** TODO
- **Depends on:** None

## Problem

In `src/api/search-config.ts:24`, `api<{ ok: boolean }>(...)` specifies a return type generic, but the return value of `deleteSearchConfig` is never used by any caller. The generic creates a false expectation that the response is parsed and returned.

## Approach

Change the generic to `void` to match the actual intent:

```ts
export function deleteSearchConfig(id: string): Promise<void> {
  return api<void>(`/api/search-configs/${id}`, { method: "DELETE" });
}
```

## Files

- `frontend/src/api/search-config.ts:24` — change generic from `{ ok: boolean }` to `void`

## Implementation Notes

- Trivial change, no risk of regression.
