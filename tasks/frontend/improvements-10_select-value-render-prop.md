# FE-18: SelectValue Render-Prop Pattern Is Not a Supported shadcn/Radix API

- **Phase:** improvements
- **Priority:** P3 (Medium)
- **Status:** TODO
- **Depends on:** None

## Problem

In `src/pages/results.tsx:117-118`, `<SelectValue>` is used with a function as children:
```tsx
<SelectValue>
  {(value) => statusLabels[value as string] ?? "All statuses"}
</SelectValue>
```
The shadcn/ui `SelectValue` component (wrapping Radix `Select.Value`) does not support render-prop children. This likely renders the function's string representation or nothing at all.

## Approach

Remove the render-prop and use the `placeholder` prop combined with controlled state:

```tsx
<SelectValue placeholder="All statuses" />
```

If custom display text is needed for the selected value, derive it from `filters.status` and render it directly:

```tsx
<SelectTrigger>
  <span>{filters.status ? statusLabels[filters.status] : "All statuses"}</span>
</SelectTrigger>
```

## Files

- `frontend/src/pages/results.tsx:117–118` — fix SelectValue usage

## Implementation Notes

- Check the other Select components on the same page for the same pattern.
- Verify the fix renders correctly for all status values including the "All" option.
