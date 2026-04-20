# TypeScript Review Tasks — v1.1.1

Tasks derived from a full manual TypeScript/React code review of the pick-ma-job frontend (April 2026).

**Verdict:** No Critical issues. 5 High, 9 Medium, 4 Low issues found.

---

## High (fix before merge)

| Task | File | Issue |
|------|------|-------|
| [H1](H1_unguarded-json-parse-build-rubric.md) | `pages/profile-helpers.ts:66` | Unguarded `JSON.parse` in `buildRubric` — throws on malformed input |
| [H2](H2_unsafe-as-casts-filter-dicts.md) | `upwork-filters-form.tsx:35–41`, `linkedin-form.tsx:84–94` | Unsafe `as`-casts on external API filter dicts — no runtime validation |
| [H3](H3_floating-promise-list-menu.md) | `components/add-to-list-menu.tsx:118–121` | Floating promise in list dropdown handler — no await, no loading state |
| [H4](H4_missing-error-boundary.md) | `App.tsx` | No `<ErrorBoundary>` wrapping authenticated routes — blank screen on render errors |
| [H5](H5_missing-schema-magic-link.md) | `api/auth.ts:12` | `requestMagicLink` passes no Zod schema — bare `as` cast on API response |

## Medium (clean up soon)

| Task | File | Issue |
|------|------|-------|
| [M1](M1_index-keys-removable-lists.md) | `components/tag-input.tsx:52`, `components/run-status.tsx:83` | `key={i}` index used for removable/updating lists |
| [M2](M2_useeffect-form-init.md) | `pages/profile.tsx:45–50` | `useEffect` for form init causes extra render cycle |
| [M3](M3_console-error-production.md) | `api/client.ts:88` | `console.error` fires unconditionally in production — leaks internals |
| [M4](M4_swallowed-error-handle-delete.md) | `components/list-manager.tsx:67–73` | `handleDelete` swallows all errors silently |
| [M5](M5_unhandled-rejection-delete-result.md) | `pages/results.tsx:500` | Concurrent bulk + per-row delete can cause unhandled rejection |
| [M6](M6_unsafe-platform-cast.md) | `pages/search-config.tsx:113` | Unsafe platform cast (`string` → `Platform`) without runtime guard |
| [M7](M7_dead-code-use-list-jobs.md) | `hooks/use-lists.ts:74–83` | Unreachable `undefined` branch in `queryFn` — dead code |
| [M8](M8_broken-eslint-config.md) | `eslint.config.js:6` | ESLint config broken — linting silently disabled throughout development |
| [M9](M9_misc-code-quality.md) | Various | Batched small quality fixes |
