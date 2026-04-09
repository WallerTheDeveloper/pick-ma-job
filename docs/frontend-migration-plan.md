# Frontend Migration Plan: Jinja2/HTMX to React/TypeScript

## Goal

Replace Jinja2 templates and HTMX with a React SPA. The backend stays Python/FastAPI but becomes a pure JSON API. The frontend is a separate build artifact served as static files from nginx on the same DigitalOcean droplet.

## Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| Framework | React 19 | Largest ecosystem, hiring pool, library support |
| Language | TypeScript 5 | Type safety, matches FastAPI's Pydantic contracts |
| Build tool | Vite | Fast dev server, static output, simple config |
| Styling | Tailwind CSS v4 | Already known, utility-first, pairs with shadcn/ui |
| Components | shadcn/ui | Copied into project (no dependency lock-in), accessible, Tailwind-native |
| Data fetching | TanStack Query v5 | Caching, polling, loading/error states out of the box |
| Routing | React Router v7 | Mature, well-documented, SPA routing |
| Validation | Zod | Runtime validation of API responses, mirrors Pydantic schemas |
| HTTP client | ky or native fetch | Lightweight, interceptors for auth headers |

## Architecture Decisions

### SPA, not SSR

The entire app is behind authentication. No public pages need SEO. An SPA is simpler to build, deploy, and reason about. No Next.js/Remix overhead needed.

### Deployment: same droplet, nginx serves static files

```
nginx
├── / → serves frontend/dist/ (React build output)
├── /api/* → proxy_pass to uvicorn (FastAPI)
└── /auth/* → proxy_pass to uvicorn (FastAPI)
```

Vite builds to `frontend/dist/`. Nginx serves the static files and proxies API requests to FastAPI. Single droplet, no extra infrastructure.

### Cookie-based auth stays

The existing magic-link + session cookie flow works perfectly with a React SPA. No need to switch to JWT or bearer tokens.

- Login: React form POSTs to `/auth/magic-link`, redirects to check-email page
- Verify: User clicks email link, hits `/auth/verify?token=...`, server sets `session_token` cookie, redirects to `/`
- CSRF: React reads `csrf_token` cookie and sends it as `X-CSRF-Token` header on mutations
- Session validation: FastAPI checks `session_token` cookie on every `/api/*` request

### Backend becomes JSON-only

All routes that currently return `TemplateResponse` will return JSON instead. The dual-mode pattern (HTML for HTMX, JSON for API) gets removed. Every endpoint returns JSON, every response has a typed schema.

### Type contract: Pydantic <-> Zod

FastAPI Pydantic models define the API contract. The React app has matching Zod schemas for runtime validation. These are manually kept in sync (auto-generation is overkill for this scale).

## Project Structure

```
frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── api/
│   │   ├── client.ts          # Configured fetch/ky instance (CSRF, cookies, base URL)
│   │   ├── auth.ts            # login, verify, logout
│   │   ├── pipeline.ts        # startRun, getRunStatus
│   │   ├── profile.ts         # getProfile, updateProfile
│   │   ├── results.ts         # getResults, updateResultStatus
│   │   ├── search-config.ts   # getConfigs, createConfig, deleteConfig
│   │   └── admin.ts           # getUsers
│   ├── components/
│   │   ├── ui/                # shadcn/ui components (button, input, table, badge, etc.)
│   │   ├── layout/
│   │   │   ├── app-shell.tsx  # Sidebar/navbar + main content area
│   │   │   └── nav.tsx        # Navigation links with active state
│   │   ├── run-status.tsx     # Pipeline run status widget with polling
│   │   ├── result-row.tsx     # Single job result with expandable details
│   │   ├── score-badge.tsx    # Color-coded score display
│   │   └── protected-route.tsx # Auth guard wrapper
│   ├── hooks/
│   │   ├── use-auth.ts        # Auth state, login/logout, current user
│   │   ├── use-results.ts     # TanStack Query: fetch + filter results
│   │   ├── use-profile.ts     # TanStack Query: fetch + mutate profile
│   │   ├── use-run.ts         # TanStack Query: start run + poll status
│   │   └── use-search-config.ts
│   ├── pages/
│   │   ├── login.tsx
│   │   ├── check-email.tsx
│   │   ├── dashboard.tsx
│   │   ├── results.tsx
│   │   ├── profile.tsx
│   │   ├── search-config.tsx
│   │   └── admin/
│   │       └── users.tsx
│   ├── types/
│   │   ├── api.ts             # Response/request types matching Pydantic models
│   │   └── schemas.ts         # Zod schemas for runtime validation
│   ├── lib/
│   │   └── utils.ts           # cn() helper, formatters, constants
│   ├── App.tsx                # Router setup, QueryClientProvider
│   ├── main.tsx               # Entry point
│   └── index.css              # Tailwind directives
├── index.html
├── vite.config.ts             # Dev proxy to FastAPI, build output config
├── tailwind.config.ts
├── tsconfig.json
├── package.json
└── .eslintrc.cjs
```

