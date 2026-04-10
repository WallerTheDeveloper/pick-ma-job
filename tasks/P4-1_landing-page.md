# P4-1: Public Landing Page

- **Phase:** 4 — New Features & Visual
- **Priority:** P3 — Nice to have
- **Status:** TODO
- **Depends on:** P4-2 (visual redesign — should share the same color scheme)

## Problem

No public-facing page. Unauthenticated users go straight to the login form with no explanation of what the product does.

## Changes Required

### Routing — `frontend/src/App.tsx`

- `/` → Landing page (public)
- `/dashboard` → Dashboard (protected, was previously `/`)
- Update all nav links and redirects

### Navigation — `frontend/src/components/layout/app-shell.tsx`

- Change first nav item from `{ to: "/", label: "Dashboard" }` to `{ to: "/dashboard", label: "Dashboard" }`

### New Page — `frontend/src/pages/landing.tsx`

Content sections:
1. **Hero** — tagline, subtitle, CTA button ("Get Started" → login)
2. **How it works** — 3-step visual:
   - Set up your profile
   - Configure platform searches
   - Get AI-scored job matches
3. **Features** — key selling points:
   - Multi-platform (Upwork, LinkedIn, more coming)
   - AI evaluation with Claude
   - Smart scoring and filtering
   - Saves hours of manual job hunting
4. **Platforms** — supported platform logos/icons
5. **Footer** — minimal footer with sign-in link

### Landing Page Header

- Simple top navbar with logo + "Sign In" button
- Not the sidebar layout (that's for authenticated users only)

## Files

- `frontend/src/App.tsx`
- `frontend/src/pages/landing.tsx` (new)
- `frontend/src/components/layout/app-shell.tsx`
- `frontend/src/components/protected-route.tsx` (redirect target changes from `/login` to `/`)

## Acceptance Criteria

- [ ] Unauthenticated users see landing page at `/`
- [ ] Landing page explains the product clearly
- [ ] "Get Started" / "Sign In" buttons navigate to `/login`
- [ ] Authenticated users can still access `/dashboard`
- [ ] All existing internal links and redirects updated
