# T13 - Clear Selection on Filter/List Change

## Priority
Low

## Status
.Done

## Description
When the user changes any filter (status, platform, min_score, sort, search, date range) or switches lists in the ListManager, clear the `selectedIds` set. Currently, selection persists across filter changes, which is confusing — selected jobs may no longer be visible but are still "selected" (the floating bar still shows them).

## Context
- `frontend/src/pages/results.tsx` — manages `selectedIds` state (line 77: `const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())`)
- Filters are managed via `useResults()` hook which provides `filters` and `updateFilter`.
- `searchTerm` and `dateRange` are local state in `ResultsPage`.
- `selectedListId` is also local state (line 74: `const [selectedListId, setSelectedListId] = useState<string | null>(null)`)
- The floating action bar at the bottom of the page shows when `selectedIds.size > 0`.

## Acceptance Criteria
- [ ] Changing any filter (status, platform, minScore, sort) clears selectedIds
- [ ] Changing the search term clears selectedIds
- [ ] Changing the date range clears selectedIds
- [ ] Switching lists in the ListManager clears selectedIds
- [ ] The clearing happens immediately when the filter value changes, not on blur or after a delay

## Implementation Notes

### Modify `frontend/src/pages/results.tsx`

Add a `useEffect` that clears `selectedIds` when any filter/search/date/list dependency changes:

```typescript
import { useState, useDeferredValue, useEffect } from "react";

// Inside ResultsPage component, after all state declarations:
useEffect(() => {
  setSelectedIds(new Set());
}, [
  filters.status,
  filters.platform,
  filters.minScore,
  filters.sort,
  searchTerm,   // or use deferredSearch if you want to clear on each keystroke
  dateRange,
  selectedListId,
]);
```

**Important note:** Using `searchTerm` directly means the selection is cleared on each keystroke. This is acceptable behavior since the visible results change with each character. However, if this feels too aggressive, you could use a debounced version or only clear on meaningful changes. The specification says "clear on any change."

**Alternative approach** — wrap filter setters:

If using `useEffect` causes issues (e.g., clearing selection when filters haven't actually changed due to React re-renders), an alternative is to modify the `updateFilter` function and `setSelectedListId` to also clear selection:

```typescript
function updateFilterAndClear(key: string, value: string) {
  updateFilter(key, value);
  setSelectedIds(new Set());
}
```

Then use `updateFilterAndClear` instead of `updateFilter` in the JSX event handlers. Similarly for `setSelectedListId`:

```typescript
function handleSelectList(listId: string | null) {
  setSelectedListId(listId);
  setSelectedIds(new Set());
}
```

This approach is more explicit and avoids the `useEffect` dependency list maintenance.

### Recommended approach

Use the `useEffect` approach since it's simpler and handles all cases uniformly. If the dependency array needs adjusting, it's a single place to update.

## Dependencies
- None

## Files to Modify/Create
- `frontend/src/pages/results.tsx` (modify — add useEffect or wrapper functions to clear selectedIds)

## Tests
- Select 3 jobs → change status filter → selection cleared
- Select 3 jobs → change platform filter → selection cleared
- Select 3 jobs → change sort order → selection cleared
- Select 3 jobs → type in search → selection cleared
- Select 3 jobs → change date range → selection cleared
- Select 3 jobs → switch to a list in ListManager → selection cleared
- Select jobs in one list → switch to another list → selection cleared