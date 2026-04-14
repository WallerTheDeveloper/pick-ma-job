# P2-3: Fix Result Row Checkbox Styling and Vertical Alignment

- **Phase:** 2 — UX Fix
- **Priority:** P2 — Enhancement
- **Status:** DONE
- **Depends on:** None

## Problem

Checkboxes on the results page look like unstyled default HTML `<input type="checkbox">` elements, which is visually inconsistent with the rest of the UI. Additionally, checkboxes are top-aligned within result rows instead of being vertically centered.

## Solution

### Frontend

1. **`frontend/src/pages/results.tsx`** — locate all result row checkbox elements.

2. Replace raw `<input type="checkbox">` with the shadcn/ui `<Checkbox>` component:
   ```tsx
   import { Checkbox } from "@/components/ui/checkbox";

   <Checkbox
     checked={selectedIds.has(job.id)}
     onCheckedChange={(checked) => handleSelect(job.id, !!checked)}
   />
   ```

3. Fix vertical alignment — ensure the checkbox cell/container uses flexbox centering:
   ```tsx
   <div className="flex items-center justify-center self-center">
     <Checkbox ... />
   </div>
   ```
   Or if the row itself is a flex/grid container, add `items-center` to the row element so all cells (including the checkbox column) align to the vertical center.

4. Verify the "select all visible" header checkbox (if present) receives the same treatment.

## Files

- `frontend/src/pages/results.tsx`
- `frontend/src/components/ui/checkbox.tsx` — should already exist; no changes expected

## Acceptance Criteria

- [x] Result row checkboxes use the shadcn/ui `Checkbox` component (styled, not default HTML)
- [x] Checkboxes are vertically centered relative to the result row height
- [x] Checkbox interaction (select/deselect) works identically to before
- [x] "Select all visible" header checkbox also uses the styled component and is centered
- [x] No visual regression on selected/indeterminate states
