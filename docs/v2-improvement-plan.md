# V2 Improvement Plan

> Based on: `feedback/1-MVP-Frontend-Integrated-Feedback.md`
> Created: 2026-04-10

## Overview

This plan addresses all feedback items from the MVP frontend review, organized into 4 phases by dependency order and risk. Each phase can be shipped independently.

---

## Phase 1 — Critical Bugs & Backend Fixes

**Goal:** Make the product actually work in production.

### 1.1 Pipeline broken on production
- **Problem:** Pipeline doesn't work on production server.
- **Action:** Debug production logs (`journalctl -u pick-ma-job`), check Apify token, DB connection, and asyncio task lifecycle in the systemd service. Verify `POST /api/run` returns 200 and the background task runs to completion.
- **Root cause investigation:** Likely one of:
  - Environment variables missing or misconfigured in production `.env`
  - Apify actor call failing (rate limit, token, network)
  - asyncio background task silently crashing (no error propagation to RunManager)
  - Database connection pool exhaustion under systemd
- **Files:** `services/pipeline.py`, `services/run_manager.py`, `main.py`, `.env` on server

### 1.2 Search Config — allow multiple configs per platform
- **Problem:** DB has `UNIQUE (user_id, platform)` constraint. The `upsert` in `repositories/search_config.py:81` uses `ON CONFLICT (user_id, platform) DO UPDATE`, so creating a second Upwork config silently overwrites the first.
- **Action:**
  1. **DB migration:** Drop the `UNIQUE (user_id, platform)` constraint on `search_configs`. Each config row is already identified by its own `id` (UUID primary key), so this is safe.
  2. **Repository:** Change `upsert()` to a plain `INSERT ... RETURNING` (no `ON CONFLICT`). Remove `find_by_user_and_platform()` — it's only used by `pipeline.py` for single-platform runs, which should now query by config ID instead.
  3. **Pipeline service:** Update `run_pipeline()` to iterate over all configs for a platform (not just one). When `platform` filter is passed, query all configs with that platform name.
  4. **Frontend:** No changes needed — the add form already sends a create request. It just silently failed due to the upsert.
- **Files:** DB migration SQL, `repositories/search_config.py`, `services/pipeline.py`, `api/routes/api_search_config.py`

---

## Phase 2 — UX Polish & Responsiveness

**Goal:** Fix usability issues that make the existing features frustrating to use.

