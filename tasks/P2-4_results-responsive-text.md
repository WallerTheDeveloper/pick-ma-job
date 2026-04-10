# P2-4: Results Page — Responsive Text Wrapping

- **Phase:** 2 — UX Polish
- **Priority:** P1 — High
- **Status:** TODO
- **Depends on:** None

## Problem

Result row text (summary, evaluation, flags, scratchpad) stretches horizontally beyond the viewport, forcing users to scroll right. Text should wrap within the card width.

## Root Cause

`result-row.tsx:106` uses `whitespace-pre-wrap` on evaluation text without constraining the container width. Long unbroken strings or wide content push the card beyond its parent.

## Changes Required

### `frontend/src/components/result-row.tsx`

- Add `overflow-hidden` to the `<Card>` component
- Add `break-words` or `overflow-wrap: anywhere` to all text paragraphs in the expanded section (summary, evaluation, flags, scratchpad)
- Add `max-w-full` or `max-w-prose` to text containers
- Ensure `whitespace-pre-wrap` is paired with `break-words` so long lines wrap
- Test with long URLs, long skill lists, and multi-paragraph evaluations

## Acceptance Criteria

- [ ] All expanded text wraps within the card boundary
- [ ] No horizontal scrollbar appears on the results page
- [ ] Long URLs in evaluation text wrap instead of overflowing
- [ ] Formatting (line breaks in scratchpad/evaluation) is preserved
