# v2.2 Task List

Each task is sized for a single focused coding session (roughly 1–3 hours)
and lists the files to touch plus acceptance criteria. Dependencies marked
where relevant.

---

### T-01 — Fix session cookie persistence (Path=/) ✅ DONE
**Scope:**
- `api/routes/auth.py` — add `path="/"` to the two `set_cookie` calls in
  `verify_magic_link` and the two `delete_cookie` calls in `logout`, for
  both `session_token` and `csrf_token` cookies.
- Manual verification that cookies now have `Path=/` in browser devtools.

**Acceptance:**
- [ ] User stays logged in after navigating to `/`, `/dashboard`, `/results`,
      `/profile`, `/search-config`, `/admin`.
- [ ] `document.cookie` shows both cookies on every path after login.
- [ ] Logout clears cookies on every path (no orphaned cookie).
- [x] Existing auth tests still pass; add one regression test asserting
      `Path=/` in the `Set-Cookie` header.

---

### T-02 — Introduce `VERSION` file and `/api/version` endpoint ✅ DONE
**Scope:**
- Create `VERSION` at repo root with contents `2.2.0`.
- `main.py` — read `VERSION` at app startup, store on `app.state.version`.
- `api/routes/api_version.py` — new router: `GET /api/version` →
  `{"version": "2.2.0"}`. No auth required.
- `api/schemas.py` — add `VersionResponse` model.

**Acceptance:**
- [x] `curl /api/version` returns `{"version": "2.2.0"}`.
- [x] If `VERSION` file missing, app fails fast at startup with a clear log.
- [x] Unit test for the route.

---

### T-03 — Frontend version footer component ✅ DONE
**Depends on:** T-02

**Scope:**
- `frontend/src/api/version.ts` — new API client module.
- `frontend/src/hooks/use-version.ts` — TanStack Query hook (stale-time
  `Infinity`, no refetch).
- `frontend/src/components/version-footer.tsx` — subtle footer, e.g. `v2.2.0`.
- Mount footer on main app layout (dashboard, results, profile, search
  config, admin). Landing/login pages optional.

**Acceptance:**
- [x] Version visible on all authenticated pages.
- [x] No hardcoded version string anywhere in the frontend.
- [x] Zero network requests after first load (query cached forever).

---

### T-04 — LinkedIn scraper implementation ✅ DONE
**Scope:**
- `scrapers/linkedin.py` — implement `fetch_jobs` and `_normalize` mirroring
  `UpworkScraper`. Map `salaryInfo[]` → budget string; all LinkedIn extras
  to `NormalizedJob.extras`.
- `configs/platforms/linkedin.json` — actor_id `2rJKkhh7vjpX7pvjg`,
  default input (reasonable defaults), full `field_mappings` including
  `extras` map (`company_name`, `location`, `work_type`, `sector`,
  `applications_count`, `apply_type`, `posted_time`, `poster_name`, `company_url`).

**NormalizedJob mapping:**
```
id               → jobId
platform         → "linkedin"
title            → jobTitle
description      → jobDescription
url              → jobUrl
skills           → None (not provided by actor)
budget           → salaryInfo joined as "$X – $Y" or None if empty
job_type         → contractType
experience_level → experienceLevel
extras           → { company_name, location, work_type, sector,
                     applications_count, apply_type, posted_time,
                     poster_name, company_url }
```

**Acceptance:**
- [x] `scrapers.registry.get_scraper("linkedin")` returns a working
      `LinkedInScraper`.
- [x] Unit tests cover: standard mapping, missing required fields (returns
      None), empty `salaryInfo`, mixed salaryInfo formats.
- [x] No regression on Upwork scraper tests.

---

### T-05 — LinkedIn prompt context ✅ DONE
**Depends on:** T-04

**Scope:**
- `configs/prompts/linkedin_context.json` — mirror `upwork_context.json`
  structure. `available_fields` must include LinkedIn-specific extras.
  `user_message_template` references every available extra.
- Evaluation notes covering: no skills array available; `applications_count`
  as competition signal; `work_type` (remote/hybrid) weighting; salary from
  `salaryInfo`.

**Acceptance:**
- [x] `core.prompt_adapter.load_platform_context("linkedin")` loads without
      error.
- [x] End-to-end mock evaluation produces valid JSON output given a
      LinkedIn `NormalizedJob`.

