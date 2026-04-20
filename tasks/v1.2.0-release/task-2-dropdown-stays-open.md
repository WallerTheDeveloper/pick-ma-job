# Task 2 — UX Bug: "Add to List" Dropdown Closes on Each Click

**Size:** S  
**Status:** done (fix: Base UI uses closeOnClick={false}, not onSelect)

## Problem

Clicking a list item in the "Add to list" dropdown immediately closes the menu. To add a job to multiple lists the user must reopen the dropdown each time — bad UX.

**Desired behaviour:** dropdown stays open after each list selection; closes only when the user clicks outside it.

## Root Cause

`frontend/src/components/add-to-list-menu.tsx:124` — `setOpen(false)` is called explicitly inside the `onClick` handler after each add/remove. On top of that, shadcn/Radix `DropdownMenuItem` auto-closes the menu on select by default.

## Files to Change

- `frontend/src/components/add-to-list-menu.tsx:115-133`
  - Add `onSelect={(e) => e.preventDefault()}` to each list-item `DropdownMenuItem` to suppress Radix's auto-close.
  - Remove `setOpen(false)` from inside the `onClick` handler.
  - Keep `setOpen(false)` only in `handleOpenCreateDialog` — the "Create new list…" path should still close the menu before opening the dialog.
  - After a successful add/remove, invalidate the `["result-lists", jobResultId]` query so the checkmark updates immediately.

## Success Criteria

- User can click multiple list items in one open session; dropdown stays open after each.
- Clicking outside the dropdown closes it (Radix default behaviour — no extra code needed).
- Checkmark appears/disappears correctly next to each list after toggling.
- "Create new list…" still closes the dropdown and opens the dialog.
