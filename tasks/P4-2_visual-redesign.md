# P4-2: Visual Redesign — Color Scheme & Professional Look

- **Phase:** 4 — New Features & Visual
- **Priority:** P3 — Nice to have
- **Status:** TODO
- **Depends on:** None (can start independently, landing page should use the new theme)

## Problem

The site is black and white only. It looks boring and unfinished. Needs to be eye-pleasing and professional.

## Changes Required

### Color Palette — `frontend/src/index.css` or globals

Update CSS custom properties for the shadcn theme:

- `--primary`: Brand color (proposed: indigo-600 / blue-600 family)
- `--primary-foreground`: White or contrast color for text on primary
- `--accent`: Secondary highlight color
- `--sidebar`: Tinted sidebar background
- Ensure both light and dark mode palettes are defined

### Component Polish

- **Cards:** Add subtle shadows (`shadow-sm`), consistent border-radius, hover lift effect
- **Buttons:** Primary buttons use brand color, add hover/active transitions
- **Sidebar:** Tinted background color, active nav item uses brand color highlight
- **Score badges:** Color gradient based on score value (red 1-3, yellow 4-6, green 7-10) — update `score-badge.tsx`
- **Badges/chips:** Use brand color variants

### Typography

- Consider a display font for headings (Inter is already common with Tailwind)
- Consistent heading sizes and weights across pages

### Icons

- Add lucide-react icons to sidebar nav items (LayoutDashboard, FileSearch, User, Settings, Shield)
- Add icons to dashboard stat cards
- Add icons to buttons where appropriate (play icon for Run Pipeline, etc.)

### General

- Gradient or subtle pattern on hero/header areas
- Consistent spacing and padding across all pages
- Smooth transitions on interactive elements

## Files

- `frontend/src/index.css` (or `globals.css`)
- `frontend/tailwind.config.ts` (if it exists)
- `frontend/src/components/layout/app-shell.tsx` — sidebar icons + colors
- `frontend/src/components/score-badge.tsx` — score color gradient
- `frontend/src/components/ui/button.tsx` — button styles
- `frontend/src/components/ui/card.tsx` — card styles
- All page files (minor class tweaks)

## Acceptance Criteria

- [ ] Site has a cohesive color scheme (not just black and white)
- [ ] Primary brand color used consistently across buttons, links, active states
- [ ] Sidebar has visual polish (icons, tinted background, active highlighting)
- [ ] Score badges are color-coded by score range
- [ ] Cards have shadows and hover effects
- [ ] Both light and dark modes look good
- [ ] Overall impression: professional and polished