---

### T-06 — Generalise `PipelineService` to accept `platforms: list[str] | None` ✅ DONE
**Depends on:** T-04

**Scope:**
- `services/pipeline.py` — change signature to
  `run_pipeline(user_id, platforms: list[str] | None = None)`. Filter
  `search_configs` by the list when provided. Preserve current `None`
  semantics (= all configured platforms).
- `services/run_manager.py` — thread the list through `start_run` and
  `_execute`.
- Add validation: empty list raises `PipelineError("No platforms selected.")`.

**Acceptance:**
- [x] Existing call sites continue to work (default `None`).
- [x] Unit test: two configs, passing `["upwork"]` only runs Upwork.
- [x] Unit test: empty list raises clear error.
- [x] Unit test: unknown platform slug is rejected before dispatch.

---

### T-07 — `POST /api/run` accepts `platforms: list[str]` body ✅ DONE
**Depends on:** T-06

**Scope:**
- `api/schemas.py` — new `RunStartRequest { platforms: list[str] | None = None }`.
- `api/routes/api_pipeline.py` — replace `?platform=` query with JSON body;
  validate every platform against `KNOWN_PLATFORMS`; require at least one
  matching search config for every requested platform (return 400 if any
  missing).
- Remove the old `platform: str | None` query parameter.

**Acceptance:**
- [x] `POST /api/run` with `{"platforms": ["upwork", "linkedin"]}` kicks off
      a run spanning both platforms.
- [x] `POST /api/run` with `{"platforms": ["linkedin"]}` runs only LinkedIn.
- [x] `POST /api/run` with `{}` or `{"platforms": null}` runs all configured
      platforms.
- [x] `POST /api/run` with an unknown platform returns 422.
- [x] `POST /api/run` with a platform the user hasn't configured returns 400.
- [x] Integration tests cover all cases above.

---

### T-08 — `GET /api/platforms` endpoint (registry-driven) ✅ DONE
**Depends on:** T-07

**Scope:**
- `api/routes/api_platforms.py` — `GET /api/platforms` returns
  `[{"slug": "upwork", "has_config": true}, {"slug": "linkedin", "has_config": false}]`
  based on `scrapers.registry.list_platforms()` ∪ user's search configs.
- `api/schemas.py` — add `PlatformInfo`, `PlatformsListResponse`.

**Acceptance:**
- [x] Response reflects every registered scraper, not a hardcoded list.
- [x] `has_config` correctly reflects the current user's search configs.
- [x] Unit test with mocked repo.

---

### T-09 — Frontend pipeline API + hook updates ✅ DONE
**Depends on:** T-07, T-08

**Scope:**
- `frontend/src/api/pipeline.ts` — change `startRun` to accept
  `{ platforms?: string[] }` and POST a body.
- `frontend/src/api/platforms.ts` — new client for `/api/platforms`.
- `frontend/src/hooks/use-run.ts` — accept platforms in mutation args.
- `frontend/src/hooks/use-platforms.ts` — new hook.
- Zod schemas for new responses.

**Acceptance:**
- [x] Typed API surface; no `any`.
- [x] Unit tests for Zod validation of both endpoints.

---

### T-10 — Platform selection dialog on "Run Pipeline" ✅ DONE
**Depends on:** T-09

**Scope:**
- `frontend/src/components/run-pipeline-dialog.tsx` — shadcn Dialog with a
  checkbox per platform. Disabled + tooltip "Configure this platform first"
  when `has_config === false`; link to `/search-config?platform=<slug>`.
- `frontend/src/pages/dashboard.tsx` — "Run Pipeline" button opens the
  dialog instead of invoking the mutation directly.
- On confirm, call `startRun({ platforms })`.
- Handle the case where no platforms are configured yet (primary CTA is
  "Configure a search" instead of "Run").

**Acceptance:**
- [x] User sees the dialog every time they click "Run Pipeline".
- [x] Unconfigured platforms are visibly disabled with a link to configure.
- [x] Selecting zero platforms disables the Confirm button.
- [x] Selecting 1+ platforms starts a run with exactly those platforms.

---

### T-11 — LinkedIn tab in search-config page ✅ DONE
**Depends on:** T-04

**Scope:**
- `frontend/src/pages/search-config.tsx` — refactor to a tabbed layout
  (Upwork | LinkedIn). The tab list is driven from `/api/platforms`.
