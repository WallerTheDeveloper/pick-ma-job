# T02 - Copy per Section in Customize CV Dialog

## Priority
Medium

## Status
.Done

## Description
Add individual "Copy" buttons next to each section title in the Customized CV pane of the CustomizeCVDialog. Currently there is only a global "Copy" button that copies all customized text. Each section in the `sections` array should get its own small copy icon button that copies just that section's content to clipboard with a toast notification.

## Context
- The `CustomizeCVDialog` in `frontend/src/components/customize-cv-dialog.tsx` renders sections at lines 164-184.
- When `sections` is available (`sections && sections.length > 0`), each section has a `title` and `content` field.
- The global `handleCopy` function (line 80) copies the entire `customizedText` — the per-section copy should only copy `section.content`.
- The project uses `sonner` for toast notifications (`toast.success()`) and `lucide-react` for icons.
- The `Copy` icon from `lucide-react` is already used in other components (e.g., `add-to-list-menu.tsx`).

## Acceptance Criteria
- [ ] Each section in the Customized CV pane displays a small copy icon button next to the section title
- [ ] Clicking the copy button copies only that section's `content` to clipboard
- [ ] A toast displays "Copied {SECTION_TITLE}" on success (e.g., "Copied SUMMARY")
- [ ] The copy buttons only appear when sections are available (`sections && sections.length > 0`)
- [ ] Buttons use ghost variant, icon-only (no text label), small size
- [ ] The existing global "Copy" button continues to work unchanged

## Implementation Notes

Modify `frontend/src/components/customize-cv-dialog.tsx`:

1. Add import for `Copy` icon from `lucide-react`:
   ```typescript
   import { Copy } from "lucide-react";
   ```

2. In the section rendering block (approximately lines 168-183), modify the section title `<h3>` element to include a copy button:
   ```tsx
   <div className="flex items-center gap-2">
     <h3 className="font-bold text-sm uppercase tracking-wider text-muted-foreground mb-1">
       {section.title}
     </h3>
     <Button
       variant="ghost"
       size="icon"
       className="h-5 w-5"
       onClick={() => {
         navigator.clipboard.writeText(section.content).then(
           () => toast.success(`Copied ${section.title}`),
           () => toast.error("Failed to copy."),
         );
       }}
     >
       <Copy className="h-3 w-3" />
     </Button>
   </div>
   ```

3. This should be inside the existing section rendering block where `sections && sections.length > 0` is true — no changes needed for the non-sections (textarea) path.

## Dependencies
- None

## Files to Modify/Create
- `frontend/src/components/customize-cv-dialog.tsx` (modify)

## Tests
- Visual verification: each section shows a copy icon, clicking copies section content
- Verify toast shows "Copied {SECTION_TITLE}"
- Verify global "Copy" button still works