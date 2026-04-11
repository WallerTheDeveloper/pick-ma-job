# FE-21: Magic Number Not Extracted to Named Constant

- **Phase:** polish
- **Priority:** P4 (Low)
- **Status:** TODO
- **Depends on:** None

## Problem

In `src/hooks/use-auth.ts:18`, `staleTime: 5 * 60 * 1000` is a magic number without a name explaining its purpose.

## Approach

Extract to a named constant at the top of the file:

```ts
const AUTH_STALE_TIME_MS = 5 * 60 * 1000; // 5 minutes
```

Then use it: `staleTime: AUTH_STALE_TIME_MS`.

## Files

- `frontend/src/hooks/use-auth.ts:18` — extract magic number to named constant

## Implementation Notes

- Consider a shared constants file if other hooks use similar stale times.
