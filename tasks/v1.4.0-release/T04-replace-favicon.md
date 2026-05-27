# T04 - Replace Website Favicon

## Priority
Low

## Status
.Pending

## Description
Replace the current SVG favicon with the provided logo PNG and ICO files. The website currently uses `favicon.svg` in `frontend/public/` and references it in `frontend/index.html`. This task swaps it out for the new branding assets.

## Context
- `frontend/index.html` currently has `<link rel="icon" type="image/svg+xml" href="/favicon.svg" />`
- `frontend/public/favicon.svg` exists and needs to be deleted
- Logo files will be placed at `tasks/v1.4.0-release/logo.png` and `tasks/v1.4.0-release/logo.ico`

## Acceptance Criteria
- [ ] `logo.ico` copied to `frontend/public/`
- [ ] `logo.png` copied to `frontend/public/`
- [ ] `frontend/index.html` updated with new favicon links (PNG + ICO, removing SVG reference)
- [ ] `frontend/public/favicon.svg` deleted
- [ ] Browser tab shows the new logo as favicon

## Implementation Notes

1. **Copy logo files** to `frontend/public/`:
   - `tasks/v1.4.0-release/logo.png` → `frontend/public/logo.png`
   - `tasks/v1.4.0-release/logo.ico` → `frontend/public/logo.ico`

2. **Update `frontend/index.html`** — replace the existing favicon `<link>`:
   - Remove: `<link rel="icon" type="image/svg+xml" href="/favicon.svg" />`
   - Add:
     ```html
     <link rel="icon" type="image/png" sizes="32x32" href="/logo.png" />
     <link rel="icon" type="image/x-icon" href="/logo.ico" />
     ```

3. **Delete `frontend/public/favicon.svg`**

4. No changes to sidebar or other page elements.

## Dependencies
- None

## Files to Modify/Create
- `frontend/public/logo.png` (new — copied from task assets)
- `frontend/public/logo.ico` (new — copied from task assets)
- `frontend/index.html` (modify — update favicon links)
- `frontend/public/favicon.svg` (delete)

## Tests
- Visual verification: browser tab shows the new logo
- Verify no 404s for favicon assets in browser DevTools network tab