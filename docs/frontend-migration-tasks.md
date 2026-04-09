# Frontend Migration Tasks

Reference: [frontend-migration-plan.md](frontend-migration-plan.md)

---

## Phase 0 — Project Scaffolding

- [x] Initialize Vite + React 19 + TypeScript project in `frontend/`
- [x] Install core dependencies: `react`, `react-dom`, `typescript`, `@types/react`, `@types/react-dom`
- [x] Install and configure Tailwind CSS v4
- [x] Initialize shadcn/ui, install base components: `button`, `input`, `textarea`, `card`, `table`, `badge`, `select`, `dialog`, `sonner`, `collapsible`, `dropdown-menu`, `separator`
- [x] Install TanStack Query v5 (`@tanstack/react-query`)
- [x] Install React Router v7 (`react-router`)
- [x] Install Zod
- [x] Configure Vite dev proxy: `/api/*` and `/auth/*` → `http://localhost:8000`
- [x] Create API client module (`src/api/client.ts`): base fetch wrapper with CSRF cookie reading, `credentials: "include"`, error handling
- [x] Create app shell layout (`src/components/layout/app-shell.tsx`): sidebar nav + main content area
- [x] Create routing skeleton in `App.tsx` with placeholder pages
- [x] Verify end-to-end: `npm run dev` serves React, API calls reach FastAPI through proxy
- [x] Add `frontend/` to `.gitignore` entries for `node_modules/`, `dist/`

---

## Phase 1 — Backend API Conversion

- [x] Create `api/routes/api_auth.py`: `GET /auth/me` → returns current user or null (new endpoint)
- [x] Ensure `POST /auth/magic-link` returns JSON `{ok: true}` (not HTML)
- [x] Ensure `POST /auth/logout` returns JSON `{ok: true}` (not HTML/HX-Redirect)
- [x] Ensure `GET /auth/verify` sets cookies and redirects to `/` (works for SPA)
- [x] Create `api/routes/api_dashboard.py`: `GET /api/dashboard` → JSON with user info, profile status, config count, recent runs
- [x] Create `api/routes/api_results.py`: `GET /api/results` → JSON with results array + pagination metadata
- [x] Create `api/routes/api_results.py`: `PATCH /api/results/{id}` → JSON response for status update
- [x] Create `api/routes/api_profile.py`: `GET /api/profile` → JSON with profile data or null
- [x] Create `api/routes/api_profile.py`: `POST /api/profile` → JSON with saved profile
- [x] Create `api/routes/api_search_config.py`: `GET /api/search-configs` → JSON with configs array
- [x] Create `api/routes/api_search_config.py`: `POST /api/search-configs` → JSON with created config
- [x] Create `api/routes/api_search_config.py`: `DELETE /api/search-configs/{id}` → JSON `{ok: true}`
- [x] Move pipeline routes: `POST /api/run`, `GET /api/run/{id}/status` (already JSON, just re-prefix)
- [x] Create `api/routes/api_admin.py`: `GET /api/admin/users` → JSON with users array
- [x] Define Pydantic response models for all new endpoints
- [x] Add CORS middleware for Vite dev server (`http://localhost:5173`)
- [x] Keep all old Jinja routes alive (coexistence)
- [x] Test every new JSON endpoint with curl/httpie

---

## Phase 2 — Auth Flow (React)

- [x] Create Zod schemas for auth responses (`src/types/schemas.ts`)
- [x] Create `use-auth` hook (`src/hooks/use-auth.ts`): calls `GET /auth/me`, exposes `user`, `isLoading`, `isAuthenticated`
- [x] Create `ProtectedRoute` component: redirects to `/login` if not authenticated
- [x] Build login page (`src/pages/login.tsx`): email form, POST to `/auth/magic-link`
- [x] Build check-email page (`src/pages/check-email.tsx`): confirmation message + retry link
- [x] Handle `/auth/verify` redirect flow: server sets cookie → redirects to `/` → React picks up session via `GET /auth/me`
- [x] Build logout function: POST to `/auth/logout`, invalidate TanStack Query cache, redirect to `/login`
- [x] Wire routing: public routes (login, check-email), protected routes (all others)
- [x] Test full magic-link flow end-to-end in React

