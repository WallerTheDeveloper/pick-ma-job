# P4-4: Dark Mode Theme

- **Phase:** 4 — Features
- **Priority:** P3 — Enhancement
- **Status:** DONE
- **Depends on:** None

## Problem

The app has no dark mode. Users who prefer dark interfaces or use the app at night have no option to switch themes.

## Approach

Use Tailwind CSS v4's built-in dark mode support (`dark:` variant) with a manual class toggle on `<html>` (i.e., `class="dark"`). Persist the user's preference in `localStorage`.

## Files

- `frontend/src/main.tsx` or `frontend/index.html` — apply initial theme class before render (avoids flash)
- `frontend/tailwind.config.ts` or equivalent — confirm `darkMode: 'class'` is set (Tailwind v4 default)
- `frontend/src/components/` — new `ThemeToggle` component (button with sun/moon icon)
- `frontend/src/hooks/` — new `use-theme.ts` hook (read/write localStorage + toggle)
- All page components — audit and add `dark:` variants for backgrounds, text, borders, cards

## Implementation Notes

- **Flash of wrong theme:** Apply the theme class synchronously in a `<script>` tag in `index.html` before React hydrates, reading from `localStorage`
- **shadcn/ui components:** Most already support `dark:` variants if the `dark` class is on `<html>` — verify after enabling
- **Toggle placement:** Top navigation bar, accessible from every page
- **System preference fallback:** If no localStorage value exists, use `prefers-color-scheme: dark` as the default

## Acceptance Criteria

- [x] Dark mode toggle button is visible on all pages
- [x] Toggling switches the theme across all pages instantly
- [x] Theme preference persists across page reloads (localStorage)
- [x] No flash of light theme when loading with dark mode active
- [x] All major UI elements (background, text, cards, tables, inputs) have correct dark variants
- [x] System `prefers-color-scheme: dark` is respected on first visit
