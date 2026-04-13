# Implementation Plan: v2.2

## Summary

v2.2 delivers four features and two UX fixes on top of the v2.1 SaaS MVP:

1. Session persistence fix (cookie `Path=/`)
2. Profile "Clear all" button
3. Version number display (single source of truth)
4. LinkedIn scraper integration + per-run platform selection UX
5. Real-time pipeline status (TanStack Query polling)
6. "Create new list" option in the "Add to list" dropdown

All backend changes keep the plugin architecture (no hardcoded platform names in
core logic), the `frozen=True` data contract on `NormalizedJob` /
`EvaluationResult`, and request-scoped DI via FastAPI `Depends()`.

---

## Implementation Phases

Order matters — later phases consume primitives introduced earlier.

### Phase 1 — Foundations (unblocks everything else)
- **Session cookie fix** (Feature 1) — small, isolated, ships first so all
  subsequent dev/QA is done on a stable session.
- **Version single-source-of-truth** (Feature 3) — introduces a `VERSION`
  constant and `/api/version` endpoint used later by the footer component.

### Phase 2 — LinkedIn Scraper (backend)
- Implement `LinkedInScraper.fetch_jobs` (mirrors `UpworkScraper` pattern).
- Create `configs/platforms/linkedin.json` (actor_id, field_mappings).
- Create `configs/prompts/linkedin_context.json` (evaluator context + template).
- Unit tests for LinkedIn → `NormalizedJob` mapping.

### Phase 3 — Per-Run Platform Selection (backend)
- Change `POST /api/run` to accept `platforms: list[str]` in JSON body
  (replace the `?platform=` query param). Keep backward-compatible single-
  platform semantics if only one is sent.
- Extend `PipelineService.run_pipeline` + `RunManager.start_run` to accept a
  `platforms: list[str] | None` argument (None = all configured).
- Generalise `SearchConfigService.get_by_platform` call sites to accept a list.
- Validate every platform slug against `KNOWN_PLATFORMS` (already derived from
  the scraper registry — no hardcoding required).

### Phase 4 — Frontend Platform Selection
- Platform selection dialog on Dashboard "Run Pipeline" button.
- Availability driven by `GET /api/search-configs` results — disable platforms
  with no config, show a hint linking to the search-config page.
- LinkedIn tab in the search-config page with the full LinkedIn form schema
  (keyword[], location, distance, publishedAt, jobType[], experienceLevel[],
  workType[], salaryBase, maxItems, saveOnlyUniqueItems).

### Phase 5 — UX Fixes
- Real-time status polling with TanStack Query (`refetchInterval` while
  `status === "running"`; stop on terminal states).
- On app boot, if the dashboard reports an active run, re-attach polling on
  that run_id so the animated "running" state is restored without reload.
- "Create new list" inline option at the bottom of the "Add to list" dropdown.

### Phase 6 — Profile Clear Button + Polish
- Destructive action with confirmation modal.
- Version footer component wired to `/api/version`.

---

## Architectural Decisions

### AD-1: `POST /api/run` body, not query param
**Decision:** Move platform selection from `?platform=` query string to a JSON
body `{ "platforms": ["upwork", "linkedin"] }`.
**Rationale:** (1) multi-value selection is natural in a body, (2) body
content already flows through CSRF-protected POST, (3) queries with repeated
keys are awkward on the client. Backward compatibility is irrelevant — only
our SPA calls this endpoint.

### AD-2: `platforms: list[str] | None` in service layer
**Decision:** Accept an optional list in `PipelineService.run_pipeline`.
`None` preserves existing "all configured" behaviour; an empty list is an
error.
**Rationale:** Avoids a breaking signature change for callers that don't care
about selection (tests, scripts). Keeps plugin architecture — the service
only filters configs by platform slug, never references specific platforms.

### AD-3: Version single source of truth
**Decision:** Plain text file `VERSION` at repo root (e.g. `2.2.0`). Loaded
at FastAPI startup into `app.state.version` and exposed via `GET /api/version`.
Frontend reads from the API, not from `package.json`.
**Rationale:** Avoids duplication between `frontend/package.json` and any
Python constant. Single file edited per release. Deploy script can `cat`
the file for logging.

### AD-4: Session cookie must include `Path=/`
**Decision:** Add explicit `path="/"` to every `set_cookie` / `delete_cookie`
call in `api/routes/auth.py` for both `session_token` and `csrf_token`.
**Rationale:** Without an explicit path, Starlette defaults the cookie path
to the request path (`/auth/verify`), so the cookie is only sent on
`/auth/*` requests and lost on `/dashboard`, `/results`, etc. This is the
root cause of Feature 1. Also confirm `secure=True` behind nginx HTTPS
(via `_is_secure()`) and `samesite="lax"` (already correct). Frontend
already sends `credentials: "include"`.

### AD-5: LinkedIn `NormalizedJob` mapping
`extras` carries LinkedIn-only fields used by the evaluator prompt template:
`company_name`, `location`, `work_type`, `sector`, `applications_count`,
`apply_type`, `posted_time`, `poster_name`, `company_url`.
`skills` stays `None` (not provided by the actor). `budget` is built by
joining `salaryInfo[]` strings (e.g. `"$93k – $130k"`), or `None` if empty.

### AD-6: Real-time polling via TanStack Query
**Decision:** Use `useQuery` on `GET /api/run/{id}/status` with
`refetchInterval: (data) => data?.status === "running" ? 2000 : false` and
`refetchIntervalInBackground: false`. No WebSocket/SSE for MVP.
**Rationale:** TanStack Query is already used; polling at 2s is cheap
(<1 req/sec/user), stops automatically on terminal states, and trivially
survives page reloads when the active run_id is rehydrated from
`GET /api/dashboard` (`recent_runs[0]`).

### AD-7: Platform selection dialog source of truth
The dialog lists all platforms from the scraper registry (exposed via a new
`GET /api/platforms` — `[{slug, has_config}]`). No hardcoded list in the
frontend. This preserves the plugin architecture: adding a new scraper later
automatically appears in the dialog.

---

## Risks & Open Questions

- **R1 (low):** Cookie path fix may expose the session cookie to non-HTTPS
  requests during local dev. Mitigation: `_is_secure()` already toggles
  `secure` based on environment.
- **R2 (medium):** LinkedIn Apify actor output may differ from the documented
  schema. Mitigation: unit tests cover the mapping with representative
  fixtures; unknown fields land in `extras` without breaking.
- **R3 (medium):** Per-run platform selection is a breaking change to
  `POST /api/run` (body instead of query param). Mitigation: frontend and
  backend ship together on the same deploy; no external consumers.
- **R4 (low):** Polling at 2s across many users could strain the DB.
  `get_run` is in-memory only — no DB hit per poll. Acceptable.
- **R5 (low):** "Create new list" from dropdown needs to invalidate the lists
  query; make sure we don't race with an immediate "add job to list" call.
  Mitigation: await list creation, then add the job with the returned id.
- **Open Q1:** Should "Clear all" on profile call `POST /api/profile` with an
  empty payload, or a new `DELETE /api/profile` endpoint? Recommendation:
  reuse `POST /api/profile` with empty payload — zero backend change.
- **Open Q2:** Version format — semver (`2.2.0`) vs. git-sha suffix
  (`2.2.0+abc1234`)? Recommendation: plain semver for now; include commit
  sha later if needed.