## Migration Phases

### Phase 0 — Project Scaffolding

Set up the React project alongside the existing Jinja templates. Both frontends coexist during migration.

**Work:**
- Initialize Vite + React + TypeScript project in `frontend/`
- Install and configure: Tailwind CSS v4, shadcn/ui, TanStack Query, React Router, Zod
- Configure Vite dev server to proxy `/api/*`, `/auth/*` to FastAPI (localhost:8000)
- Set up the API client module with CSRF cookie reading and credential inclusion
- Create the app shell layout (sidebar nav, main content area)
- Set up routing skeleton with placeholder pages
- Verify dev workflow: `npm run dev` serves React, API calls proxy to FastAPI

**Outcome:** Running React app with navigation, hitting the real FastAPI backend through the proxy.

### Phase 1 — Backend API Conversion

Convert FastAPI routes from HTML template responses to JSON responses. This is prerequisite for all frontend work.

**Work:**
- Define Pydantic response models for every endpoint that currently returns HTML:
  - `GET /` (dashboard) → `GET /api/dashboard` → `{user: {email, created_at}, has_profile: bool, config_count: int, recent_runs: [...]}`
  - `GET /results` → `GET /api/results` → `{results: [...], pagination: {total, page, limit}}`
  - `GET /profile` → `GET /api/profile` → `{profile: {skills, experience, ...} | null}`
  - `POST /profile` → `POST /api/profile` → `{profile: {...}}`
  - `GET /search-config` → `GET /api/search-configs` → `{configs: [...]}`
  - `POST /search-config` → `POST /api/search-configs` → `{config: {...}}`
  - `DELETE /search-config/{id}` → `DELETE /api/search-configs/{id}` → `{ok: true}`
  - `GET /admin/users` → `GET /api/admin/users` → `{users: [...]}`
  - `GET /auth/me` (new) → `{user: {id, email, is_admin} | null}` — for React to check auth state
- Auth endpoints (`/auth/magic-link`, `/auth/verify`, `/auth/logout`) stay at their current paths, return JSON
- Pipeline endpoints (`POST /run`, `GET /run/{id}/status`) already return JSON — keep as-is, move under `/api/run`
- `PATCH /results/{id}` → `PATCH /api/results/{id}` — already returns JSON for HTMX, just move path
- Keep old Jinja routes alive during migration (both old and new coexist)
- Add CORS middleware configured for the Vite dev server origin (`localhost:5173`)

**Outcome:** Complete JSON API. Every endpoint has a typed Pydantic response model. Old Jinja routes still work.

### Phase 2 — Auth Flow (React)

Port the magic link login flow to React. This unlocks all other pages.

**Work:**
- Create Zod schemas matching auth Pydantic models
- Build `use-auth` hook: checks `GET /auth/me` on mount, provides `user`, `isLoading`, `isAuthenticated`
- Build `ProtectedRoute` wrapper: redirects to `/login` if not authenticated
- Build login page: email form, POST to `/auth/magic-link`, navigate to check-email on success
- Build check-email page: static message + "try again" link
- Handle `/auth/verify` redirect: user lands on the app after clicking email link, cookie is set by server, React detects auth via `GET /auth/me`
- Build logout: POST to `/auth/logout`, clear query cache, redirect to login
- Wire up routing: public routes (login, check-email) and protected routes (everything else)

**Outcome:** Full auth flow in React. Users can log in, stay logged in, and log out.

### Phase 3 — Dashboard & Navigation

Port the dashboard and establish the app shell that all other pages live inside.

**Work:**
- Build the app shell: sidebar with nav links (Dashboard, Results, Profile, Search Config, Admin)
- Show/hide Admin link based on user role from `GET /auth/me`
- Build dashboard page:
  - Welcome message with user email
  - Quick stats (profile complete?, number of search configs, recent run status)
  - "Run Pipeline" button → triggers `POST /api/run`
  - Run status widget with TanStack Query polling (`refetchInterval: 2000` while status is `running`)
