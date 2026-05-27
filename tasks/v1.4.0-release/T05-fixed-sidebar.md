# T05 - Fixed Sidebar That Doesn't Scroll With Page

## Priority
Medium

## Status
.Done

## Description
On the Profile and Results pages, the left sidebar's bottom section (with version, email, sign out, theme toggle) is pushed down when the main content area is tall. The sidebar stretches to match the content height, requiring scrolling to reach the bottom buttons. The fix is to make the sidebar sticky so it stays fixed while the main content scrolls.

## Context
- `frontend/src/components/layout/app-shell.tsx` (line 27-78) contains the layout.
- Current structure: `<div className="flex min-h-screen">` with `<aside>` and `<main>`. The aside grows with the flex container when main has lots of content.
- Dashboard and Search Config pages don't have this issue because their content is shorter.
- The aside has `flex flex-col` and the bottom section is pushed down by `flex-1` on the nav.

## Acceptance Criteria
- [ ] Sidebar stays fixed in the viewport while main content scrolls
- [ ] Bottom section (version, email, sign out, theme toggle) is always visible without scrolling the sidebar
- [ ] Main content area scrolls independently
- [ ] Layout works correctly on pages with short content (Dashboard) and long content (Results, Profile)
- [ ] Responsive behavior is preserved (sidebar still works on mobile if applicable)

## Implementation Notes

Modify `frontend/src/components/layout/app-shell.tsx`:

1. Change the outer `<div>` from `flex min-h-screen` to `flex h-screen` (or keep `min-h-screen` — either works, but the sidebar needs `h-screen`)

2. Add `h-screen sticky top-0` to the `<aside>`:
   ```tsx
   <aside className="w-60 border-r border-sidebar-border bg-sidebar text-sidebar-foreground flex flex-col h-screen sticky top-0">
   ```

3. Add `overflow-y-auto` to `<main>` so it scrolls independently:
   ```tsx
   <main className="min-w-0 flex-1 overflow-y-auto overflow-x-hidden p-6">
   ```

4. The complete change:
   - `<div className="flex min-h-screen">` → `<div className="flex min-h-screen">` (keep as-is, or change to `h-screen` — both work with sticky)
   - `<aside className="w-60 border-r border-sidebar-border bg-sidebar text-sidebar-foreground flex flex-col">` → `<aside className="w-60 border-r border-sidebar-border bg-sidebar text-sidebar-foreground flex flex-col h-screen sticky top-0">`
   - `<main className="min-w-0 flex-1 overflow-x-hidden p-6">` → `<main className="min-w-0 flex-1 overflow-y-auto overflow-x-hidden p-6">`

The `h-screen` gives the aside the full viewport height. The `sticky top-0` keeps it pinned. The `flex-1` on the nav section pushes the bottom section to the bottom. The main area gets `overflow-y-auto` so it scrolls independently.

## Dependencies
- None

## Files to Modify/Create
- `frontend/src/components/layout/app-shell.tsx` (modify)

## Tests
- Visual verification: on Results page with many items, sidebar bottom section stays visible
- Visual verification: on Dashboard page, sidebar still renders correctly
- Verify no horizontal scrollbar on sidebar
- Verify main content scrolls smoothly