---

## Phase 3 — Dashboard & Navigation

- [x] Build sidebar nav component with links: Dashboard, Results, Profile, Search Config
- [x] Add conditional Admin link (only if `user.is_admin`)
- [x] Highlight active nav link based on current route
- [x] Build dashboard page (`src/pages/dashboard.tsx`):
  - [x] Welcome section with user email
  - [x] Quick stats cards (profile status, config count)
  - [x] "Run Pipeline" button → `POST /api/run`
  - [x] Run status widget with polling (`refetchInterval: 2000` while running)
- [x] Create `use-run` hook (`src/hooks/use-run.ts`): start run mutation + status polling query
- [x] Create `run-status.tsx` component: displays pending/running/completed/failed with result summary
- [x] Test pipeline trigger and live status polling

---

## Phase 4 — Results Page

- [x] Create `use-results` hook (`src/hooks/use-results.ts`): fetch with filter/sort/pagination params
- [x] Build results page (`src/pages/results.tsx`):
  - [x] Filter bar: status dropdown, minimum score, platform selector
  - [x] Sort controls: by score, by date
  - [x] Pagination controls
- [x] Build result row component (`src/components/result-row.tsx`):
  - [x] Score badge with color coding (green 9-10, blue 7-8, yellow 5-6, orange 3-4, red 1-2)
  - [x] Title, platform, recommendation display
  - [x] Expandable details section: evaluation text, scratchpad, flags, job URL link
  - [x] Status dropdown (new/applied/dismissed) → `PATCH /api/results/{id}`
- [x] Build score badge component (`src/components/score-badge.tsx`)
- [x] Create Zod schemas for results responses
- [x] Test filtering, sorting, pagination, status updates

---

## Phase 5 — Profile Page

- [x] Create `use-profile` hook (`src/hooks/use-profile.ts`): fetch query + save mutation
- [x] Build profile page (`src/pages/profile.tsx`):
  - [x] Form sections: skills, experience level, rate, background, notable projects, languages, "not a good fit for", custom rubric
  - [x] Zod validation for form fields
  - [x] Save button with loading state
  - [x] Success/error toast notifications
  - [x] Empty state for new users (no profile yet)
- [x] Create Zod schemas for profile data
- [x] Test create new profile, edit existing profile, validation errors

---

## Phase 6 — Search Configuration Page

- [x] Create `use-search-config` hook (`src/hooks/use-search-config.ts`): list, create, delete
- [x] Build search config page (`src/pages/search-config.tsx`):
  - [x] List existing configs as cards
  - [x] "Add Config" button → opens inline form
  - [x] Platform selector (Upwork, LinkedIn)
  - [x] Query input and platform-specific filter fields
  - [x] Delete button with confirmation dialog
- [x] Create Zod schemas for search config data
- [x] Test add config, delete config, form validation

---

## Phase 7 — Admin Page

- [x] Build admin users page (`src/pages/admin.tsx`):
  - [x] Users table: email, registration date, last login, job count
  - [x] Admin access gate (redirect if not admin)
- [x] Create `use-admin` hook or inline TanStack Query call
- [x] Create Zod schemas for admin responses
- [x] Test admin page renders for admin user, redirects for non-admin

---

## Phase 8 — Cleanup & Deployment

- [x] Delete `templates/` directory (all Jinja templates and partials)
- [x] Delete `static/` directory (old CSS)
- [x] Remove old Jinja HTML routes from FastAPI route modules
- [x] Remove Jinja2 and `python-multipart` from `requirements.txt` (if no longer needed)
- [x] Remove HTMX CDN and `TemplateResponse` imports from codebase
- [x] Build frontend: `cd frontend && npm run build`
- [x] Configure nginx:
  - [x] Serve `frontend/dist/` at `/`
  - [x] `try_files $uri /index.html` for SPA routing fallback
  - [x] `proxy_pass` for `/api/*` and `/auth/*` to uvicorn
- [x] Create or update deployment script to include frontend build step
- [ ] Test full end-to-end flow on DigitalOcean droplet
- [x] Update `CLAUDE.md` to reflect new frontend stack
- [x] Update `docs/saas-mvp-plan.md` tech stack section