- `frontend/src/components/search-config/linkedin-form.tsx` — form with:
  `keyword` (string[] tag input), `location`, `distance`, `publishedAt`
  (select: 24h/week/month = r86400/r604800/r2592000), `jobType` (multi-select),
  `experienceLevel` (multi-select), `workType` (multi-select), `salaryBase`
  (number), `maxItems` (number, max 1000), `saveOnlyUniqueItems` (bool).
- Re-use existing create/update mutation — LinkedIn config is stored as a
  normal `search_configs` row with `platform = "linkedin"`.

**Acceptance:**
- [x] User can create, view, and delete a LinkedIn search config.
- [x] Form validates `maxItems <= 1000`.
- [x] Saved filters match the Apify actor schema exactly.
- [x] Existing Upwork form still works unchanged.

---

### T-12 — Real-time pipeline status polling ✅ DONE
**Scope:**
- `frontend/src/hooks/use-run.ts` — add `useRunStatus(runId)` using
  `refetchInterval: (q) => q.state.data?.status === "running" ? 2000 : false`,
  `refetchIntervalInBackground: false`.
- Invalidate results / dashboard queries on transition to `completed`.
- Update dashboard run status component to use the hook (no setTimeout).

**Acceptance:**
- [x] When run finishes, UI updates within ≤3s without reload.
- [x] No polling happens once status is `completed` or `failed`.
- [x] No memory leak — unmount stops polling.

---

### T-13 — Rehydrate running state on page reload ✅ DONE
**Depends on:** T-12

**Scope:**
- `frontend/src/pages/dashboard.tsx` — on mount, check `recent_runs[0]`;
  if status is `running` or `pending`, seed `useRunStatus` with that run_id
  so the animated "running" state appears immediately.
- Ensure the dashboard `recent_runs` query is re-validated when polling
  transitions to terminal state.

**Acceptance:**
- [x] Reload during an active run shows animated running icon (not static pending).
- [x] No flicker/race between initial dashboard fetch and status poll.

---

### T-14 — "Create new list" option in the Add-to-list dropdown ✅ DONE
**Scope:**
- `frontend/src/components/job-card/add-to-list-menu.tsx` (or equivalent) —
  add a "Create new list..." item at the bottom of the dropdown.
- Clicking it opens an inline Popover/Dialog with a name input.
- On submit: `POST /api/lists` to create the list, then
  `POST /api/lists/{id}/jobs` to add the job; invalidate lists queries.
- Handle errors (duplicate name, network failure) with toasts.

**Acceptance:**
- [x] User can create a new list and add the current job in one flow.
- [x] New list appears in the dropdown immediately (cache invalidated).
- [x] No regression with the existing "+" button flow.

---

### T-15 — Profile "Clear all" button ✅ DONE
**Scope:**
- `frontend/src/pages/profile.tsx` — add a destructive "Clear all" button.
  Opens a shadcn AlertDialog: "Clear all profile fields? This cannot be undone."
- On confirm, reset form state to empty defaults and call the existing save
  mutation (`POST /api/profile` with empty payload).
- Toast on success.

**Acceptance:**
- [x] Confirmation dialog shown every time; Esc/Cancel leaves data intact.
- [x] After confirm, `GET /api/profile` returns empty arrays and null scalars.
- [x] No backend changes required.

---

### T-16 — Documentation & release bump ✅ DONE
**Depends on:** all above

**Scope:**
- Update `CLAUDE.md` if new env vars or tech stack entries added.
- Bump `VERSION` to `2.2.0` for release commit.
- Create `docs/v2.2.md` summarising shipped features and migration notes.

**Acceptance:**
- [x] Docs mention LinkedIn scraper and platform selection dialog.
- [x] `VERSION` file bumped, visible in the footer after deploy.

---

## Dependency Graph

```
T-01  independent
T-02  independent
T-03  → T-02
T-04  independent
T-05  → T-04
T-06  → T-04
T-07  → T-06
T-08  → T-07
T-09  → T-07, T-08
T-10  → T-09
T-11  → T-04
T-12  independent (frontend-only)
T-13  → T-12
T-14  independent
T-15  independent
T-16  → all
```

**Parallel start candidates (no dependencies):** T-01, T-02, T-04, T-12, T-14, T-15