### 2.1 Dashboard — live run status with icons (no reload required)
- **Problem:** User sees text "pending"/"completed" and must reload the tab to see status change.
- **Action:**
  1. Replace text status labels with icons: animated spinner (CSS `animate-spin`) for pending/running, checkmark icon for completed, X icon for failed.
  2. The `useRun` hook already polls every 2s via `refetchInterval`. Verify polling works and the `RunStatus` component re-renders on data change.
  3. Also update the **recent runs list** at the bottom of the dashboard: invalidate the `dashboard` query when a run completes (the `useRun` hook's `onSuccess` or `onSettled` should do this).
  4. Add a subtle pulse/glow animation on the spinner so it's visually obvious something is in progress.
- **Files:** `frontend/src/components/run-status.tsx`, `frontend/src/pages/dashboard.tsx`, `frontend/src/hooks/use-run.ts`

### 2.2 Pipeline loading animation
- **Problem:** No visual feedback while pipeline is running.
- **Action:** This overlaps with 2.1. The "Run Pipeline" button should show a spinner while `isRunning` is true. The `RunStatus` card should show an animated loading indicator (skeleton or spinner), not just text "Waiting to start..." / "Scraping and evaluating jobs...".
- **Files:** `frontend/src/pages/dashboard.tsx`, `frontend/src/components/run-status.tsx`

### 2.3 Results page — filter display labels
- **Problem:** When a sort filter is applied, the trigger shows raw values like `score_desc` instead of human-readable labels like "Score (high -> low)".
- **Action:** The `sortLabels` map already exists in `results.tsx`. The issue is likely that shadcn's `<SelectValue>` renders the `value` prop, not the label from the `<SelectItem>` child. Fix by ensuring the `<SelectValue>` displays the mapped label. May need a custom `renderValue` or a controlled display.
- **Files:** `frontend/src/pages/results.tsx`, possibly `frontend/src/components/ui/select.tsx`

### 2.4 Results page — responsive text wrapping
- **Problem:** Summary, evaluation, flags, and scratchpad text stretches horizontally, forcing horizontal scroll.
- **Action:**
  1. Add `break-words` / `overflow-wrap: anywhere` to text sections in `ResultRow`.
  2. Constrain `CardContent` max-width or use `max-w-prose` on text blocks.
  3. Ensure the parent layout doesn't allow unconstrained horizontal growth (check for `whitespace-pre-wrap` without width constraint — line 106 in `result-row.tsx` has this).
  4. Add `overflow-hidden` or `overflow-x-auto` as a safety net on the card.
- **Files:** `frontend/src/components/result-row.tsx`

### 2.5 Clear irrelevant/old jobs
- **Problem:** No way to bulk-clear old or irrelevant results.
- **Action:**
  1. Add a "Dismiss All" or "Clear Old Results" button to the results page header.
  2. Backend: `PATCH /api/results/bulk-dismiss` — sets status to `dismissed` for results older than N days or matching current filter criteria.
  3. Alternative simpler approach: Add a "Dismiss filtered" button that sets all currently-filtered results to "dismissed" status (re-uses existing `PATCH /api/results/{id}` endpoint in a loop, or add a bulk endpoint).
- **Files:** `api/routes/api_results.py`, `repositories/job_result.py`, `frontend/src/pages/results.tsx`, `frontend/src/hooks/use-results.ts`

---

## Phase 3 — Profile Page Redesign

**Goal:** Make profile setup painless for non-technical users.

### 3.1 Profile page — guided UX redesign
- **Problem:** Too many text fields, comma-separated input is confusing, raw JSON rubric is intimidating for non-developers.
- **Action:**
  1. **Skills input:** Replace comma-separated textareas with a tag/chip input component. User types a skill, presses Enter, and sees it as a removable chip. Use an existing shadcn-compatible tag input or build a minimal one.
  2. **Background:** Replace "one entry per line" textarea with a dynamic list of input fields. Each entry gets its own row with an "Add" / "Remove" button (same pattern as Notable Projects).
  3. **Notable Projects:** Already uses the add/remove pattern — keep as-is.
  4. **Rubric:** Replace raw JSON textarea with structured form fields:
     - "Minimum score threshold" (number input, 1-10)
     - "Prefer remote" (toggle/checkbox)
     - "Priority keywords" (tag input)
     - "Avoid keywords" (tag input)
     - Keep an "Advanced: raw JSON" collapsible for power users
  5. **Wizard/stepper (optional):** Consider a multi-step wizard for first-time setup: Step 1 (Basic Info) -> Step 2 (Skills) -> Step 3 (Background) -> Step 4 (Preferences). Show a progress indicator. For returning users, show the full form.
  6. **Onboarding prompts:** Add helper text / examples for each field to guide users.
- **Files:** `frontend/src/pages/profile.tsx`, new component `frontend/src/components/tag-input.tsx`, `frontend/src/types/schemas.ts` (rubric type), `api/schemas.py`

---

## Phase 4 — New Features & Visual Refresh

**Goal:** Make the product presentable and self-explanatory.

### 4.1 Landing / Home page
- **Problem:** No public-facing page explaining the product. Unauthenticated users go straight to login.
- **Action:**
  1. Create a public landing page at `/` (move dashboard to `/dashboard`).
  2. Content sections:
     - **Hero:** Tagline + CTA ("Get Started" / "Sign In")
     - **How it works:** 3-step visual (Set up profile -> Configure searches -> Get AI-scored results)
     - **Features:** Key selling points (multi-platform, AI evaluation, saves time)
     - **Platforms supported:** Upwork, LinkedIn logos
  3. Update routing: `/` = landing (public), `/dashboard` = dashboard (protected).
  4. Update sidebar nav: first item becomes `/dashboard`.
  5. Add a header/navbar to the landing page with "Sign In" button.
- **Files:** `frontend/src/App.tsx`, `frontend/src/pages/landing.tsx` (new), `frontend/src/components/layout/app-shell.tsx`

### 4.2 Visual redesign — color scheme & professional look
- **Problem:** Black and white only, looks boring and unfinished.
- **Action:**
  1. **Color palette:** Pick a primary brand color (suggestion: indigo/blue-600 family — professional, tech, trustworthy). Add accent color for CTAs and highlights.
  2. **Tailwind theme:** Update CSS variables in `tailwind.config` or `globals.css` to set:
     - `--primary`: Brand color
     - `--accent`: Highlight color
     - `--sidebar`: Tinted sidebar background
     - Gradient backgrounds on cards or hero sections
  3. **Component upgrades:**
     - Cards: Add subtle shadows, hover effects, border-radius consistency
     - Buttons: Primary buttons get brand color, hover states, transitions
     - Sidebar: Tinted background, active state highlight with brand color
     - Score badges: Color gradient (red -> yellow -> green) based on score
  4. **Typography:** Consider adding a display font for headings (e.g., Inter for body, Cal Sans or similar for headings).
  5. **Icons:** Add lucide-react icons to nav items, stat cards, and buttons for visual hierarchy.
  6. **Dark mode:** Ensure the color palette works in both light and dark modes (shadcn already supports this).
- **Files:** `frontend/src/index.css` or `globals.css`, `tailwind.config.ts`, component files throughout

---

## Phase Summary

| Phase | Items | Effort | Priority |
|-------|-------|--------|----------|
| 1 — Critical Bugs | Pipeline prod fix, multi-config per platform | Medium | **P0 — Blocking** |
| 2 — UX Polish | Live status icons, loading animations, filter labels, responsive text, clear jobs | Medium | **P1 — High** |
| 3 — Profile Redesign | Tag inputs, structured rubric, guided UX | Medium-Large | **P2 — Medium** |
| 4 — New Features & Visual | Landing page, color scheme, icons, polish | Large | **P3 — Nice to have** |

## Open Questions

1. **Pipeline prod failure:** Need to check production logs before starting. Is the server accessible? Can you share `journalctl` output or server access?
2. **Color palette preference:** Do you have a brand color in mind, or should I propose options?
3. **Profile rubric fields:** The current rubric is a free-form JSON object. What specific rubric fields do you actually want users to configure? (min score, remote preference, keywords — anything else?)
4. **Clear jobs behavior:** Should "clear" mean permanently delete from DB, or just set status to "dismissed"? And should it be time-based (older than X days) or manual selection?
5. **Landing page content:** Do you want to write the marketing copy, or should I draft it based on the CLAUDE.md description?
