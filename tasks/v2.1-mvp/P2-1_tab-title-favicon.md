# P2-1: Fix Tab Title and Favicon

- **Phase:** 2 — UI Fixes
- **Priority:** P2 — Medium
- **Status:** DONE
- **Depends on:** None

## Problem

- Browser tab shows **"Vite + React + TS"** — should be **"Pick Most Appropriate Job"**
- Browser tab favicon is Vite's default logo — should be a custom icon for the product

## Files

- `frontend/index.html` — `<title>` tag and `<link rel="icon">` tag
- `frontend/public/` — favicon asset location

## Fix

1. **Tab title** — Update `<title>` in `frontend/index.html`:
   ```html
   <title>Pick Most Appropriate Job</title>
   ```

2. **Favicon** — Create a simple custom favicon (SVG preferred for crispness at small sizes) and place it in `frontend/public/`. Update the `<link rel="icon">` reference in `index.html`.
   - Simple option: a briefcase or checkmark SVG in the app's primary color
   - If no design asset exists, a text-based SVG with "PM" initials is acceptable

## Acceptance Criteria

- [ ] Browser tab displays "Pick Most Appropriate Job" as the page title
- [ ] Browser tab shows a custom favicon (not Vite's default)
- [ ] Favicon is visible and recognizable at 16×16 and 32×32 sizes
- [ ] Production build (`npm run build`) includes the updated favicon in `frontend/dist/`
