# FE-8: Bulk Dismiss/Delete Sends max_score for What the UI Calls min-score

- **Phase:** fixes
- **Priority:** P1 (Critical)
- **Status:** DONE
- **Depends on:** None

## Problem

In `src/pages/results.tsx:228-233,267-272`, the bulk dismiss and bulk delete functions send:
```ts
...(filters.minScore && { max_score: Number(filters.minScore) }),
```
The UI filter label says "Min score" but the API parameter is `max_score`. This means the feature may dismiss/delete jobs in the opposite direction from what the user expects — a potential data-safety issue.

## Approach

1. Clarify the intended semantics with the backend: does `max_score` mean "dismiss all jobs scoring AT MOST X"?
2. If that IS the intent, rename the UI label from "Min score" to something accurate like "Max score" or "Score threshold".
3. If the intent is to dismiss jobs in the *currently filtered view* (score >= X), then the API param should be `min_score`, not `max_score`.
4. Align the UI label and the API parameter name so they express the same intent.

## Files

- `frontend/src/pages/results.tsx:228–233` — bulk dismiss parameter
- `frontend/src/pages/results.tsx:267–272` — bulk delete parameter
- `frontend/src/pages/results.tsx` — filter label UI text

## Implementation Notes

- This is a data-safety issue. Coordinate with the backend to confirm what `max_score` means in the bulk endpoints before making a code change.
- The fix may be as simple as renaming `max_score` → `min_score` in the API call, or renaming the UI label — but not both without backend alignment.
