# FE-23: Missing aria-label and htmlFor on Filter Selects

- **Phase:** polish
- **Priority:** P4 (Low)
- **Status:** TODO
- **Depends on:** None

## Problem

In `src/pages/results.tsx:107-128`, filter `<label>` elements have no `htmlFor` attribute, and the `<Select>` components have no `id` or `aria-labelledby`. Screen readers cannot associate the labels with their corresponding controls.

## Approach

1. Add `id` attributes to each Select trigger.
2. Add matching `htmlFor` on each `<label>`.
3. Alternatively, wrap each Select in its `<label>` element for implicit association.

Example:
```tsx
<label htmlFor="status-filter">Status</label>
<Select id="status-filter" ...>
```

## Files

- `frontend/src/pages/results.tsx:107–128` — add htmlFor/id pairs on filter controls

## Implementation Notes

- Radix Select may need the `id` on the `SelectTrigger` rather than the `Select` root. Test with a screen reader or browser accessibility inspector.
