# P2-4: Prevent Layout Shift When "Select All" Action Bar Appears

- **Phase:** 2 — UX Fix
- **Priority:** P2 — Enhancement
- **Status:** DONE
- **Depends on:** None

## Problem

When the user clicks "select all visible", a bulk action bar appears and causes all result rows to shift downward. This is visually jarring and a poor UX — content should not jump when a UI control becomes active.

## Solution

### Frontend

1. **`frontend/src/pages/results.tsx`** — locate the action bar (bulk delete / move to list / etc.) that appears on row selection.

2. Preferred fix — make the action bar **sticky/fixed** so it overlays the page without affecting document flow:
   ```tsx
   <div className={`fixed bottom-6 left-1/2 -translate-x-1/2 z-50 transition-opacity duration-150 ${
     selectedIds.size > 0 ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
   }`}>
     {/* action bar content */}
   </div>
   ```
   This keeps the bar always in the DOM (no layout shift), fades it in when rows are selected, and positions it as a floating bar at the bottom of the viewport.

   Alternative fix (if floating bar doesn't fit the design) — always render the action bar at full height but use `visibility: hidden` / `opacity-0` when empty, so it occupies space at all times and no shift occurs:
   ```tsx
   <div className={`transition-opacity duration-150 ${
     selectedIds.size > 0 ? 'opacity-100' : 'opacity-0 pointer-events-none'
   }`}>
     {/* action bar content */}
   </div>
   ```

3. **Ask the user** which visual style is preferred (floating bottom bar vs. always-reserved space at top) if the preferred approach needs design input before implementing. Per the task file this is already noted as a potential input point.

## Files

- `frontend/src/pages/results.tsx`

## Acceptance Criteria

- [ ] Clicking "select all visible" does not cause result rows to shift position
- [ ] The action bar appears/disappears without affecting surrounding layout
- [ ] Action bar buttons (delete, move to list, etc.) remain fully functional
- [ ] Transition is smooth (fade or slide — no abrupt pop-in)
- [ ] Deselecting all rows hides the action bar cleanly without layout shift
