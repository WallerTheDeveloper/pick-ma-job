# P2-3: Fix Results Page Filter Display Labels

- **Phase:** 2 — UX Polish
- **Priority:** P1 — High
- **Status:** Done
- **Depends on:** None

## Problem

When a sort/status filter is applied, the select trigger shows raw internal values like `score_desc`, `score_asc` instead of human-readable labels like "Score (high -> low)".

## Root Cause

shadcn `<SelectValue>` renders the selected `value` prop text when no matching `<SelectItem>` children are visible (trigger is collapsed). The fix is to ensure `<SelectValue>` pulls from the `<SelectItem>` label.

## Changes Required

### `frontend/src/pages/results.tsx`

- Check that `<SelectValue>` for the sort dropdown displays the label from `sortLabels` map, not the raw key
- Possible fix: use `placeholder` on `<SelectValue>` and ensure `<SelectItem>` children render the display label
- If shadcn's `<SelectValue>` auto-picks from children, verify it's wired correctly

### `frontend/src/components/ui/select.tsx`

- If needed, check the shadcn select component renders `SelectValue` using the selected item's text content

## Acceptance Criteria

- [x] Sort dropdown shows "Score (high -> low)" not `score_desc`
- [x] Status dropdown shows "New" / "Applied" / "Dismissed" not raw values
- [x] Platform dropdown shows "Upwork" / "LinkedIn" not raw values
- [x] Labels are correct both before and after selection
