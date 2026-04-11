# FE-22: BulkDismissParams and BulkDeleteParams Are Structurally Identical

- **Phase:** polish
- **Priority:** P4 (Low)
- **Status:** DONE
- **Depends on:** None

## Problem

In `src/api/results.ts:43-50`, `BulkDismissParams` and `BulkDeleteParams` are two separate interfaces with identical fields. This violates DRY and makes future changes error-prone.

## Approach

Extract a shared base type:

```ts
interface BulkActionParams {
  platform?: string;
  status?: string;
  max_score?: number;
  search?: string;
}

type BulkDismissParams = BulkActionParams;
type BulkDeleteParams = BulkActionParams;
```

Keep the type aliases so callsites remain descriptive.

## Files

- `frontend/src/api/results.ts:43–50` — extract shared BulkActionParams type

## Implementation Notes

- If the two types diverge in the future, the aliases make it easy to re-separate them.
