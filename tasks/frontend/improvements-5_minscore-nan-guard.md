# FE-13: minScore Typed as String but Number("abc") Would Send NaN to API

- **Phase:** improvements
- **Priority:** P3 (Medium)
- **Status:** DONE
- **Depends on:** None

## Problem

In `src/hooks/use-results.ts:23,44`, `minScore` is typed as `string` in the filters interface. It is converted with `Number(filters.minScore)` before sending to the API, but there is no `isNaN` guard. If the user types a non-numeric string, `NaN` is sent to the backend.

## Approach

Add a NaN guard before including `minScore` in the API params:

```ts
const score = Number(filters.minScore);
...(filters.minScore && !isNaN(score) && { min_score: score }),
```

Also consider validating the input field itself to only accept numeric values.

## Files

- `frontend/src/hooks/use-results.ts:44` — add NaN guard on minScore conversion
- `frontend/src/pages/results.tsx` — optionally add `type="number"` or input validation on the min score field

## Implementation Notes

- The same pattern should be applied anywhere a string-to-number conversion is sent to the API.