- Ensure all nav links work and highlight the active page

**Outcome:** Working dashboard with navigation to all sections. Pipeline can be triggered and status is live-polled.

### Phase 4 — Results Page

Port the results table — the most complex page.

**Work:**
- Build results page with TanStack Query fetching `GET /api/results`
- Implement filters: status (new/applied/dismissed), minimum score, platform
- Implement sorting: by score, by date
- Implement pagination (server-side, using query params)
- Build result row component:
  - Score badge (color-coded: green 9-10, blue 7-8, yellow 5-6, orange 3-4, red 1-2)
  - Title, platform, recommendation
  - Expandable details: full evaluation text, scratchpad, flags, job URL
  - Status dropdown (new/applied/dismissed) → `PATCH /api/results/{id}`
- Use shadcn/ui `Table`, `Badge`, `Select`, `Collapsible` components

**Outcome:** Full results browsing with filtering, sorting, pagination, and inline status updates.

### Phase 5 — Profile Page

Port the profile editor form.

**Work:**
- Fetch profile with TanStack Query (`GET /api/profile`)
- Build form with sections: skills, experience level, rate, background, notable projects, languages, "not a good fit for", custom rubric
- Form validation with Zod (required fields, reasonable lengths)
- Save with mutation (`POST /api/profile`), show success/error toast
- Handle empty state: new user with no profile yet
- Use shadcn/ui `Input`, `Textarea`, `Button`, `Card`, `Toast` components

**Outcome:** Users can create and edit their evaluation profile.

### Phase 6 — Search Configuration Page

Port the search config management.

**Work:**
- List existing configs with TanStack Query (`GET /api/search-configs`)
- Build "Add Config" form: platform selector, query input, platform-specific filter fields
- Delete config with confirmation dialog (`DELETE /api/search-configs/{id}`)
- Use shadcn/ui `Card`, `Dialog`, `Select`, `Input` components

**Outcome:** Users can manage their per-platform search configurations.

### Phase 7 — Admin Page

Port the admin users table.

**Work:**
- Fetch users with TanStack Query (`GET /api/admin/users`)
- Build users table: email, registration date, last login, job count
- Gate access: only render if user is admin, redirect otherwise
- Use shadcn/ui `Table` component

**Outcome:** Admin can view user statistics.

### Phase 8 — Cleanup & Deployment

Remove the old frontend and configure production deployment.

**Work:**
- Delete `templates/` directory and all Jinja partials
- Delete `static/` directory (old CSS)
- Remove Jinja2 dependency from `requirements.txt`
- Remove `TemplateResponse` imports and old HTML routes from FastAPI
- Remove HTMX CDN references
- Remove `python-multipart` if no longer needed (check if form parsing is still used)
- Build frontend: `cd frontend && npm run build` → outputs to `frontend/dist/`
- Configure nginx:
  - Serve `frontend/dist/` at `/`
  - `try_files $uri /index.html` for SPA client-side routing
  - `proxy_pass` for `/api/*` and `/auth/*` to uvicorn
- Update systemd service or add a build step to deployment script
- Test full flow end-to-end on the droplet
- Update `CLAUDE.md` and `docs/saas-mvp-plan.md` to reflect new frontend stack

**Outcome:** Clean codebase, no Jinja remnants, production-ready React frontend served from nginx.

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| Migration breaks existing users | Both frontends coexist during phases 0-7. Old Jinja routes stay alive until phase 8. |
| CSRF handling breaks in SPA | Phase 0 validates CSRF flow works with the API client before building any pages. |
| Type drift between Pydantic and Zod | Keep schemas simple. Manual sync is fine at this scale. Add a CI check later if needed. |
| Scope creep (redesigning UI during migration) | Port existing functionality first. Visual improvements come after migration is complete. |
| Dev experience regression | Vite proxy ensures `npm run dev` talks to the real FastAPI backend — no mock servers needed. |

## What Does NOT Change

- FastAPI backend, all business logic, services, repositories
- PostgreSQL schema and queries
- Authentication mechanism (magic links, session cookies)
- Scraper adapters and evaluator
- Pipeline execution model (background tasks, polling)
- DigitalOcean deployment (same droplet)
- All environment variables and secrets
